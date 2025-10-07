# 🚀 Quick Deployment Guide

This guide will help you deploy the Mandate Vault application. Choose the deployment option that best fits your needs.

---

## 🎯 Deployment Options

1. **Docker Compose** (Easiest - Local/Development/Small Production)
2. **Google Cloud Run** (Recommended - Production)
3. **Kubernetes** (Enterprise - Large Scale)

---

## Option 1: Docker Compose (5 Minutes) ⭐ EASIEST

Perfect for: Development, testing, small production workloads

### Prerequisites
- Docker & Docker Compose installed
- 4GB RAM available

### Steps

1. **Generate Secrets**
```bash
# Generate a secure secret key
python scripts/generate_secret_key.py

# Generate ACP webhook secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Create Environment File**
```bash
# Copy the example file
cp config/env.production.template .env

# Edit with your values
nano .env
```

Required variables:
```bash
# Security (REQUIRED)
SECRET_KEY=<output-from-step-1>
ACP_WEBHOOK_SECRET=<output-from-step-1>

# Database (auto-configured by docker-compose)
DB_PASSWORD=<choose-a-strong-password>

# Application
ENVIRONMENT=production
DEBUG=false

# Optional
CORS_ORIGINS=https://your-frontend-domain.com
SENTRY_DSN=<your-sentry-dsn>
```

3. **Deploy**
```bash
# Start all services (API, PostgreSQL, Redis, Prometheus, Grafana)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

4. **Initialize Database**
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python scripts/seed_initial_data.py
```

5. **Verify Deployment**
```bash
# Health check
curl http://localhost:8000/healthz

# API docs
open http://localhost:8000/docs

# Grafana dashboard
open http://localhost:3001  # admin/admin
```

**Done! 🎉** Your app is running at `http://localhost:8000`

### Manage Deployment

```bash
# Stop services
docker-compose down

# Update after code changes
docker-compose build api
docker-compose up -d api

# Backup database
docker-compose exec db pg_dump -U mandate_user mandate_vault > backup.sql

# View resource usage
docker stats
```

---

## Option 2: Google Cloud Run (Production) ⭐ RECOMMENDED

Perfect for: Production workloads, auto-scaling, serverless

### Prerequisites
- Google Cloud account with billing enabled
- `gcloud` CLI installed and configured
- Terraform installed (optional but recommended)

### Quick Deploy (Manual)

1. **Setup GCP Project**
```bash
# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

2. **Create Secrets**
```bash
# Generate and store SECRET_KEY
python scripts/generate_secret_key.py | \
  gcloud secrets create mandate-vault-secret-key --data-file=-

# Generate and store ACP_WEBHOOK_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets create mandate-vault-acp-webhook-secret --data-file=-

# Store database password
echo -n "your-db-password" | \
  gcloud secrets create mandate-vault-db-password --data-file=-
```

3. **Create Cloud SQL Instance**
```bash
# Create PostgreSQL instance
gcloud sql instances create mandate-vault-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create mandate_vault \
  --instance=mandate-vault-db

# Create user
gcloud sql users create mandate_user \
  --instance=mandate-vault-db \
  --password=$(gcloud secrets versions access latest --secret=mandate-vault-db-password)
```

4. **Build and Deploy**
```bash
# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/mandate-vault

# Deploy to Cloud Run
gcloud run deploy mandate-vault \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production,DEBUG=false \
  --set-secrets SECRET_KEY=mandate-vault-secret-key:latest,\
ACP_WEBHOOK_SECRET=mandate-vault-acp-webhook-secret:latest \
  --add-cloudsql-instances $PROJECT_ID:us-central1:mandate-vault-db
```

5. **Run Migrations**
```bash
# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe mandate-vault \
  --region us-central1 \
  --format 'value(status.url)')

# Run migrations (using Cloud Run Jobs)
gcloud run jobs create mandate-vault-migrate \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --region us-central1 \
  --command alembic \
  --args upgrade,head \
  --set-secrets SECRET_KEY=mandate-vault-secret-key:latest \
  --add-cloudsql-instances $PROJECT_ID:us-central1:mandate-vault-db

gcloud run jobs execute mandate-vault-migrate --region us-central1
```

**Done! 🎉** Your app is running at the Cloud Run URL

### Deploy with Terraform (Recommended)

```bash
# Navigate to terraform directory
cd terraform

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply

# Get outputs
terraform output
```

---

## Option 3: Kubernetes (Enterprise)

Perfect for: Large scale, multi-region, on-premises

### Prerequisites
- Kubernetes cluster (GKE, EKS, AKS, or self-hosted)
- `kubectl` configured
- Helm (optional)

### Deploy

1. **Create Namespace**
```bash
kubectl apply -f k8s/namespace.yaml
```

2. **Configure Secrets**
```bash
# Create secret for app
kubectl create secret generic mandate-vault-secrets \
  --namespace=mandate-vault \
  --from-literal=SECRET_KEY=$(python scripts/generate_secret_key.py) \
  --from-literal=ACP_WEBHOOK_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))") \
  --from-literal=DATABASE_URL="postgresql://user:pass@db-host:5432/dbname"
