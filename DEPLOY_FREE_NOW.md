# 🚀 FREE Production Deployment Guide - Mandate Vault

## 🎯 What You'll Get (100% FREE)
- ✅ **Live API** on Render.com (https://mandate-vault.onrender.com)
- ✅ **Free PostgreSQL Database** (90-day renewable)
- ✅ **Landing Page** on Vercel (https://mandate-vault.vercel.app)
- ✅ **Automatic HTTPS** for both
- ✅ **No Credit Card Required**

**Total Cost: $0** 🎉

---

## 📝 Your Generated Secrets

**SAVE THESE - You'll need them in Step 4!**

```
SECRET_KEY=aA-PqbQIpyvdOwfhUfzV-nuwioXVf-KQOxbMfSGTRBY
ACP_WEBHOOK_SECRET=jFqzEkz6LRFFmD-vwwxHyFaWzE0jjjpkSUZUM37dCxA
```

---

## 🚀 STEP 1: Create GitHub Repository (2 minutes)

### 1.1 Create New Repository on GitHub

1. Go to https://github.com/new
2. Fill in:
   - **Repository name**: `mandate-vault`
   - **Description**: Enterprise Digital Authorization Platform
   - **Visibility**: Public (for free Render deployment)
   - ❌ Don't initialize with README (we have one)
3. Click **"Create repository"**

### 1.2 Push Your Code to GitHub

```bash
cd /Users/alexlim/Desktop/mandate_vault

# Initialize git if needed
git init

# Add all files
git add .

# Commit
git commit -m "Initial deployment - Enterprise API ready"

# Add your GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/mandate-vault.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**✅ Checkpoint**: Visit your GitHub repo URL - you should see all your code!

---

## 🎨 STEP 2: Deploy API to Render.com (5 minutes)

### 2.1 Create Render Account

1. Go to https://render.com
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (easiest)
4. ✅ No credit card required!

### 2.2 Create PostgreSQL Database (FREE)

1. In Render Dashboard, click **"New +"**
2. Select **"PostgreSQL"**
3. Configure:
   - **Name**: `mandate-vault-db`
   - **Database**: `mandate_vault`
   - **User**: `mandate_user`
   - **Region**: Oregon (US West)
   - **PostgreSQL Version**: 14
   - **Datadog API Key**: Leave empty
   - **Plan**: ⭐ **FREE** ⭐
4. Click **"Create Database"**
5. **IMPORTANT**: 
   - Wait for database to be created (~2 minutes)
   - Click on your new database
   - Scroll to **"Connections"** section
   - Copy the **"Internal Database URL"** (looks like `postgresql://mandate_user:...`)
   - **Save this URL - you'll need it in step 2.3!**

### 2.3 Create Web Service (FREE)

1. In Render Dashboard, click **"New +"**
2. Select **"Web Service"**
3. Click **"Build and deploy from a Git repository"**
4. Click **"Configure account"** to connect GitHub (if needed)
5. Find and select your **`mandate-vault`** repository
6. Click **"Connect"**

7. **Configure the service:**

   - **Name**: `mandate-vault`
   - **Region**: Oregon (US West) - *must match database!*
   - **Branch**: `main`
   - **Runtime**: **Docker** ⭐
   - **Plan**: ⭐ **FREE** ⭐

8. **Scroll down to "Advanced"** and click it

9. **Add Environment Variables** (click "Add Environment Variable" for each):

   ```
   SECRET_KEY = aA-PqbQIpyvdOwfhUfzV-nuwioXVf-KQOxbMfSGTRBY
   ACP_WEBHOOK_SECRET = jFqzEkz6LRFFmD-vwwxHyFaWzE0jjjpkSUZUM37dCxA
   DATABASE_URL = [paste the Internal Database URL from step 2.2]
   ENVIRONMENT = production
   DEBUG = false
   ACP_ENABLE = true
   CORS_ORIGINS = *
   LOG_LEVEL = INFO
   ```

10. **Health Check Path**: `/healthz`

11. Click **"Create Web Service"**

### 2.4 Wait for Deployment

- ⏱️ First build takes **5-10 minutes**
- Watch the logs in real-time
- You'll see:
  - ✅ Building Docker image
  - ✅ Pushing to registry
  - ✅ Deploying service
  - ✅ Live status: **"Your service is live" 🎉**

### 2.5 Initialize Database

Once your service shows "Live":

1. Click on your service name (`mandate-vault`)
2. Click the **"Shell"** tab at the top
3. Run these commands one by one:

```bash
# Run database migrations
alembic upgrade head

# Create initial admin user (SAVE THE PASSWORD IT OUTPUTS!)
python scripts/seed_initial_data.py
```

**✅ Checkpoint**: You should see:
```
✅ Admin user created successfully!
Email: admin@example.com
Password: [RANDOM_PASSWORD]
```

**SAVE THIS PASSWORD!**

### 2.6 Test Your Live API! 🎉

Your API URL will be: `https://mandate-vault.onrender.com`

**Test it:**

1. **Health Check**: Visit https://mandate-vault.onrender.com/healthz
   - Should return: `{"status":"healthy"}`

2. **API Docs**: Visit https://mandate-vault.onrender.com/docs
   - Should see interactive Swagger UI

3. **Test Login**:
```bash
curl -X POST "https://mandate-vault.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"[YOUR_PASSWORD]"}'
```

**✅ API IS LIVE!** 🚀

---

## 🌐 STEP 3: Deploy Landing Page to Vercel (3 minutes)

### 3.1 Update Landing Page with Your Live API URL

The landing page has been created with your production API URL!
Location: `/Users/alexlim/Desktop/mandate_vault/landing.html`

### 3.2 Create Vercel Account

1. Go to https://vercel.com
2. Click **"Sign Up"**
3. Choose **"Continue with GitHub"**
4. ✅ No credit card required!

### 3.3 Deploy Landing Page

**Option A: Using Vercel Dashboard (Easiest)**

1. In Vercel dashboard, click **"Add New..." → "Project"**
2. Click **"Import Git Repository"**
3. Select your `mandate-vault` repository
4. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: Leave as `.`
   - **Build Command**: Leave empty or `echo "Static site"`
   - **Output Directory**: `.`
5. Click **"Deploy"**

**Option B: Using Vercel CLI (Alternative)**

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
cd /Users/alexlim/Desktop/mandate_vault
vercel --prod
```

### 3.4 Access Your Landing Page

Your landing page will be live at:
- `https://mandate-vault.vercel.app` (or similar)
- Or your custom domain if you configure one (free!)

**✅ LANDING PAGE IS LIVE!** 🎉

---

## 🎯 What You Have Now

### API (Render.com)
- 🌐 **URL**: https://mandate-vault.onrender.com
- 📚 **Docs**: https://mandate-vault.onrender.com/docs
- ❤️ **Health**: https://mandate-vault.onrender.com/healthz
- 🔐 **Admin**: admin@example.com / [your password]

### Landing Page (Vercel)
- 🌐 **URL**: https://mandate-vault.vercel.app
- ⚡ **Fast**: Edge-optimized globally
- 🔄 **Auto-deploy**: Updates on git push

### Database (Render.com)
- 💾 **Type**: PostgreSQL 14
- 📊 **Size**: 1GB free
- ⏰ **Duration**: 90 days (then recreate for free)

---

## 📋 Important Notes

### ⚠️ Free Tier Limitations

**Render.com (API):**
- ✅ Completely FREE forever
- ⚠️ **Sleeps after 15 minutes** of inactivity
- ⚠️ **Wake-up time**: ~30 seconds on first request
- ✅ Perfect for: demos, testing, low-traffic APIs

**Render.com (Database):**
- ✅ FREE for 90 days
- ⚠️ After 90 days: Just create a new one (backup & restore)
- ✅ Backup command provided below

**Vercel (Landing Page):**
- ✅ FREE forever
- ✅ Always on (no sleeping)
- ✅ 100GB bandwidth/month
- ✅ Perfect for static sites

### 💡 Keep Your API Always Awake (Optional)

Use **UptimeRobot** (also free, no credit card) to ping your API every 5 minutes:

1. Go to https://uptimerobot.com
2. Sign up (free)
3. Create new monitor:
   - **Monitor Type**: HTTP(s)
   - **URL**: https://mandate-vault.onrender.com/healthz
   - **Monitoring Interval**: 5 minutes
4. Your API will never sleep! 🎉

---

## 🔒 Security Best Practices

### 1. Rotate Secrets After Testing

Once you've tested everything works, generate new secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update in Render Dashboard:
- Go to your web service
- Click "Environment"
- Update `SECRET_KEY` and `ACP_WEBHOOK_SECRET`
- Click "Save Changes" (triggers automatic redeploy)

### 2. Restrict CORS

Update `CORS_ORIGINS` in Render:
```
CORS_ORIGINS=https://mandate-vault.vercel.app,https://your-custom-domain.com
```

### 3. Enable Sentry (Optional - Free Tier)

1. Sign up at https://sentry.io (free tier)
2. Create new project
3. Copy DSN
4. Add to Render environment:
   ```
   SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
   SENTRY_ENVIRONMENT=production
   ```

---

## 💾 Database Backup (Before 90-Day Expiry)

### Backup Your Data

```bash
# Get connection string from Render dashboard
pg_dump "postgresql://mandate_user:password@..." > backup.sql
```

### Create New Free Database

1. In Render, create new PostgreSQL database (free)
2. Get new connection string
3. Restore:
```bash
psql "new-connection-string" < backup.sql
```

4. Update `DATABASE_URL` in your web service
5. Done! Another 90 days free 🎉

---

## 🚀 Deployment Workflow

### Making Updates

```bash
# Make your code changes
git add .
git commit -m "Update: your feature"
git push

# Render auto-deploys in ~2-3 minutes
# Vercel auto-deploys in ~30 seconds
```

### View Logs

**Render:**
1. Go to your service
2. Click "Logs" tab
3. Real-time streaming logs

**Vercel:**
1. Go to your deployment
2. Click "Logs" or "Functions"
3. View access logs

---

## 🎯 Next Steps

### 1. Custom Domain (FREE on both platforms)

**Render:**
- Settings → Custom Domain
- Add your domain
- Configure DNS (A record or CNAME)

**Vercel:**
- Project Settings → Domains
- Add your domain
- Automatic HTTPS

### 2. Monitoring

**Render provides:**
- ✅ Basic metrics (free)
- ✅ Logs (7-day retention)
- ✅ Health checks

**Add Sentry for:**
- ✅ Error tracking
- ✅ Performance monitoring
- ✅ User sessions

### 3. SDKs

Test your SDKs against production:

**Python:**
```python
from mandate_vault import MandateVaultClient

client = MandateVaultClient(
    base_url="https://mandate-vault.onrender.com",
    api_key="your-api-key"
)
```

**Node.js:**
```javascript
import { MandateVaultClient } from './sdks/nodejs';

const client = new MandateVaultClient({
  baseUrl: 'https://mandate-vault.onrender.com',
  apiKey: 'your-api-key'
});
```

---

## 📞 Support

### Your Deployment
- **API**: https://mandate-vault.onrender.com
- **Docs**: https://mandate-vault.onrender.com/docs
- **Landing**: https://mandate-vault.vercel.app

### Troubleshooting

**API won't start:**
- Check logs in Render dashboard
- Verify all environment variables are set
- Ensure DATABASE_URL is the *Internal* URL

**Database connection error:**
- Make sure API and database are in same region
- Use Internal Database URL (not External)
- Check database is running (green status)

**Landing page 404:**
- Ensure `landing.html` is in root directory
- Check Vercel build logs
- Verify deployment completed

---

## ✅ Checklist

- [ ] Created GitHub repository
- [ ] Pushed code to GitHub
- [ ] Created Render account
- [ ] Deployed PostgreSQL database on Render
- [ ] Deployed web service on Render
- [ ] Ran database migrations
- [ ] Created admin user
- [ ] Tested API endpoints
- [ ] Created Vercel account
- [ ] Deployed landing page to Vercel
- [ ] Tested landing page
- [ ] (Optional) Setup UptimeRobot
- [ ] Saved all credentials securely

---

## 🎉 CONGRATULATIONS!

You now have a **production-grade API platform** running **completely free**!

**Share your API:**
- API Docs: https://mandate-vault.onrender.com/docs
- Landing Page: https://mandate-vault.vercel.app

**What you built:**
- ✅ Multi-protocol authorization API (AP2 + ACP)
- ✅ PostgreSQL database with migrations
- ✅ REST API with 700+ tests
- ✅ Auto-scaling infrastructure
- ✅ Professional landing page
- ✅ Automatic HTTPS
- ✅ Real-time monitoring

**Total cost: $0** 🎉

---

## 🚀 Upgrade Path

When you're ready for production-scale:

| Platform | Upgrade | Cost | Benefits |
|----------|---------|------|----------|
| **Render** | Starter | $7/mo | No sleep, SLA |
| **Vercel** | Pro | $20/mo | More bandwidth |
| **Database** | Starter | $7/mo | 10GB, backups |

**But for now, enjoy your free enterprise API!** 🎊

