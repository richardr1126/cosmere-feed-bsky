#!/bin/bash

export KUBECONFIG=~/.kube/rckspc-personal-kubeconfig.yaml
FIREHOSE_IMAGE=ghcr.io/richardr1126/cosmere-firehose
WEB_IMAGE=ghcr.io/richardr1126/cosmere-feed
SCHEDULER_IMAGE=ghcr.io/richardr1126/cosmere-scheduler

# Exit on any error
set -e

# Parse command line arguments
BUILD=false
BUILD_WEB=false
BUILD_FIREHOSE=false
BUILD_SCHEDULER=false
CLEAR=false

# Check if .env exists
if [ ! -f "../../.env" ]; then
  echo "Error: .env file not found"
  echo "Please copy template.env to .env and fill in your API keys"
  exit 1
fi

# Source the .env file
source "../../.env"

for arg in "$@"; do
  if [ "$arg" == "--build" ]; then
    BUILD=true
  elif [ "$arg" == "--build-web" ]; then
    BUILD_WEB=true
  elif [ "$arg" == "--build-firehose" ]; then
    BUILD_FIREHOSE=true
  elif [ "$arg" == "--build-scheduler" ]; then
    BUILD_SCHEDULER=true
  elif [ "$arg" == "--clear" ]; then
    CLEAR=true
  else
    echo "Unknown parameter: $arg"
    exit 1
  fi
done

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

# Early check for individual component builds
if [ "$BUILD_WEB" = true ] || [ "$BUILD_FIREHOSE" = true ] || [ "$BUILD_SCHEDULER" = true ]; then
  # Login to ghcr.io
  echo "Logging in to ghcr.io..."
  docker login ghcr.io -u richardr1126 -p $GITHUB_PAT

  if [ "$BUILD_WEB" = true ]; then
    helm uninstall web --wait --ignore-not-found
    echo "Building and pushing web API image..."
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t $WEB_IMAGE:latest \
      --push \
      ../../.

    echo "Upgrading web chart..."
    helm upgrade --install web ./web \
      --wait
  fi

  if [ "$BUILD_FIREHOSE" = true ]; then
    helm uninstall firehose --wait --ignore-not-found
    echo "Building and pushing firehose image..."
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t $FIREHOSE_IMAGE:latest \
      --push \
      ../../firehose

    echo "Upgrading firehose chart..."
    helm upgrade --install firehose ./firehose \
      --wait
  fi

  if [ "$BUILD_SCHEDULER" = true ]; then
    helm uninstall scheduler --wait --ignore-not-found
    echo "Building and pushing scheduler image..."
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t $SCHEDULER_IMAGE:latest \
      --push \
      ../../scheduler

    echo "Upgrading scheduler chart..."
    helm upgrade --install scheduler ./scheduler \
      --wait
  fi

  echo "Component build and upgrade complete!"
  exit 0
fi

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

  echo "Deleting YugabyteDB CRDs..."
  kubectl delete crd ybclusters.yugabyte.com --ignore-not-found

  echo "Deleting namespaces and persistent volume claims..."
  kubectl delete namespaces yugabyte cert-manager --wait --ignore-not-found
  kubectl delete pvc --all --force
  
  sleep 10
fi

if [ "$BUILD" = true ]; then
  # Login to ghcr.io
  echo "Logging in to ghcr.io..."
  docker login ghcr.io -u richardr1126 -p $GITHUB_PAT

  # Build and push all 3 images
  echo "Building and pushing all images..."
  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t $WEB_IMAGE:latest \
    --push \
    ../../.

  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t $FIREHOSE_IMAGE:latest \
    --push \
    ../../firehose

  docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t $SCHEDULER_IMAGE:latest \
    --push \
    ../../scheduler

  echo "All images built and pushed successfully!"

  # Add helm repositories
  echo "Adding Helm repositories..."
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm repo add jetstack https://charts.jetstack.io
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm repo add yugabytedb https://charts.yugabyte.com
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
  helm upgrade --install external-dns oci://registry-1.docker.io/bitnamicharts/external-dns \
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

# Install yugabytedb
echo "Installing YugabyteDB..."
# helm install yb-demo yugabytedb/yugabyte --version 2.25.0 --namespace yb-demo --wait
helm upgrade --install yugabyte yugabytedb/yugabyte --namespace yugabyte --create-namespace \
  -f yugabyte-values.yaml \
  --wait \
  --timeout 30m

# Install custom charts with appropriate settings
echo "Installing firehose chart..."
helm upgrade --install firehose ./firehose \
  --wait

echo "Installing web chart..."
helm upgrade --install web ./web \
  --wait

echo "Installing scheduler chart..."
helm upgrade --install scheduler ./scheduler \
  --wait


echo "Setup complete!"