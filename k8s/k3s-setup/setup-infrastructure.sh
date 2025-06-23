#!/bin/bash

# Setup script for general helm chart installations (infrastructure components)

# Exit on any error
set -e

# Check if .env exists
if [ ! -f "../../.env" ]; then
  echo "Error: .env file not found"
  echo "Please copy template.env to .env and fill in your API keys"
  exit 1
fi

# Source the .env file
. ./.env

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

# Install NGINX Ingress Controller (commented out)
# echo "Installing NGINX Ingress Controller..."
# helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
#   -f ./ingress/nginx-values.yaml \
#   --wait

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

echo "Grafana admin password:"
kubectl --namespace monitoring get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

echo "Infrastructure setup complete!"
