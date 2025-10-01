#!/bin/bash
# Deployment Script for Mandate Vault
# ====================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-us-central1}

echo -e "${GREEN}Starting deployment to ${ENVIRONMENT}...${NC}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo -e "${RED}Error: Environment must be 'staging' or 'production'${NC}"
    exit 1
fi

# Check if logged in to GCP
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Error: Not logged in to GCP. Run: gcloud auth login${NC}"
    exit 1
fi

echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}Version: ${VERSION}${NC}"
echo -e "${YELLOW}Project: ${PROJECT_ID}${NC}"

# Confirm deployment
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Build and push Docker image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t gcr.io/${PROJECT_ID}/mandate-vault:${VERSION} .

echo -e "${GREEN}Pushing to Google Container Registry...${NC}"
docker push gcr.io/${PROJECT_ID}/mandate-vault:${VERSION}

if [ "$ENVIRONMENT" = "staging" ]; then
    # Deploy to Cloud Run (staging)
    echo -e "${GREEN}Deploying to Cloud Run (staging)...${NC}"
    gcloud run deploy mandate-vault-staging \
        --image gcr.io/${PROJECT_ID}/mandate-vault:${VERSION} \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars ENVIRONMENT=staging \
        --set-secrets=SECRET_KEY=mandate-vault-secret-key:latest,DATABASE_URL=mandate-vault-database-url-staging:latest \
        --min-instances 1 \
        --max-instances 5
    
    # Get URL
    STAGING_URL=$(gcloud run services describe mandate-vault-staging --region ${REGION} --format 'value(status.url)')
    
    # Run health check
    echo -e "${GREEN}Running health check...${NC}"
    sleep 10
    if curl -f ${STAGING_URL}/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check passed${NC}"
        echo -e "${GREEN}Staging URL: ${STAGING_URL}${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        exit 1
    fi

else
    # Deploy to Kubernetes (production)
    echo -e "${GREEN}Deploying to Kubernetes (production)...${NC}"
    
    # Get cluster credentials
    gcloud container clusters get-credentials mandate-vault-cluster --region ${REGION}
    
    # Update deployment
    kubectl set image deployment/mandate-vault \
        api=gcr.io/${PROJECT_ID}/mandate-vault:${VERSION} \
        -n mandate-vault
    
    # Wait for rollout
    echo -e "${YELLOW}Waiting for rollout to complete...${NC}"
    kubectl rollout status deployment/mandate-vault -n mandate-vault --timeout=5m
    
    # Verify pods
    echo -e "${GREEN}Verifying pods...${NC}"
    kubectl get pods -n mandate-vault -l app=mandate-vault
    
    # Run health check
    echo -e "${GREEN}Running health check...${NC}"
    PROD_URL="https://api.yourdomain.com"
    if curl -f ${PROD_URL}/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        echo -e "${YELLOW}Rolling back...${NC}"
        kubectl rollout undo deployment/mandate-vault -n mandate-vault
        exit 1
    fi
fi

echo -e "${GREEN}✓ Deployment successful!${NC}"

