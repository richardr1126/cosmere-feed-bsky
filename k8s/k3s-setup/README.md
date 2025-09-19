# K3s Homelab Setup Guide

This guide provides step-by-step instructions for setting up a K3s cluster with all necessary infrastructure components for the Cosmere Feed application.

## Prerequisites

- Raspberry Pi or similar hardware running Ubuntu/Debian
- Domain name configured with Cloudflare DNS
- kubectl installed on your local machine
- Helm 3.x installed

## Environment Setup

1. **Create Environment File**
   ```bash
   cp template.env .env
   ```
   
2. **Configure Environment Variables**
   Edit `.env` file with your Cloudflare API token:
   ```properties
   CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
   ```

## K3s Cluster Installation

### 1. Install K3s Master Node

Use k3sup to install K3s on your master node:

```bash
k3sup install --ip 192.168.0.18 \
  --tls-san 192.168.0.40 \
  --cluster \
  --k3s-extra-args '--disable servicelb' \
  --local-path ~/.kube/raspberry-pi-kubeconfig.yaml \
  --user richard-roberson
```

**Explanation:**
- `--ip`: IP address of your K3s master node
- `--tls-san`: Subject Alternative Name for TLS certificate (VIP address)
- `--disable servicelb`: Disable default service load balancer (we'll use kube-vip)
- `--local-path`: Where to save the kubeconfig file

**Note:** We keep Traefik enabled as it's used as the ingress controller.

### 2. Configure Kube-VIP for Load Balancing

SSH into your K3s server and run these commands:

```bash
# Create manifests directory
sudo mkdir -p /var/lib/rancher/k3s/server/manifests/

# Download RBAC configuration
sudo curl https://kube-vip.io/manifests/rbac.yaml | sudo tee /var/lib/rancher/k3s/server/manifests/kube-vip.yaml > /dev/null
echo -e "\n---" | sudo tee -a /var/lib/rancher/k3s/server/manifests/kube-vip.yaml

# Set environment variables
export VIP=192.168.0.40
export INTERFACE=eth0
KVVERSION=$(curl -sL https://api.github.com/repos/kube-vip/kube-vip/releases | jq -r ".[0].name")

# Create alias for kube-vip
alias kube-vip="sudo ctr image pull ghcr.io/kube-vip/kube-vip:$KVVERSION; sudo ctr run --rm --net-host ghcr.io/kube-vip/kube-vip:$KVVERSION vip /kube-vip"

# Generate kube-vip manifest
kube-vip manifest daemonset \
  --interface $INTERFACE \
  --address $VIP \
  --inCluster \
  --taint \
  --controlplane \
  --services \
  --arp \
  --leaderElection | sudo tee -a /var/lib/rancher/k3s/server/manifests/kube-vip.yaml
```

**Note:** After generating the manifest, edit `/var/lib/rancher/k3s/server/manifests/kube-vip.yaml` and add this environment variable to the kube-vip container:
```yaml
- name: enableUPNP
  value: "true"
```

### 3. Install Kube-VIP Cloud Provider

```bash
kubectl apply -f https://raw.githubusercontent.com/kube-vip/kube-vip-cloud-provider/main/manifest/kube-vip-cloud-controller.yaml
kubectl create configmap -n kube-system kubevip --from-literal range-global=192.168.0.69-192.168.0.79
kubectl annotate service traefik -n kube-system kube-vip.io/forwardUPNP="true"
```

### 4. Add Additional Nodes (Optional)

To add worker nodes:

```bash
# First, copy SSH key and configure sudo access on the new node
ssh-copy-id richard-roberson@192.168.0.30
```

Ensure the user `richard-roberson` has passwordless sudo access on the new node. You can do this by editing the sudoers file:

```bash
# SSH into the new node
ssh richard-roberson@192.168.0.30
# Edit the sudoers file
sudo visudo
```
Add the following line to allow passwordless sudo for the user:
```bash
richard-roberson ALL=(ALL) NOPASSWD: ALL
```
Then, run the following command from your master node to join the new node to the cluster:

```bash
# Join the node to the cluster
k3sup join --ip 192.168.0.30 \
  --server-ip 192.168.0.18 \
  --server \
  --k3s-channel latest \
  --user richard-roberson
```

## Infrastructure Components Installation

### 1. Add Helm Repositories

```bash
helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm repo add jetstack https://charts.jetstack.io
helm repo add yugabytedb https://charts.yugabyte.com
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

### 2. Install Cert-Manager

Cert-manager handles automatic TLS certificate provisioning from Let's Encrypt.

```bash
# Install cert-manager
helm upgrade --install -n cert-manager cert-manager jetstack/cert-manager \
  --create-namespace \
  -f ./cert-manager/values.yaml \
  --wait

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available deployment/cert-manager-webhook -n cert-manager --timeout=60s
kubectl wait --for=condition=Available deployment/cert-manager-cainjector -n cert-manager --timeout=60s
kubectl wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=60s
```

**Configuration:** The `cert-manager/values.yaml` file should contain cert-manager specific configurations.

### 3. Install External DNS

External DNS automatically manages DNS records in Cloudflare based on Kubernetes ingress resources.

```bash
# Create Cloudflare API token secret
kubectl create secret generic cloudflare-dns \
  --namespace cert-manager \
  --from-literal=cloudflare_api_token=$CLOUDFLARE_API_TOKEN \
  --dry-run=client -o yaml | kubectl apply -f -

# Install external-dns
helm upgrade --install external-dns external-dns/external-dns --version 1.15.2 \
  -f ./ingress/external-dns-values.yaml \
  --namespace cert-manager \
  --wait
```

**Configuration:** The `external-dns-values.yaml` contains:
```yaml
provider:
  name: cloudflare

env:
  - name: CF_API_TOKEN
    valueFrom:
      secretKeyRef:
        name: cloudflare-dns
        key: cloudflare_api_token

extraArgs:
  - --exclude-target-net=192.168.0.0/16
```

### 4. Configure Let's Encrypt Cluster Issuer

```bash
# Create secret for Let's Encrypt private key storage
kubectl create secret generic letsencrypt-prod-key \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply cluster issuer configuration
kubectl apply -f ./cert-manager/cluster-issuer.yaml

# Wait for cluster issuer to be ready
kubectl wait --for=condition=Ready clusterissuer/letsencrypt-prod --timeout=60s
```

### 5. Install Monitoring Stack

#### Prometheus and Grafana

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  -f ./kube-prometheus-stack-values.yaml \
  --namespace monitoring \
  --create-namespace \
  --wait
```

#### Loki for Log Aggregation

```bash
helm upgrade --install loki grafana/loki-stack \
  --namespace monitoring \
  --set loki.isDefault=false \
  --wait
```

### 6. Install YugabyteDB

YugabyteDB serves as the distributed database for the application.

```bash
helm upgrade --install yugabyte yugabytedb/yugabyte --namespace yugabyte --create-namespace \
  -f yugabyte-homelab.yaml \
  --wait \
  --timeout 30m
```

## Post-Installation

### Access Grafana

Get the Grafana admin password:
```bash
kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d
```

### Verify Installation

1. **Check all pods are running:**
   ```bash
   kubectl get pods --all-namespaces
   ```

2. **Verify services have external IPs:**
   ```bash
   kubectl get services --all-namespaces
   ```

3. **Check ingress resources:**
   ```bash
   kubectl get ingress --all-namespaces
   ```

## Network Configuration

### IP Address Allocation

- **K3s Master Node:** 192.168.0.18
- **Kube-VIP Virtual IP:** 192.168.0.40
- **LoadBalancer IP Range:** 192.168.0.69-192.168.0.79
- **Additional Nodes:** 192.168.0.30+

### Port Configuration

- **K3s API Server:** 6443
- **Grafana:** 3000
- **YugabyteDB Master:** 7000
- **YugabyteDB TServer:** 9000

## Troubleshooting

### Common Issues

1. **Cert-manager not ready:** Wait longer for cert-manager components to become available
2. **DNS not resolving:** Check Cloudflare API token and external-dns logs
3. **LoadBalancer pending:** Verify kube-vip cloud provider is installed correctly
4. **Pods not scheduling:** Check node resources and taints

### Useful Commands

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check external-dns logs
kubectl logs -n cert-manager deployment/external-dns

# Check kube-vip status
kubectl logs -n kube-system daemonset/kube-vip-ds

# Get cluster issuer status
kubectl describe clusterissuer letsencrypt-prod
```

## Security Considerations

1. **API Tokens:** Store all API tokens in Kubernetes secrets, never in plain text
2. **Network Policies:** Consider implementing network policies for pod-to-pod communication
3. **RBAC:** Review and customize RBAC permissions as needed
4. **TLS:** All external traffic should use TLS certificates from Let's Encrypt

## Maintenance

### Regular Tasks

1. **Update Helm Charts:** Regularly update helm repositories and chart versions
2. **Monitor Resources:** Keep an eye on CPU, memory, and disk usage
3. **Backup Configuration:** Regularly backup your kubeconfig and important secrets
4. **Certificate Renewal:** Cert-manager handles this automatically, but monitor for issues

### Scaling

To scale the cluster:
1. Add more worker nodes using the node addition process
2. Increase resource limits in helm chart values
3. Consider implementing horizontal pod autoscaling for applications