```

3. **Deploy Application**
```bash
# Deploy all resources
kubectl apply -f k8s/

# Check status
kubectl get pods -n mandate-vault

# View logs
kubectl logs -f deployment/mandate-vault -n mandate-vault
```

4. **Run Migrations**
```bash
# Create migration job
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: mandate-vault-migrate
  namespace: mandate-vault
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: mandate-vault:latest
        command: ["alembic", "upgrade", "head"]
        envFrom:
        - secretRef:
            name: mandate-vault-secrets
      restartPolicy: Never
EOF

# Check migration status
kubectl logs job/mandate-vault-migrate -n mandate-vault
```

5. **Access Application**
```bash
# Port forward for testing
kubectl port-forward svc/mandate-vault 8000:8000 -n mandate-vault

# Or get LoadBalancer IP
kubectl get svc mandate-vault -n mandate-vault
```

**Done! 🎉** Your app is running on Kubernetes

---

## 🔧 Post-Deployment Tasks

### 1. Create Admin User

```bash
# Docker Compose
docker-compose exec api python scripts/seed_initial_data.py

# Cloud Run (using gcloud)
gcloud run jobs create seed-data \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --region us-central1 \
  --command python \
  --args scripts/seed_initial_data.py

# Kubernetes
kubectl exec -it deployment/mandate-vault -n mandate-vault -- \
  python scripts/seed_initial_data.py
```

### 2. Configure Monitoring

```bash
# Docker Compose - Already included!
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090

# Cloud Run - Use Google Cloud Monitoring
# https://console.cloud.google.com/monitoring

# Kubernetes - Deploy Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

### 3. Setup Alerts

Edit `config/alerts.yml` and configure:
- Slack webhook for notifications
- PagerDuty integration
- Email alerts

### 4. Backup Strategy

```bash
# Docker Compose
./scripts/backup_database.sh

# Cloud Run (automatic backups enabled)
gcloud sql backups list --instance=mandate-vault-db

# Kubernetes
kubectl apply -f k8s/cronjob-backup.yaml
```

---

## 🧪 Verify Deployment

### Run Smoke Tests

```bash
# Set environment variables
export TEST_EMAIL='admin@example.com'
export TEST_PASSWORD='your-password'
export API_URL='http://your-deployment-url'

# Run smoke tests
python scripts/smoke_authorizations.py
python scripts/smoke_acp_webhooks.py
python scripts/smoke_evidence_export.py
```

### Health Checks

```bash
# Health endpoint
curl https://your-url/healthz

# Readiness endpoint
curl https://your-url/readyz

# API documentation
open https://your-url/docs
```

---

## 📊 Monitoring Your Deployment

### Key Metrics to Watch

- **Request Rate**: Should be under your rate limit
- **Response Time**: P95 < 500ms, P99 < 1s
- **Error Rate**: < 0.1%
- **Database Connections**: Should not hit max
- **Memory Usage**: Should be < 80% of allocated

### Access Logs

```bash
# Docker Compose
docker-compose logs -f api

# Cloud Run
gcloud run services logs tail mandate-vault --region us-central1

# Kubernetes
kubectl logs -f deployment/mandate-vault -n mandate-vault
```

---

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Failed**
```bash
# Check database is running
# Docker Compose:
docker-compose ps db

# Verify DATABASE_URL is correct
# Check database credentials in secrets
```

2. **Health Check Failing**
```bash
# Check application logs
# Verify SECRET_KEY is set
# Ensure database migrations have run
```

3. **High Memory Usage**
```bash
# Increase memory allocation
# Docker Compose: Edit docker-compose.yml
# Cloud Run: Use --memory flag
# Kubernetes: Edit deployment.yaml resources
```

4. **Rate Limiting Issues**
```bash
# Adjust rate limits in app/core/config.py
# Or use environment variables
```

### Get Help

- 📖 Check docs: `./docs/`
- 🐛 Report issues: GitHub Issues
- 💬 Community: Discord/Slack

---

## 🎯 Next Steps

1. **Setup Custom Domain**
   - Configure DNS
   - Setup SSL certificates
   - Update CORS settings

2. **Enable Monitoring**
   - Configure Sentry
   - Setup Grafana dashboards
   - Configure alerts

3. **Performance Tuning**
   - Adjust worker count
   - Configure caching
   - Optimize database queries

4. **Security Hardening**
   - Enable WAF
   - Setup VPN/firewall rules
   - Configure IP allowlists

---

**Need help? Run the interactive setup wizard:**
```bash
python scripts/setup_wizard.py
```
