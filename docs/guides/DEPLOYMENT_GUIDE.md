# Deployment Guide

Complete guide for deploying Mandate Vault to various platforms and environments.

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Google Cloud Run](#google-cloud-run)
4. [AWS (ECS/Fargate)](#aws-ecsfargate)
5. [Azure App Service](#azure-app-service)
6. [Docker](#docker)
7. [Kubernetes](#kubernetes)
8. [Traditional VPS](#traditional-vps)

---

## ✅ Pre-Deployment Checklist

Before deploying to production, complete this checklist:

### Configuration
- [ ] Generated secure SECRET_KEY (32+ characters)
- [ ] Configured PostgreSQL database (not SQLite)
- [ ] Set ENVIRONMENT=production
- [ ] Set DEBUG=False
- [ ] Configured CORS_ORIGINS with actual domains
- [ ] Set ALLOWED_HOSTS correctly
- [ ] Validated configuration: `python scripts/validate_environment.py`

### Database
- [ ] PostgreSQL instance created and configured
- [ ] Database migrations run: `alembic upgrade head`
- [ ] Initial data seeded if needed
- [ ] Backup strategy configured
- [ ] Connection pooling configured (20+ connections)

### Security
- [ ] Secrets stored in secrets manager (not .env file)
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Database in private network
- [ ] Rate limiting enabled
- [ ] Security headers enabled

### Monitoring
- [ ] Error tracking configured (Sentry)
- [ ] Logging configured and aggregated
- [ ] Health check endpoints tested (`/healthz`, `/readyz`)
- [ ] Alerts configured for critical errors
- [ ] Uptime monitoring enabled

### Testing
- [ ] All tests passing: `pytest tests/`
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] End-to-end tests passing

---

## 🌍 Environment Setup

### 1. Generate Secure Keys

```bash
python scripts/generate_secret_key.py
```

### 2. Create Environment File

```bash
# For development
cp config/env.development.template .env

# For production (use secrets manager instead!)
cp config/env.production.template .env.production
```

### 3. Validate Configuration

```bash
# Load environment
export $(cat .env | xargs)

# Validate
python scripts/validate_environment.py
```

---

## ☁️ Google Cloud Run

### Prerequisites

- Google Cloud account
- `gcloud` CLI installed
- Project created

### 1. Setup Cloud SQL (PostgreSQL)

```bash
# Create Cloud SQL instance
gcloud sql instances create mandate-vault-db \
  --database-version=POSTGRES_14 \
  --tier=db-g1-small \
  --region=us-central1 \
  --network=default \
  --backup \
  --backup-start-time=03:00

# Create database
gcloud sql databases create mandate_vault \
  --instance=mandate-vault-db

# Create user
gcloud sql users create mandate_user \
  --instance=mandate-vault-db \
  --password=SECURE_PASSWORD
```

### 2. Setup Secrets

```bash
# Enable Secret Manager
gcloud services enable secretmanager.googleapis.com

# Create secrets
echo "YOUR_SECURE_SECRET_KEY" | gcloud secrets create mandate-vault-secret-key --data-file=-
echo "postgresql+asyncpg://mandate_user:PASSWORD@/mandate_vault?host=/cloudsql/PROJECT:REGION:mandate-vault-db" | \
  gcloud secrets create mandate-vault-database-url --data-file=-
```

### 3. Build and Deploy

```bash
# Build image
gcloud builds submit --tag gcr.io/PROJECT_ID/mandate-vault

# Deploy to Cloud Run
gcloud run deploy mandate-vault \
  --image gcr.io/PROJECT_ID/mandate-vault \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-cloudsql-instances=PROJECT_ID:us-central1:mandate-vault-db \
  --update-secrets=SECRET_KEY=mandate-vault-secret-key:latest \
  --update-secrets=DATABASE_URL=mandate-vault-database-url:latest \
  --set-env-vars ENVIRONMENT=production,DEBUG=False \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300
```

### 4. Run Migrations

```bash
# Connect to Cloud SQL
gcloud sql connect mandate-vault-db --user=mandate_user

# Or use Cloud SQL Proxy
./cloud_sql_proxy -instances=PROJECT:REGION:mandate-vault-db=tcp:5432 &

# Run migrations
DATABASE_URL="postgresql://mandate_user:PASSWORD@localhost:5432/mandate_vault" \
  alembic upgrade head
```

---

## 🚀 AWS (ECS/Fargate)

### 1. Setup RDS (PostgreSQL)

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier mandate-vault-db \
  --db-instance-class db.t3.small \
  --engine postgres \
  --engine-version 14 \
  --master-username mandate_user \
  --master-user-password SECURE_PASSWORD \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-XXXXX \
  --backup-retention-period 7 \
  --storage-encrypted
```

### 2. Setup Secrets Manager

```bash
# Create secrets
aws secretsmanager create-secret \
  --name mandate-vault/secret-key \
  --secret-string "YOUR_SECURE_KEY"

aws secretsmanager create-secret \
  --name mandate-vault/database-url \
  --secret-string "postgresql+asyncpg://user:pass@rds-endpoint:5432/mandate_vault"
```

### 3. Create ECS Task Definition

**task-definition.json:**
```json
{
  "family": "mandate-vault",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [{
    "name": "mandate-vault-api",
    "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/mandate-vault:latest",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"},
      {"name": "DEBUG", "value": "False"}
    ],
    "secrets": [
      {
        "name": "SECRET_KEY",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:mandate-vault/secret-key"
      },
      {
        "name": "DATABASE_URL",
        "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:mandate-vault/database-url"
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/mandate-vault",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "api"
      }
    }
  }]
}
```

### 4. Deploy

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name mandate-vault-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster mandate-vault-cluster \
  --service-name mandate-vault \
  --task-definition mandate-vault \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

## 🔵 Azure App Service

### 1. Setup Azure Database for PostgreSQL

```bash
# Create PostgreSQL server
az postgres server create \
  --resource-group mandate-vault-rg \
  --name mandate-vault-db \
  --location eastus \
  --admin-user mandate_user \
  --admin-password SECURE_PASSWORD \
  --sku-name B_Gen5_1 \
  --storage-size 51200 \
  --backup-retention 7

# Create database
az postgres db create \
  --resource-group mandate-vault-rg \
  --server-name mandate-vault-db \
  --name mandate_vault
```

### 2. Setup Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name mandate-vault-kv \
  --resource-group mandate-vault-rg \
  --location eastus

# Add secrets
az keyvault secret set \
  --vault-name mandate-vault-kv \
  --name SECRET-KEY \
  --value "YOUR_SECURE_KEY"
```

### 3. Deploy App Service

```bash
# Create App Service Plan
az appservice plan create \
  --name mandate-vault-plan \
  --resource-group mandate-vault-rg \
  --is-linux \
  --sku B1

# Create Web App
az webapp create \
  --resource-group mandate-vault-rg \
  --plan mandate-vault-plan \
  --name mandate-vault \
  --deployment-container-image-name mandate-vault:latest

# Configure environment
az webapp config appsettings set \
  --resource-group mandate-vault-rg \
  --name mandate-vault \
  --settings \
    ENVIRONMENT=production \
    DEBUG=False \
    SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://mandate-vault-kv.vault.azure.net/secrets/SECRET-KEY/)
```

---

## 🐳 Docker

### 1. Create Docker Compose for Production

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  api:
    image: mandate-vault:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql+asyncpg://mandate_user:${DB_PASSWORD}@db:5432/mandate_vault
    depends_on:
      - db
    restart: unless-stopped
    
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=mandate_vault
      - POSTGRES_USER=mandate_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### 2. Deploy

```bash
# Generate secrets
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
export DB_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec api alembic upgrade head
```

---

## ☸️ Kubernetes

### 1. Create Secrets

```bash
# Create namespace
kubectl create namespace mandate-vault

# Create secrets
kubectl create secret generic mandate-vault-secrets \
  --namespace=mandate-vault \
  --from-literal=secret-key="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --from-literal=database-url="postgresql+asyncpg://user:pass@postgres:5432/mandate_vault"
```

### 2. Create Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mandate-vault
  namespace: mandate-vault
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mandate-vault
  template:
    metadata:
      labels:
        app: mandate-vault
    spec:
      containers:
      - name: api
        image: mandate-vault:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DEBUG
          value: "False"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: mandate-vault-secrets
              key: secret-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mandate-vault-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: mandate-vault
  namespace: mandate-vault
spec:
  selector:
    app: mandate-vault
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 3. Deploy

```bash
kubectl apply -f deployment.yaml
```

---

## 💻 Traditional VPS

### 1. Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python
sudo apt-get install python3.9 python3.9-venv python3.9-dev -y

# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib -y

# Install Nginx
sudo apt-get install nginx -y
```

### 2. Setup Application

```bash
# Clone repository
git clone https://github.com/your-org/mandate-vault.git
cd mandate-vault

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL
./scripts/setup_postgres.sh

# Generate secrets
python scripts/generate_secret_key.py

# Create .env file
cp config/env.production.template .env
# Edit .env with your values

# Validate configuration
python scripts/validate_environment.py

# Run migrations
alembic upgrade head

# Seed initial data
python seed_initial_data.py
```

### 3. Setup Systemd Service

**`/etc/systemd/system/mandate-vault.service`:**
```ini
[Unit]
Description=Mandate Vault API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/mandate-vault
Environment="PATH=/opt/mandate-vault/venv/bin"
EnvironmentFile=/opt/mandate-vault/.env
ExecStart=/opt/mandate-vault/venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level warning

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable mandate-vault
sudo systemctl start mandate-vault
sudo systemctl status mandate-vault
```

### 4. Setup Nginx Reverse Proxy

**`/etc/nginx/sites-available/mandate-vault`:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    
    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check (bypass auth)
    location /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mandate-vault /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔍 Post-Deployment Verification

### 1. Health Checks

```bash
# Basic health
curl https://api.yourdomain.com/healthz

# Database connectivity
curl https://api.yourdomain.com/readyz
```

### 2. API Functionality

```bash
# Create test customer
curl -X POST https://api.yourdomain.com/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Company", "email": "test@example.com"}'

# Login
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@testcompany.com", "password": "AdminPass123!"}'
```

### 3. Performance Test

```bash
# Simple load test
ab -n 1000 -c 10 https://api.yourdomain.com/healthz
```

---

## 🔧 Troubleshooting

### Application Won't Start

```bash
# Check logs
docker logs mandate-vault  # Docker
kubectl logs -f deployment/mandate-vault  # Kubernetes
journalctl -u mandate-vault -f  # Systemd

# Common issues:
# 1. SECRET_KEY not set or too short
# 2. DATABASE_URL incorrect
# 3. Database not accessible
# 4. Port already in use
```

### Database Connection Fails

```bash
# Test connection manually
psql "postgresql://user:pass@host:5432/db"

# Check firewall
telnet db-host 5432

# Verify credentials in secrets manager
```

### High Memory Usage

```bash
# Reduce workers
uvicorn app.main:app --workers 2

# Reduce connection pool
# In app/core/database.py: pool_size = 10
```

---

## 📊 Scaling

### Vertical Scaling

| Environment | vCPU | RAM | Database | Users |
|-------------|------|-----|----------|-------|
| Dev/Test | 1 | 1GB | db.t3.micro | 1-10 |
| Small Prod | 2 | 2GB | db.t3.small | 100 |
| Medium Prod | 4 | 4GB | db.t3.medium | 1,000 |
| Large Prod | 8 | 8GB | db.t3.large | 10,000 |

### Horizontal Scaling

```yaml
# Kubernetes autoscaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mandate-vault
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mandate-vault
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

**Last Updated:** October 2025  
**Version:** 1.0.0

