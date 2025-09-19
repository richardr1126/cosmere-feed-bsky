#!/bin/bash

# Deploy script for building and deploying local charts (cosmere application components)

FIREHOSE_IMAGE=ghcr.io/richardr1126/cosmere-firehose
WEB_IMAGE=ghcr.io/richardr1126/cosmere-feed
SCHEDULER_IMAGE=ghcr.io/richardr1126/cosmere-scheduler

# Exit on any error
set -e

# Parse command line arguments
BUILD=false

# Check if .env exists
if [ ! -f "../../.env" ]; then
  echo "Error: .env file not found"
  echo "Please copy template.env to .env and fill in your API keys"
  exit 1
fi

# Source the .env file
. ../../.env

for arg in "$@"; do
  if [ "$arg" == "--build" ]; then
    BUILD=true
  else
    echo "Unknown parameter: $arg"
    echo "Usage: $0 [--build]"
    echo "  --build: Build and push Docker images before deploying"
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
fi

# Install custom charts with appropriate settings
echo "Installing firehose chart..."
helm upgrade --install firehose ./firehose \
  --wait

echo "Installing web chart..."
helm upgrade --install cosmere-web ./web \
  -f ./web/homelab-values.yaml \
  --wait

echo "Installing scheduler chart..."
helm upgrade --install scheduler ./scheduler \
  --wait

echo "Application deployment complete!"
