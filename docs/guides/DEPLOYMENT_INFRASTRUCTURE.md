# Deployment Infrastructure Guide

Complete guide for deploying Mandate Vault across different environments using Docker, Kubernetes, and CI/CD.

---

## 📋 Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Staging Environment](#staging-environment)
6. [Production Deployment](#production-deployment)
7. [Terraform Infrastructure](#terraform-infrastructure)

---

## 🏠 Local Development

### Using Docker Compose

**Start all services:**
```bash
# Create .env file
cp config/env.development.template .env

# Edit .env with your values
nano .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

**Services started:**
- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`

**Run migrations:**
```bash
docker-compose exec api alembic upgrade head
```

**Access database:**
```bash
docker-compose exec db psql -U mandate_user -d mandate_vault
```

### Without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
export SECRET_KEY="your-secret-key"
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/mandate_vault"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build
docker build -t mandate-vault:latest .

# Build with specific tag
docker build -t mandate-vault:v1.0.0 .

# Build with build args
docker build \
  --build-arg PYTHON_VERSION=3.9 \
  -t mandate-vault:latest .
```

### Run Container

```bash
# Run with environment variables
docker run -d \
  --name mandate-vault \
  -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e DATABASE_URL="postgresql://..." \
  -e ENVIRONMENT="production" \
  mandate-vault:latest

# Run with env file
docker run -d \
  --name mandate-vault \
  -p 8000:8000 \
  --env-file .env.production \
  mandate-vault:latest

# View logs
docker logs -f mandate-vault

# Execute commands
docker exec -it mandate-vault python -c "print('Hello')"
```

### Docker Compose Production

```bash
# Use production profile
docker-compose --profile production up -d

# Scale API instances
docker-compose up -d --scale api=3

# Update single service
docker-compose up -d --no-deps api
```

### Push to Registry

```bash
# Google Container Registry
docker tag mandate-vault:latest gcr.io/PROJECT_ID/mandate-vault:latest
docker push gcr.io/PROJECT_ID/mandate-vault:latest

# AWS ECR
docker tag mandate-vault:latest AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/mandate-vault:latest
docker push AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/mandate-vault:latest

# Docker Hub
docker tag mandate-vault:latest username/mandate-vault:latest
docker push username/mandate-vault:latest
```

---

## ☸️ Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
brew install kubectl  # macOS
# or download from https://kubernetes.io/docs/tasks/tools/

# Install helm (optional)
brew install helm

# Verify cluster access
kubectl cluster-info
kubectl get nodes
```

### Deploy to Kubernetes

**Step 1: Create namespace**
```bash
kubectl apply -f k8s/namespace.yaml
```

**Step 2: Create secrets**
```bash
# Generate secret key
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Create secret
kubectl create secret generic mandate-vault-secrets \
  --namespace=mandate-vault \
  --from-literal=secret-key="$SECRET_KEY" \
  --from-literal=database-url="postgresql+asyncpg://..." \
  --from-literal=sentry-dsn="https://..."
```

**Step 3: Apply manifests**
```bash
# Apply all at once
kubectl apply -f k8s/

# Or step by step
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

**Step 4: Verify deployment**
```bash
# Check pods
kubectl get pods -n mandate-vault

# Check deployment
kubectl get deployment -n mandate-vault

# Check service
kubectl get service -n mandate-vault

# View logs
kubectl logs -f deployment/mandate-vault -n mandate-vault

# Describe pod
kubectl describe pod POD_NAME -n mandate-vault
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/mandate-vault \
  api=gcr.io/PROJECT/mandate-vault:v1.1.0 \
  -n mandate-vault

# Check rollout status
kubectl rollout status deployment/mandate-vault -n mandate-vault

# Rollback if needed
kubectl rollout undo deployment/mandate-vault -n mandate-vault

# View rollout history
kubectl rollout history deployment/mandate-vault -n mandate-vault
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment mandate-vault --replicas=5 -n mandate-vault

# Autoscaling (HPA already configured)
kubectl get hpa -n mandate-vault

# Watch autoscaling
kubectl get hpa -n mandate-vault --watch
```

### Debugging

```bash
# Get pod shell
kubectl exec -it POD_NAME -n mandate-vault -- /bin/sh

# Port forward
kubectl port-forward deployment/mandate-vault 8000:8000 -n mandate-vault

# View events
kubectl get events -n mandate-vault --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n mandate-vault
kubectl top nodes
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions

**Workflows:**
- `.github/workflows/ci.yml` - Continuous Integration
- `.github/workflows/cd.yml` - Continuous Deployment

**CI Workflow (on push/PR):**
1. Lint code (flake8, black, isort)
2. Run unit tests
3. Run integration tests
4. Security scan (Trivy, Safety)
5. Build Docker image
6. Upload coverage

**CD Workflow (on tag/main):**
1. Build and push Docker image
2. Deploy to staging (Cloud Run)
3. Run smoke tests
4. Deploy to production (GKE)
5. Run health checks
6. Notify team (Slack)

### Required Secrets

Configure in GitHub Repository Settings → Secrets:

```
GCP_PROJECT_ID        - Google Cloud project ID
GCP_SA_KEY            - Service account JSON key
SLACK_WEBHOOK         - Slack webhook URL
CODECOV_TOKEN         - Codecov token
```

### Trigger Deployment

```bash
# Deploy to staging (push to main)
git push origin main

# Deploy to production (create tag)
git tag v1.0.0
git push origin v1.0.0

# View workflow
# Go to: https://github.com/YOUR_REPO/actions
```

### Manual Deployment

```bash
# Run workflow manually
gh workflow run cd.yml

# List runs
gh run list --workflow=cd.yml

# View run logs
gh run view RUN_ID --log
```

---

## 🧪 Staging Environment

### Purpose

Staging environment mirrors production for final testing before release.

**Differences from production:**
- Lower resource limits
- Test data
- More relaxed monitoring
- Swagger UI enabled

### Setup Staging

**Option 1: Cloud Run (GCP)**
```bash
# Deploy with Terraform
cd terraform
terraform workspace new staging
terraform apply -var="environment=staging"

# Or manually
gcloud run deploy mandate-vault-staging \
  --image gcr.io/PROJECT/mandate-vault:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=staging
```

**Option 2: Kubernetes Namespace**
```bash
# Create staging namespace
kubectl create namespace mandate-vault-staging

# Apply manifests
kubectl apply -f k8s/ -n mandate-vault-staging

# Update ConfigMap for staging
kubectl patch configmap mandate-vault-config \
  -n mandate-vault-staging \
  -p '{"data":{"ENVIRONMENT":"staging"}}'
```

### Access Staging

```
Staging URL: https://staging-api.yourdomain.com
Swagger UI: https://staging-api.yourdomain.com/docs
Metrics: https://staging-api.yourdomain.com/api/v1/metrics
```

### Promote to Production

```bash
# 1. Test staging thoroughly
curl https://staging-api.yourdomain.com/healthz

# 2. Tag release
git tag v1.0.0
git push origin v1.0.0

# 3. CI/CD automatically deploys to production

# 4. Verify production
curl https://api.yourdomain.com/healthz
```

---

## 🚀 Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Security scan clean
- [ ] Performance benchmarks met
- [ ] Database backup created
- [ ] Secrets rotated (if scheduled)
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Runbooks updated
- [ ] Team notified

### Deployment Strategies

#### Blue-Green Deployment

```bash
# Deploy new version (green)
kubectl apply -f k8s/deployment-green.yaml

# Switch traffic
kubectl patch service mandate-vault \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback if needed
kubectl patch service mandate-vault \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

#### Canary Deployment

```bash
# Deploy canary (10% traffic)
kubectl apply -f k8s/deployment-canary.yaml

# Monitor metrics
kubectl get pods -l version=canary -n mandate-vault

# Gradually increase traffic
# Update ingress weights: 10% → 25% → 50% → 100%

# Promote canary to stable
kubectl apply -f k8s/deployment.yaml
```

### Production Best Practices

1. **Always use tagged images** (not :latest)
2. **Deploy during low-traffic hours**
3. **Monitor metrics during deployment**
4. **Have rollback plan ready**
5. **Notify team before/after**
6. **Test health endpoints**
7. **Check logs for errors**

### Post-Deployment

```bash
# Verify deployment
kubectl get pods -n mandate-vault
kubectl logs -f deployment/mandate-vault -n mandate-vault

# Check metrics
curl https://api.yourdomain.com/api/v1/metrics

# Monitor dashboards
# Grafana: https://grafana.yourdomain.com
# Sentry: https://sentry.io/organizations/YOUR_ORG

# Run smoke tests
pytest tests/e2e/ --base-url=https://api.yourdomain.com
```

---

## 🏗️ Terraform Infrastructure

### Setup Terraform

```bash
# Install Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# Initialize
cd terraform
terraform init

# Create workspace
terraform workspace new production
terraform workspace new staging
```

### Deploy Infrastructure

```bash
# Plan changes
terraform plan -var="project_id=YOUR_PROJECT" -var="environment=production"

# Apply changes
terraform apply -var="project_id=YOUR_PROJECT" -var="environment=production"

# Destroy (careful!)
terraform destroy -var="project_id=YOUR_PROJECT" -var="environment=staging"
```

### State Management

```bash
# Create GCS bucket for state
gsutil mb gs://mandate-vault-terraform-state

# Enable versioning
gsutil versioning set on gs://mandate-vault-terraform-state

# State is automatically stored in GCS
```

### Terraform Outputs

```bash
# View outputs
terraform output

# Get specific output
terraform output database_connection_name

# Use output in script
DB_URL=$(terraform output -raw database_connection_name)
```

---

## 📊 Monitoring Deployment

### Health Checks

```bash
# Kubernetes liveness
kubectl get pods -n mandate-vault

# Application health
curl https://api.yourdomain.com/healthz

# Database connectivity
curl https://api.yourdomain.com/readyz

# Metrics
curl https://api.yourdomain.com/api/v1/metrics
```

### View Logs

```bash
# Kubernetes
kubectl logs -f deployment/mandate-vault -n mandate-vault

# Cloud Run
gcloud run services logs read mandate-vault --region us-central1

# Docker
docker-compose logs -f api
```

### Metrics & Dashboards

- **Prometheus**: `http://localhost:9090` (local) or your Prometheus URL
- **Grafana**: `http://localhost:3001` (local) or your Grafana URL
- **Sentry**: https://sentry.io (if configured)

---

## 🔧 Troubleshooting

### Pod Won't Start

```bash
# Describe pod
kubectl describe pod POD_NAME -n mandate-vault

# Check events
kubectl get events -n mandate-vault

# Check image pull
kubectl get pods -n mandate-vault -o jsonpath='{.items[*].status.containerStatuses[*].state}'
```

### Database Connection Issues

```bash
# Test from pod
kubectl exec -it POD_NAME -n mandate-vault -- python -c "
from app.core.database import check_database_connection
import asyncio
asyncio.run(check_database_connection())
"

# Check secrets
kubectl get secret mandate-vault-secrets -n mandate-vault -o yaml
```

### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n mandate-vault

# Reduce workers
kubectl set env deployment/mandate-vault \
  WORKERS=2 \
  -n mandate-vault
```

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Terraform Documentation](https://www.terraform.io/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Cloud Documentation](https://cloud.google.com/docs)

---

**Last Updated:** October 2025  
**Version:** 1.0.0

