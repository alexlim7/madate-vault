# ☁️ Cloud Deployment Options for Mandate Vault

Since you want actual production deployment (not localhost), here are your best options:

---

## 🚀 Option 1: Google Cloud Run (Recommended) ⭐

### Method A: Using Google Cloud Console (No CLI Required)

This is the **easiest** way to deploy without installing anything locally!

#### Step 1: Setup Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable billing (first-time users get $300 free credits)

#### Step 2: Enable Required APIs

1. Go to [APIs & Services](https://console.cloud.google.com/apis/dashboard)
2. Click "Enable APIs and Services"
3. Enable these APIs:
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Build API
   - Secret Manager API
   - Artifact Registry API

#### Step 3: Create Secrets

1. Go to [Secret Manager](https://console.cloud.google.com/security/secret-manager)
2. Click "Create Secret"
3. Create these three secrets:

   **SECRET_KEY:**
   ```
   Name: mandate-vault-secret-key
   Value: <generate using: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
   ```

   **ACP_WEBHOOK_SECRET:**
   ```
   Name: mandate-vault-acp-webhook-secret
   Value: <generate using: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
   ```

   **DB_PASSWORD:**
   ```
   Name: mandate-vault-db-password
   Value: <generate using: python3 -c "import secrets; print(secrets.token_urlsafe(24))">
   ```

#### Step 4: Create Cloud SQL Database

1. Go to [Cloud SQL](https://console.cloud.google.com/sql/instances)
2. Click "Create Instance"
3. Choose "PostgreSQL"
4. Configure:
   - Instance ID: `mandate-vault-db`
   - Password: (use the one from Secret Manager)
   - Version: PostgreSQL 14
   - Region: `us-central1`
   - Tier: `db-f1-micro` (for testing) or `db-custom-2-7680` (for production)
   - Storage: 10GB (autoscaling enabled)
5. Click "Create"
6. Once created, create a database:
   - Database name: `mandate_vault`
   - Click "Create"
7. Create a user:
   - Username: `mandate_user`
   - Password: (use the DB_PASSWORD from Secret Manager)

#### Step 5: Deploy via Cloud Shell (Browser-Based)

1. Go to your [Cloud Console](https://console.cloud.google.com)
2. Click the "Activate Cloud Shell" button (top right, terminal icon)
3. In Cloud Shell, run these commands:

```bash
# Clone your repository or upload the code
# For this example, we'll assume you upload the code to Cloud Shell

# Upload your mandate_vault folder using the Cloud Shell upload feature
# Click the three dots ⋮ > Upload > Select folder

# Navigate to the folder
cd mandate_vault

# Set your project ID
export PROJECT_ID="your-project-id"  # Replace with your actual project ID
gcloud config set project $PROJECT_ID

# Build and submit container
gcloud builds submit --tag gcr.io/$PROJECT_ID/mandate-vault

# Create VPC connector for Cloud SQL access
gcloud compute networks vpc-access connectors create mandate-vault-connector \
  --region=us-central1 \
  --range=10.8.0.0/28

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
  --vpc-connector mandate-vault-connector \
  --add-cloudsql-instances $PROJECT_ID:us-central1:mandate-vault-db \
  --set-secrets "SECRET_KEY=mandate-vault-secret-key:latest,ACP_WEBHOOK_SECRET=mandate-vault-acp-webhook-secret:latest" \
  --set-env-vars "ENVIRONMENT=production,DEBUG=false,DATABASE_URL=postgresql+asyncpg://mandate_user:YOUR_DB_PASSWORD@/mandate_vault?host=/cloudsql/$PROJECT_ID:us-central1:mandate-vault-db"

# Get the service URL
gcloud run services describe mandate-vault --region us-central1 --format 'value(status.url)'
```

4. **Run Database Migrations:**

```bash
# Create and run migration job
gcloud run jobs create mandate-vault-migrate \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --region us-central1 \
  --vpc-connector mandate-vault-connector \
  --add-cloudsql-instances $PROJECT_ID:us-central1:mandate-vault-db \
  --set-env-vars "DATABASE_URL=postgresql+asyncpg://mandate_user:YOUR_DB_PASSWORD@/mandate_vault?host=/cloudsql/$PROJECT_ID:us-central1:mandate-vault-db" \
  --command alembic \
  --args upgrade,head

gcloud run jobs execute mandate-vault-migrate --region us-central1 --wait
```

5. **Create Admin User:**

```bash
# Create and run seed data job
gcloud run jobs create mandate-vault-seed \
  --image gcr.io/$PROJECT_ID/mandate-vault \
  --region us-central1 \
  --vpc-connector mandate-vault-connector \
  --add-cloudsql-instances $PROJECT_ID:us-central1:mandate-vault-db \
  --set-env-vars "DATABASE_URL=postgresql+asyncpg://mandate_user:YOUR_DB_PASSWORD@/mandate_vault?host=/cloudsql/$PROJECT_ID:us-central1:mandate-vault-db" \
  --set-secrets "SECRET_KEY=mandate-vault-secret-key:latest" \
  --command python \
  --args scripts/seed_initial_data.py

gcloud run jobs execute mandate-vault-seed --region us-central1 --wait
```

**Done! Your API is live!**

---

## 🔷 Option 2: Render.com (Easiest - No GCP Account Needed)

Render is super simple and has a generous free tier!

### Step 1: Create Account
1. Go to [Render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Connect GitHub Repository
1. Push your code to GitHub
2. In Render dashboard, click "New +"
3. Select "Web Service"
4. Connect your GitHub repository

### Step 3: Configure Service
```yaml
Name: mandate-vault
Environment: Docker
Region: Oregon (US West)
Instance Type: Starter ($7/month) or Free
```

### Step 4: Add Environment Variables
```
SECRET_KEY=<generated-secret>
ACP_WEBHOOK_SECRET=<generated-secret>
DATABASE_URL=<postgres-url-from-render>
ENVIRONMENT=production
DEBUG=false
```

### Step 5: Add PostgreSQL Database
1. Click "New +"
2. Select "PostgreSQL"
3. Copy the Internal Database URL
4. Paste it as DATABASE_URL in your web service

### Step 6: Deploy
1. Click "Create Web Service"
2. Wait for deployment (5-10 minutes)
3. Your API will be live at: `https://mandate-vault.onrender.com`

**Total Cost: $7/month (Starter) or Free tier available**

---

## 🐳 Option 3: Railway.app (Developer-Friendly)

Railway is modern, simple, and great for production.

### Step 1: Setup
1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub
3. Create new project

### Step 2: Add PostgreSQL
1. Click "New"
2. Select "Database" → "PostgreSQL"
3. Copy the connection string

### Step 3: Deploy from GitHub
1. Click "New"
2. Select "GitHub Repo"
3. Connect your mandate_vault repository
4. Railway auto-detects Dockerfile

### Step 4: Add Environment Variables
```
SECRET_KEY=<generated>
ACP_WEBHOOK_SECRET=<generated>
DATABASE_URL=${{Postgres.DATABASE_URL}}
ENVIRONMENT=production
DEBUG=false
```

### Step 5: Deploy
- Railway automatically deploys
- Get your URL from the deployment
- Your API is live!

**Total Cost: $5/month (Developer plan) + usage**

---

## ☁️ Option 4: Heroku (Classic, Reliable)

### Step 1: Install Heroku CLI
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Or use the installer from heroku.com
```

### Step 2: Deploy
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Login to Heroku
heroku login

# Create app
heroku create mandate-vault-prod

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
heroku config:set ACP_WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG=false

# Deploy
git push heroku main

# Run migrations
heroku run alembic upgrade head

# Create admin user
heroku run python scripts/seed_initial_data.py

# Open your app
heroku open
```

**Total Cost: ~$7/month (Eco Dynos)**

---

## 🌐 Option 5: DigitalOcean App Platform

### Step 1: Setup
1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect GitHub repository

### Step 2: Configure
- Detected: Dockerfile ✓
- Plan: Basic ($5/month)
- Add PostgreSQL database ($15/month for Managed DB, or $7 for dev)

### Step 3: Environment Variables
Add in the console:
```
SECRET_KEY
ACP_WEBHOOK_SECRET
DATABASE_URL (auto-configured)
ENVIRONMENT=production
DEBUG=false
```

### Step 4: Deploy
- Click "Deploy"
- Wait 5-10 minutes
- Your API is live!

**Total Cost: $12-20/month**

---

## 📊 Comparison Table

| Platform | Ease of Setup | Cost/Month | Free Tier | Best For |
|----------|--------------|------------|-----------|----------|
| **Google Cloud Run** | ⭐⭐⭐ Medium | Pay-per-use (~$5-30) | $300 credits | Production, Auto-scaling |
| **Render.com** | ⭐⭐⭐⭐⭐ Easiest | $7 or Free | Yes (750hrs) | Quick launch |
| **Railway.app** | ⭐⭐⭐⭐⭐ Easiest | $5 + usage | $5 credit | Developer-friendly |
| **Heroku** | ⭐⭐⭐⭐ Easy | $7+ | No | Classic reliability |
| **DigitalOcean** | ⭐⭐⭐ Medium | $12-20 | $200 credits | Predictable pricing |

---

## 🎯 My Recommendation for You

Based on your needs (actual deployment, no localhost):

### **Best Choice: Render.com** 🏆

**Why:**
1. ✅ **No CLI installation needed** - Everything via web UI
2. ✅ **Free tier available** - Test before paying
3. ✅ **Automatic HTTPS** - SSL certificates included
4. ✅ **Auto-deploy from GitHub** - Push code, it deploys
5. ✅ **Built-in PostgreSQL** - Database included
6. ✅ **Simple environment variables** - Easy to configure
7. ✅ **Live in 10 minutes** - Fastest path to production

### **Second Choice: Google Cloud Run** 🥈

**Why:**
1. Enterprise-grade infrastructure
2. Auto-scaling (scales to zero when not used)
3. Pay only for what you use
4. Can use Cloud Shell (browser-based, no local install)

---

## 🚀 Quick Start: Deploy to Render.com NOW

### 1. Push to GitHub (if not already)
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Initialize git if needed
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/mandate-vault.git
git push -u origin main
```

### 2. Deploy on Render
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New +" → "Web Service"
4. Select your `mandate-vault` repository
5. Configure:
   - Name: `mandate-vault`
   - Environment: `Docker`
   - Instance Type: `Starter` ($7/mo) or `Free`
   - Click "Advanced" and add environment variables:
     ```
     SECRET_KEY=<paste-generated-secret>
     ACP_WEBHOOK_SECRET=<paste-generated-secret>
     ENVIRONMENT=production
     DEBUG=false
     ```
6. Click "Create Web Service"
7. While deploying, add database:
   - Click "New +" → "PostgreSQL"
   - Name: `mandate-vault-db`
   - Plan: `Starter` ($7/mo)
8. Copy the Internal Database URL
9. Add to web service environment variables:
   ```
   DATABASE_URL=<paste-internal-db-url>
   ```
10. Your service will auto-deploy!

### 3. Run Migrations
Once deployed, go to Shell tab in Render dashboard:
```bash
alembic upgrade head
python scripts/seed_initial_data.py
```

**DONE! Your API is live at: `https://mandate-vault.onrender.com`** 🎉

---

## 📞 Need Help?

Choose your deployment method and I'll create a detailed step-by-step guide specifically for that platform!

Just tell me: **"Let's deploy to [Render/Railway/Cloud Run/Heroku/DigitalOcean]"**
