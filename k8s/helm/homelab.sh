
#!/bin/bash

FIREHOSE_IMAGE=ghcr.io/richardr1126/cosmere-firehose
WEB_IMAGE=ghcr.io/richardr1126/cosmere-feed
SCHEDULER_IMAGE=ghcr.io/richardr1126/cosmere-scheduler

# Exit on any error
set -e

# Parse command line arguments
LONG=false
CLEAR=false

# Check if .env exists
if [ ! -f "../../.env" ]; then
  echo "Error: .env file not found"
  echo "Please copy template.env to .env and fill in your API keys"
  exit 1
fi

# Source the .env file
. ../../.env

for arg in "$@"; do
  if [ "$arg" == "--long" ]; then
    LONG=true
  elif [ "$arg" == "--clear" ]; then
    CLEAR=true
  else
    echo "Unknown parameter: $arg"
    exit 1
  fi
done

# Clear existing resources if --clear flag is set
if [ "$CLEAR" = true ]; then
  echo "Running helm uninstall cert-manager, external-dns..."
  helm uninstall -n cert-manager cert-manager external-dns --wait --ignore-not-found

  echo "Running helm uninstall yugabyte..."
  helm uninstall -n yugabyte yugabyte --wait --ignore-not-found

  echo "Running helm uninstall on all other charts..."
  helm uninstall web firehose scheduler --wait --ignore-not-found
  
  echo "Deleting cert-manager CRDs..."
  kubectl delete crd certificates.cert-manager.io --ignore-not-found
  kubectl delete crd certificaterequests.cert-manager.io --ignore-not-found
  kubectl delete crd challenges.acme.cert-manager.io --ignore-not-found
  kubectl delete crd clusterissuers.cert-manager.io --ignore-not-found
  kubectl delete crd issuers.cert-manager.io --ignore-not-found
  kubectl delete crd orders.acme.cert-manager.io --ignore-not-found

  echo "Deleting kube-prometheus-stack"
  helm uninstall prometheus --namespace monitoring --wait --ignore-not-found
  kubectl delete crd alertmanagerconfigs.monitoring.coreos.com
  kubectl delete crd alertmanagers.monitoring.coreos.com
  kubectl delete crd podmonitors.monitoring.coreos.com
  kubectl delete crd probes.monitoring.coreos.com
  kubectl delete crd prometheusagents.monitoring.coreos.com
  kubectl delete crd prometheuses.monitoring.coreos.com
  kubectl delete crd prometheusrules.monitoring.coreos.com
  kubectl delete crd scrapeconfigs.monitoring.coreos.com
  kubectl delete crd servicemonitors.monitoring.coreos.com
  kubectl delete crd thanosrulers.monitoring.coreos.com
  kubectl delete namespace monitoring --wait --ignore-not-found

  echo "Deleting YugabyteDB CRDs..."
  kubectl delete crd ybclusters.yugabyte.com --ignore-not-found

  echo "Deleting namespaces and persistent volume claims..."
  kubectl delete namespaces yugabyte cert-manager --wait --ignore-not-found
  kubectl delete pvc --all --force
  
  sleep 10
fi

# Create Kubernetes secret from environment variables
echo "Creating Kubernetes secrets..."
kubectl create secret generic api-secrets \
  --from-literal=HOSTNAME=$HOSTNAME \
  --from-literal=CHRONOLOGICAL_TRENDING_URI=$CHRONOLOGICAL_TRENDING_URI \
  --from-literal=HANDLE=$HANDLE \
  --from-literal=PASSWORD=$PASSWORD \
  --from-literal=POSTGRES_USER=$POSTGRES_USER \
  --from-literal=POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  --from-literal=POSTGRES_DB=$POSTGRES_DB \
  --from-literal=POSTGRES_HOST=$POSTGRES_HOST \
  --from-literal=POSTGRES_PORT=$POSTGRES_PORT \
  --dry-run=client -o yaml | kubectl apply -f -

if [ "$LONG" = true ]; then
  # Add helm repositories
  echo "Adding Helm repositories..."
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
  helm repo add jetstack https://charts.jetstack.io
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm repo add yugabytedb https://charts.yugabyte.com
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
  helm repo add grafana https://grafana.github.io/helm-charts
  helm repo update

  # Install cert-manager for Let's Encrypt
  echo "Installing cert-manager..."
  helm upgrade --install -n cert-manager cert-manager jetstack/cert-manager \
    --create-namespace \
    -f ./cert-manager/values.yaml \
    --wait

  # Install ExternalDNS for Cloudflare
  echo "Installing ExternalDNS..."
  kubectl create secret generic cloudflare-dns \
    --namespace cert-manager \
    --from-literal=cloudflare_api_token=$CLOUDFLARE_API_TOKEN \
    --dry-run=client -o yaml | kubectl apply -f -
  helm upgrade --install external-dns external-dns/external-dns --version 1.15.2 \
    -f ./ingress/external-dns-values.yaml \
    --namespace cert-manager \
    --wait

  # Wait for cert-manager to be ready
  echo "Waiting for cert-manager to be ready..."
  kubectl wait --for=condition=Available deployment/cert-manager-webhook -n cert-manager --timeout=60s
  kubectl wait --for=condition=Available deployment/cert-manager-cainjector -n cert-manager --timeout=60s
  kubectl wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=60s

  # Create keystore password secret first
  echo "Creating letsencrypt-prod-key secret..."
  kubectl create secret generic letsencrypt-prod-key \
    --dry-run=client -o yaml | kubectl apply -f -

  # Create cluster issuer secrets
  echo "Creating Let's Encrypt cluster issuer secrets..."
  kubectl apply -f ./cert-manager/cluster-issuer.yaml

  kubectl wait --for=condition=Ready clusterissuer/letsencrypt-prod --timeout=60s

  # Install NGINX Ingress Controller
  echo "Installing NGINX Ingress Controller..."
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    -f ./ingress/nginx-values.yaml \
    --wait
    
fi

# Install kube-prometheus-stack
echo "Installing kube-prometheus-stack..."
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  -f ./kube-prometheus-stack-values.yaml \
  --namespace monitoring \
  --create-namespace \
  --wait

# Install Loki
echo "Installing Loki..."
helm upgrade --install loki grafana/loki-stack \
  --namespace monitoring \
  --set loki.isDefault=false \
  --wait 

# Install yugabytedb
echo "Installing YugabyteDB..."
# helm install yb-demo yugabytedb/yugabyte --version 2.25.0 --namespace yb-demo --wait
helm upgrade --install yugabyte yugabytedb/yugabyte --namespace yugabyte --create-namespace \
  -f yugabyte-homelab.yaml \
  --wait \
  --timeout 30m

# Install custom charts with appropriate settings
echo "Installing firehose chart..."
helm upgrade --install firehose ./firehose \
  --wait

echo "Installing web chart..."
helm upgrade --install web ./web \
  -f ./web/homelab-values.yaml \
  --wait

echo "Installing scheduler chart..."
helm upgrade --install scheduler ./scheduler \
  --wait

# Setup Cloudflared
# Import cloudflared tunnel credentials
# echo "Importing cloudflared tunnel credentials..."
# kubectl create secret generic tunnel-credentials \
#   --from-file=credentials.json=/home/richard-roberson/.cloudflared/d2fada6d-89c0-473e-a5f2-4625b2b5576d.json

# kubectl apply -f ./ingress/homelab-cloudflared-config.yaml
# kubectl apply -f ./ingress/homelab-cloudflared-deployment.yaml

echo "Grafana admin password:"
kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

echo "Setup complete!"