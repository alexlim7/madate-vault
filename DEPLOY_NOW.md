# 🚀 Deploy Mandate Vault NOW - Step by Step

Choose your deployment method and follow the exact commands below.

---

## ⚡ FASTEST: Docker Compose (5 Minutes)

### Step 1: Generate Secrets
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Generate SECRET_KEY
python3 scripts/generate_secret_key.py

# Generate ACP_WEBHOOK_SECRET  
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate DB_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Copy the outputs from above and use them in the next step!**

### Step 2: Create .env File
```bash
cat > .env << 'EOF'
# Mandate Vault Environment
SECRET_KEY=<paste-secret-key-here>
ACP_WEBHOOK_SECRET=<paste-acp-secret-here>
DB_PASSWORD=<paste-db-password-here>

# Application
ENVIRONMENT=production
DEBUG=false

# CORS (update with your domain)
CORS_ORIGINS=http://localhost:3000

# Database (auto-configured)
DATABASE_URL=postgresql+asyncpg://mandate_user:${DB_PASSWORD}@db:5432/mandate_vault
EOF
```

**Edit the file and replace the `<paste-...>` values with your generated secrets!**

### Step 3: Deploy
```bash
# Start all services
docker-compose up -d

# Wait for services to start
sleep 15

# Run database migrations
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python scripts/seed_initial_data.py
```

### Step 4: Verify
```bash
# Check health
curl http://localhost:8000/healthz

# Open API docs in browser
open http://localhost:8000/docs
```

### 🎉 Done! Your API is running at: `http://localhost:8000`

**Default Admin Credentials:**
- Email: `admin@example.com`
- Password: `Admin123!@#`

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

---

## 🔧 Manage Your Deployment

### View Logs
```bash
docker-compose logs -f api
```

### Stop Services
```bash
docker-compose down
```

### Restart After Code Changes
```bash
docker-compose build api
docker-compose up -d api
```

### Backup Database
```bash
docker-compose exec db pg_dump -U mandate_user mandate_vault > backup_$(date +%Y%m%d).sql
```

### Run Smoke Tests
```bash
export TEST_EMAIL='admin@example.com'
export TEST_PASSWORD='Admin123!@#'
python3 scripts/smoke_authorizations.py
```

---

## ☁️ Alternative: Google Cloud Run (Production)

### Prerequisites
```bash
# Install gcloud CLI if not installed
# Visit: https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID
```

### One-Command Deploy
```bash
# Run the interactive deployment script
./scripts/quick_deploy.sh
```

Then select option `2) Google Cloud Run`

### Or Manual Deploy
```bash
# Set variables
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"

# Enable APIs
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com

# Generate and store secrets
python3 scripts/generate_secret_key.py | \
  gcloud secrets create mandate-vault-secret-key --data-file=-

python3 -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets create mandate-vault-acp-webhook-secret --data-file=-

# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/mandate-vault

gcloud run deploy mandate-vault \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --min-instances 1 \
  --set-env-vars ENVIRONMENT=production,DEBUG=false \
  --set-secrets SECRET_KEY=mandate-vault-secret-key:latest,ACP_WEBHOOK_SECRET=mandate-vault-acp-webhook-secret:latest

# Get URL
gcloud run services describe mandate-vault --region $REGION --format 'value(status.url)'
```

---

## 🐳 Alternative: Kubernetes

### Quick Deploy
```bash
# Generate secrets
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export ACP_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export DATABASE_URL="postgresql://user:pass@db-host:5432/dbname"

# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic mandate-vault-secrets \
  --namespace=mandate-vault \
  --from-literal=SECRET_KEY=$SECRET_KEY \
  --from-literal=ACP_WEBHOOK_SECRET=$ACP_SECRET \
  --from-literal=DATABASE_URL=$DATABASE_URL

# Deploy
kubectl apply -f k8s/

# Wait for ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/mandate-vault -n mandate-vault

# Port forward to test
kubectl port-forward svc/mandate-vault 8000:8000 -n mandate-vault
```

---

## 🆘 Troubleshooting

### Issue: "docker-compose: command not found"
**Solution:**
```bash
# Install Docker Desktop which includes Docker Compose
# Visit: https://www.docker.com/products/docker-desktop
```

### Issue: "Database connection failed"
**Solution:**
```bash
# Check if database is running
docker-compose ps db

# View database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Issue: "Health check failing"
**Solution:**
```bash
# Check API logs
docker-compose logs api

# Verify environment variables
docker-compose exec api env | grep SECRET_KEY

# Restart API
docker-compose restart api
```

### Issue: "Port already in use"
**Solution:**
```bash
# Stop any running instances
docker-compose down

# Or change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Change 8000 to 8001
```

---

## 📊 Next Steps After Deployment

### 1. Create Your First User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "YourSecurePassword123!",
    "full_name": "Your Name",
    "tenant_id": "your-company"
  }'
```

### 2. Get Access Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "YourSecurePassword123!"
  }'
```

### 3. Test Authorization Creation
```bash
# Save your token
export TOKEN="your-access-token-from-step-2"

# Create an ACP authorization
curl -X POST "http://localhost:8000/api/v1/authorizations/acp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "your-company",
    "token_id": "test-token-123",
    "issuer": "psp-test",
    "amount": "100.00",
    "currency": "USD"
  }'
```

### 4. Setup Monitoring
```bash
# Access Grafana
open http://localhost:3001

# Default credentials: admin/admin
# Import dashboards from: /config/grafana/
```

### 5. Configure Production Settings
```bash
# Edit .env file
nano .env

# Update these for production:
# - CORS_ORIGINS=https://your-actual-domain.com
# - SENTRY_DSN=your-sentry-dsn
# - FORCE_HTTPS=true
# - ENABLE_DOCS=false

# Restart to apply changes
docker-compose restart api
```

---

## 🎯 Success Criteria

Your deployment is successful if:

✅ Health check returns 200: `curl http://localhost:8000/healthz`  
✅ API docs accessible: `http://localhost:8000/docs`  
✅ Can login with admin credentials  
✅ Can create and verify authorizations  
✅ Grafana dashboards showing metrics  

---

## 📚 Additional Resources

- **Full Documentation**: `./docs/README.md`
- **API Reference**: `http://localhost:8000/docs`
- **Deployment Guide**: `./QUICK_DEPLOY.md`
- **Troubleshooting**: `./docs/guides/DEPLOYMENT_GUIDE.md`

---

## 🎉 You're All Set!

Your Mandate Vault is now deployed and ready to handle authorization storage and verification.

**Need Help?**
- Check logs: `docker-compose logs -f api`
- Run diagnostics: `python3 scripts/validate_environment.py`
- Interactive setup: `./scripts/quick_deploy.sh`

**Next Steps:**
1. Update CORS origins with your actual domain
2. Configure webhook endpoints for your PSPs
3. Setup SSL certificates for production
4. Configure monitoring alerts
5. Review security checklist: `./DEPLOYMENT_CHECKLIST.md`
