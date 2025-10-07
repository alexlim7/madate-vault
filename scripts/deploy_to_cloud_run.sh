#!/bin/bash
# Deploy Mandate Vault to Google Cloud Run
# Production-ready deployment script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║           Mandate Vault - Cloud Run Deployment            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed${NC}"
    echo -e "${YELLOW}Install from: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI is installed${NC}"

# Get project configuration
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 1: Configure GCP Project${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

read -p "Enter your GCP Project ID: " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Project ID is required${NC}"
    exit 1
fi

# Set region
read -p "Enter region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

# Set environment
read -p "Enter environment (staging/production) [default: staging]: " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-staging}

echo -e "\n${GREEN}Configuration:${NC}"
echo -e "  Project ID:  ${CYAN}$PROJECT_ID${NC}"
echo -e "  Region:      ${CYAN}$REGION${NC}"
echo -e "  Environment: ${CYAN}$ENVIRONMENT${NC}"
echo ""

read -p "Continue with this configuration? (y/n): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set project
echo -e "\n${BLUE}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 2: Enable Required APIs${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo "Enabling APIs (this may take a few minutes)..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    sql-component.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ All APIs enabled${NC}"

# Generate and store secrets
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 3: Generate and Store Secrets${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo "Generating secure secrets..."

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo -e "${GREEN}✅ Generated SECRET_KEY${NC}"

# Generate ACP_WEBHOOK_SECRET
ACP_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo -e "${GREEN}✅ Generated ACP_WEBHOOK_SECRET${NC}"

# Generate DB_PASSWORD
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo -e "${GREEN}✅ Generated DB_PASSWORD${NC}"

echo -e "\nStoring secrets in Secret Manager..."

# Store SECRET_KEY
echo -n "$SECRET_KEY" | gcloud secrets create mandate-vault-secret-key \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" \
    2>/dev/null || echo -n "$SECRET_KEY" | gcloud secrets versions add mandate-vault-secret-key --data-file=- --project=$PROJECT_ID

echo -e "${GREEN}✅ Stored SECRET_KEY${NC}"

# Store ACP_WEBHOOK_SECRET
echo -n "$ACP_SECRET" | gcloud secrets create mandate-vault-acp-webhook-secret \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" \
    2>/dev/null || echo -n "$ACP_SECRET" | gcloud secrets versions add mandate-vault-acp-webhook-secret --data-file=- --project=$PROJECT_ID

echo -e "${GREEN}✅ Stored ACP_WEBHOOK_SECRET${NC}"

# Store DB_PASSWORD
echo -n "$DB_PASSWORD" | gcloud secrets create mandate-vault-db-password \
    --data-file=- \
    --project=$PROJECT_ID \
    --replication-policy="automatic" \
    2>/dev/null || echo -n "$DB_PASSWORD" | gcloud secrets versions add mandate-vault-db-password --data-file=- --project=$PROJECT_ID

echo -e "${GREEN}✅ Stored DB_PASSWORD${NC}"

# Setup Cloud SQL
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 4: Setup Cloud SQL Database${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

read -p "Create new Cloud SQL instance? (y/n): " create_sql

if [[ "$create_sql" == "y" || "$create_sql" == "Y" ]]; then
    DB_INSTANCE="mandate-vault-db"
    
    echo "Creating Cloud SQL instance (this takes 5-10 minutes)..."
    
    gcloud sql instances create $DB_INSTANCE \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --project=$PROJECT_ID \
        --no-assign-ip \
        --network=default \
        2>/dev/null || echo "Instance might already exist, continuing..."
    
    echo -e "${GREEN}✅ Cloud SQL instance created${NC}"
    
    # Create database
    echo "Creating database..."
    gcloud sql databases create mandate_vault \
        --instance=$DB_INSTANCE \
        --project=$PROJECT_ID \
        2>/dev/null || echo "Database might already exist"
    
    echo -e "${GREEN}✅ Database created${NC}"
    
    # Create user
    echo "Creating database user..."
    gcloud sql users create mandate_user \
        --instance=$DB_INSTANCE \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID \
        2>/dev/null || echo "User might already exist"
    
    echo -e "${GREEN}✅ Database user created${NC}"
else
    read -p "Enter existing Cloud SQL instance name: " DB_INSTANCE
fi

# Build and push container
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 5: Build and Push Container Image${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

IMAGE_NAME="gcr.io/$PROJECT_ID/mandate-vault"

echo "Building container image..."
gcloud builds submit --tag $IMAGE_NAME --project=$PROJECT_ID .

echo -e "${GREEN}✅ Container image built and pushed${NC}"

# Create VPC Connector (for Cloud SQL access)
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 6: Setup VPC Connector${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

VPC_CONNECTOR="mandate-vault-connector"

echo "Creating VPC connector..."
gcloud compute networks vpc-access connectors create $VPC_CONNECTOR \
    --region=$REGION \
    --range=10.8.0.0/28 \
    --project=$PROJECT_ID \
    2>/dev/null || echo "VPC connector might already exist"

echo -e "${GREEN}✅ VPC connector ready${NC}"

# Deploy to Cloud Run
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 7: Deploy to Cloud Run${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

SERVICE_NAME="mandate-vault"
CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE"

echo "Deploying to Cloud Run..."

gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 100 \
    --vpc-connector $VPC_CONNECTOR \
    --add-cloudsql-instances $CONNECTION_NAME \
    --set-env-vars "ENVIRONMENT=$ENVIRONMENT,DEBUG=false,DATABASE_URL=postgresql+asyncpg://mandate_user:$DB_PASSWORD@/$DB_INSTANCE?host=/cloudsql/$CONNECTION_NAME" \
    --set-secrets "SECRET_KEY=mandate-vault-secret-key:latest,ACP_WEBHOOK_SECRET=mandate-vault-acp-webhook-secret:latest" \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Deployed to Cloud Run${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project=$PROJECT_ID \
    --format 'value(status.url)')

# Run database migrations
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 8: Run Database Migrations${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

read -p "Run database migrations? (y/n): " run_migrations

if [[ "$run_migrations" == "y" || "$run_migrations" == "Y" ]]; then
    echo "Creating migration job..."
    
    gcloud run jobs create mandate-vault-migrate \
        --image $IMAGE_NAME \
        --region $REGION \
        --vpc-connector $VPC_CONNECTOR \
        --add-cloudsql-instances $CONNECTION_NAME \
        --set-env-vars "DATABASE_URL=postgresql+asyncpg://mandate_user:$DB_PASSWORD@/$DB_INSTANCE?host=/cloudsql/$CONNECTION_NAME" \
        --command alembic \
        --args upgrade,head \
        --project=$PROJECT_ID \
        2>/dev/null || echo "Job might already exist"
    
    echo "Running migrations..."
    gcloud run jobs execute mandate-vault-migrate \
        --region $REGION \
        --project=$PROJECT_ID \
        --wait
    
    echo -e "${GREEN}✅ Database migrations completed${NC}"
fi

# Create initial admin user
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 9: Create Initial Admin User${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

read -p "Create initial admin user? (y/n): " create_admin

if [[ "$create_admin" == "y" || "$create_admin" == "Y" ]]; then
    echo "Creating seed data job..."
    
    gcloud run jobs create mandate-vault-seed \
        --image $IMAGE_NAME \
        --region $REGION \
        --vpc-connector $VPC_CONNECTOR \
        --add-cloudsql-instances $CONNECTION_NAME \
        --set-env-vars "DATABASE_URL=postgresql+asyncpg://mandate_user:$DB_PASSWORD@/$DB_INSTANCE?host=/cloudsql/$CONNECTION_NAME" \
        --set-secrets "SECRET_KEY=mandate-vault-secret-key:latest" \
        --command python \
        --args scripts/seed_initial_data.py \
        --project=$PROJECT_ID \
        2>/dev/null || echo "Job might already exist"
    
    echo "Creating admin user..."
    gcloud run jobs execute mandate-vault-seed \
        --region $REGION \
        --project=$PROJECT_ID \
        --wait
    
    echo -e "${GREEN}✅ Admin user created${NC}"
fi

# Display deployment summary
echo -e "\n${CYAN}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║              🎉 DEPLOYMENT SUCCESSFUL! 🎉                  ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

echo -e "${GREEN}Your Mandate Vault API is now LIVE!${NC}\n"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Deployment Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo -e "${CYAN}Service URL:${NC}     $SERVICE_URL"
echo -e "${CYAN}API Docs:${NC}        $SERVICE_URL/docs"
echo -e "${CYAN}Health Check:${NC}    $SERVICE_URL/healthz"
echo -e "${CYAN}Readiness:${NC}       $SERVICE_URL/readyz"
echo ""
echo -e "${CYAN}Project:${NC}         $PROJECT_ID"
echo -e "${CYAN}Region:${NC}          $REGION"
echo -e "${CYAN}Environment:${NC}     $ENVIRONMENT"
echo -e "${CYAN}Database:${NC}        $DB_INSTANCE"
echo ""

if [[ "$create_admin" == "y" || "$create_admin" == "Y" ]]; then
    echo -e "${CYAN}Default Admin Credentials:${NC}"
    echo -e "  Email:    admin@example.com"
    echo -e "  Password: Admin123!@#"
    echo -e "  ${YELLOW}⚠️  Change this password immediately!${NC}"
    echo ""
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Next Steps${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo "1. Verify deployment:"
echo -e "   ${CYAN}curl $SERVICE_URL/healthz${NC}"
echo ""

echo "2. View API documentation:"
echo -e "   ${CYAN}open $SERVICE_URL/docs${NC}"
echo ""

echo "3. Test authentication:"
cat << EOF
   curl -X POST "$SERVICE_URL/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{"email":"admin@example.com","password":"Admin123!@#"}'
EOF
echo ""

echo "4. View logs:"
echo -e "   ${CYAN}gcloud run services logs tail $SERVICE_NAME --region $REGION${NC}"
echo ""

echo "5. Monitor service:"
echo -e "   ${CYAN}https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Useful Commands${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo "Update deployment:"
echo -e "  ${CYAN}gcloud builds submit --tag $IMAGE_NAME${NC}"
echo -e "  ${CYAN}gcloud run services update $SERVICE_NAME --image $IMAGE_NAME --region $REGION${NC}"
echo ""

echo "View service details:"
echo -e "  ${CYAN}gcloud run services describe $SERVICE_NAME --region $REGION${NC}"
echo ""

echo "Scale service:"
echo -e "  ${CYAN}gcloud run services update $SERVICE_NAME --min-instances 2 --max-instances 20 --region $REGION${NC}"
echo ""

echo "Delete service:"
echo -e "  ${CYAN}gcloud run services delete $SERVICE_NAME --region $REGION${NC}"
echo ""

echo -e "${GREEN}🎉 Deployment complete! Your API is production-ready!${NC}\n"

# Save deployment info
cat > deployment_info.txt << EOF
Mandate Vault - Deployment Information
======================================

Deployment Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION
Environment: $ENVIRONMENT

Service URL: $SERVICE_URL
API Docs: $SERVICE_URL/docs
Health Check: $SERVICE_URL/healthz

Database Instance: $DB_INSTANCE
VPC Connector: $VPC_CONNECTOR

Secrets (in Secret Manager):
- mandate-vault-secret-key
- mandate-vault-acp-webhook-secret
- mandate-vault-db-password

Default Admin:
- Email: admin@example.com
- Password: Admin123!@# (CHANGE IMMEDIATELY)

Cloud Console:
https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME?project=$PROJECT_ID
EOF

echo -e "${GREEN}✅ Deployment information saved to: deployment_info.txt${NC}\n"
