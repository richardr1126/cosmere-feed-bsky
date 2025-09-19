#!/bin/bash

# Script for creating Kubernetes secrets from environment variables

# Exit on any error
set -e

# Check if .env exists
if [ ! -f "../../.env" ]; then
  echo "Error: .env file not found"
  echo "Please copy template.env to .env and fill in your API keys"
  exit 1
fi

# Source the .env file
. ../../.env

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

echo "Kubernetes secrets created successfully!"