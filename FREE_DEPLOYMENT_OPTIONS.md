# 🆓 100% FREE Deployment Options for Mandate Vault

Yes! You can deploy your production-ready API **completely free**. Here are your best options:

---

## 🏆 Option 1: Render.com Free Tier (RECOMMENDED) ⭐⭐⭐⭐⭐

**Cost:** $0 forever (with limitations)
**Setup Time:** 10 minutes
**Best For:** Testing, low-traffic production

### What You Get FREE:
- ✅ 750 hours/month (enough for 1 service running 24/7)
- ✅ PostgreSQL database (90-day expiration, free to recreate)
- ✅ Automatic HTTPS/SSL
- ✅ GitHub auto-deploy
- ✅ Custom domain support
- ⚠️ Service spins down after 15 min of inactivity (takes ~30s to wake up)

### Quick Deploy Steps:

#### 1. Generate Secrets
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Generate and save these
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('ACP_WEBHOOK_SECRET=' + secrets.token_urlsafe(32))"
```

#### 2. Push to GitHub
```bash
git init
git add .
git commit -m "Deploy to Render"

# Create repo on GitHub.com (free), then:
git remote add origin https://github.com/YOUR_USERNAME/mandate-vault.git
git branch -M main
git push -u origin main
```

#### 3. Deploy on Render (All via Browser)

1. **Sign Up:**
   - Go to https://render.com
   - Sign up with GitHub (no credit card required!)

2. **Create FREE PostgreSQL Database:**
   - Dashboard → "New +" → "PostgreSQL"
   - Name: `mandate-vault-db`
   - Database: `mandate_vault`
   - User: `mandate_user`
   - Region: Oregon (US West)
   - Plan: **FREE** ⭐
   - Click "Create Database"
   - **IMPORTANT:** Copy the "Internal Database URL"

3. **Create FREE Web Service:**
   - Dashboard → "New +" → "Web Service"
   - Connect GitHub account
   - Select your `mandate-vault` repository
   - Configure:
     - Name: `mandate-vault`
     - Environment: **Docker**
     - Region: Oregon (US West)
     - Branch: `main`
     - Plan: **FREE** ⭐
   
4. **Add Environment Variables:**
   - Click "Advanced"
   - Add these environment variables:
     ```
     SECRET_KEY=<paste-from-step-1>
     ACP_WEBHOOK_SECRET=<paste-from-step-1>
     DATABASE_URL=<paste-internal-db-url>
     ENVIRONMENT=production
     DEBUG=false
     ```

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for build
   - Your API will be live at: `https://mandate-vault.onrender.com`

#### 4. Setup Database

Once deployed, click "Shell" tab in your web service:
```bash
alembic upgrade head
python scripts/seed_initial_data.py
```

### ✅ Done! Your API is live and FREE!

**Your URLs:**
- API: `https://mandate-vault.onrender.com`
- Docs: `https://mandate-vault.onrender.com/docs`
- Health: `https://mandate-vault.onrender.com/healthz`

**Limitations:**
- ⚠️ Spins down after 15 min inactivity (first request takes ~30s)
- ⚠️ Database expires after 90 days (just recreate it)
- ⚠️ 750 hours/month (31 days = 744 hours, so enough for 1 service)

**Perfect for:** Testing, demos, low-traffic APIs, hobby projects

---

## 🐳 Option 2: Fly.io Free Tier ⭐⭐⭐⭐

**Cost:** $0 (generous free tier)
**Setup Time:** 15 minutes
**Best For:** Always-on free hosting

### What You Get FREE:
- ✅ Up to 3 shared-cpu-1x VMs (256MB RAM each)
- ✅ 3GB persistent storage
- ✅ 160GB outbound data transfer
- ✅ Always on (no sleeping!)
- ✅ Automatic HTTPS
- ⚠️ Requires credit card for verification (no charges on free tier)

### Deploy Steps:

#### 1. Install Fly CLI
```bash
# macOS
curl -L https://fly.io/install.sh | sh

# Add to PATH
echo 'export PATH="$HOME/.fly/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### 2. Login and Initialize
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Login (creates free account)
fly auth signup

# Initialize app
fly launch --no-deploy

# When prompted:
# - App name: mandate-vault (or choose your own)
# - Region: Choose closest to you
# - PostgreSQL: Yes (free tier)
# - Redis: No
```

#### 3. Configure Secrets
```bash
# Generate and set secrets
fly secrets set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
fly secrets set ACP_WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
fly secrets set ENVIRONMENT=production
fly secrets set DEBUG=false
```

#### 4. Deploy
```bash
fly deploy
```

#### 5. Setup Database
```bash
# SSH into your app
fly ssh console

# Run migrations
alembic upgrade head
python scripts/seed_initial_data.py
exit
```

### ✅ Done! Your API is live at: `https://mandate-vault.fly.dev`

**Limitations:**
- ⚠️ Requires credit card (but free tier has no charges)
- ⚠️ 256MB RAM per VM (should be enough for light use)

**Perfect for:** Always-on APIs, no cold starts

---

## ☁️ Option 3: Google Cloud Platform (Free Tier) ⭐⭐⭐⭐

**Cost:** $0 for 12 months ($300 credits)
**Setup Time:** 20 minutes
**Best For:** Learning enterprise cloud

### What You Get FREE:
- ✅ $300 credits for 90 days
- ✅ Always Free tier (after credits):
  - 2 million Cloud Run requests/month
  - 360,000 GB-seconds compute time
  - 1GB outbound data
- ✅ Enterprise-grade infrastructure
- ⚠️ Requires credit card

### Deploy Steps:

Use the **Cloud Shell** method from `DEPLOY_TO_PRODUCTION.md` (no local CLI needed).

**Perfect for:** Enterprise-grade hosting, auto-scaling

---

## 🚀 Option 4: Railway.app (Free Trial) ⭐⭐⭐⭐

**Cost:** $5 free credits (lasts ~1 month with light usage)
**Setup Time:** 5 minutes
**Best For:** Modern developer experience

### What You Get FREE:
- ✅ $5 in credits (no credit card required)
- ✅ Auto-deploy from GitHub
- ✅ Built-in PostgreSQL
- ✅ Modern dashboard
- ⚠️ Credits run out after ~1 month

### Deploy Steps:

1. Go to https://railway.app
2. Sign up with GitHub
3. Create new project → Deploy from GitHub
4. Select your repo
5. Add PostgreSQL
6. Add environment variables
7. Deploy!

**Perfect for:** Quick testing, modern UI

---

## 🎯 Option 5: Oracle Cloud (Always Free) ⭐⭐⭐

**Cost:** $0 forever (generous always-free tier)
**Setup Time:** 30 minutes
**Best For:** Maximum free resources

### What You Get FREE Forever:
- ✅ 2 AMD-based VMs (1GB RAM each)
- ✅ 200GB block storage
- ✅ 10TB outbound data transfer/month
- ✅ Autonomous Database (always free tier)
- ⚠️ Requires credit card verification
- ⚠️ More complex setup

### Deploy Steps:

1. Sign up at https://www.oracle.com/cloud/free/
2. Create VM instance
3. Install Docker
4. Deploy with docker-compose

**Perfect for:** Maximum free resources, advanced users

---

## 📊 Comparison: FREE Tiers

| Platform | Cost | Always On? | Database | Setup | Credit Card? |
|----------|------|-----------|----------|-------|--------------|
| **Render** | $0 | ❌ (sleeps) | ✅ FREE | ⭐⭐⭐⭐⭐ | ❌ No |
| **Fly.io** | $0 | ✅ Yes | ✅ FREE | ⭐⭐⭐⭐ | ⚠️ Yes |
| **GCP** | $300 credits | ✅ Yes | ✅ Included | ⭐⭐⭐ | ⚠️ Yes |
| **Railway** | $5 credits | ✅ Yes | ✅ FREE | ⭐⭐⭐⭐⭐ | ❌ No |
| **Oracle** | $0 forever | ✅ Yes | ✅ FREE | ⭐⭐ | ⚠️ Yes |

---

## 🏆 MY RECOMMENDATION FOR FREE DEPLOYMENT

### **Best Choice: Render.com Free Tier** 

**Why?**
1. ✅ **Truly free** - No credit card needed
2. ✅ **Dead simple** - 10 minutes to deploy
3. ✅ **Free database** - PostgreSQL included
4. ✅ **Auto HTTPS** - SSL certificates included
5. ✅ **Perfect for testing** - Great for demos and low-traffic

**The only downside:** Service sleeps after 15 minutes of inactivity (takes 30 seconds to wake up on first request).

**Perfect for:**
- Testing your deployment
- Demos and presentations  
- Low-traffic APIs (< 1000 requests/day)
- Personal projects
- Learning and development

### **If You Need "Always On" for Free:**

Use **Fly.io** - Requires credit card but stays running 24/7 with no cold starts.

---

## 🚀 QUICK START: Deploy FREE on Render NOW

### Complete Steps (Copy-Paste):

```bash
# 1. Navigate to your project
cd /Users/alexlim/Desktop/mandate_vault

# 2. Generate secrets and save them
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "ACP_WEBHOOK_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# 3. Initialize git (if not already)
git init
git add .
git commit -m "Deploy to Render"

# 4. Create GitHub repo at https://github.com/new

# 5. Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/mandate-vault.git
git branch -M main
git push -u origin main
```

Now go to https://render.com and:
1. Sign up with GitHub (FREE)
2. New + → PostgreSQL (FREE plan)
3. Copy the Internal Database URL
4. New + → Web Service
5. Select your repo
6. Environment: Docker
7. Plan: FREE
8. Add environment variables (from step 2 + DATABASE_URL)
9. Create Web Service

**Wait 10 minutes → Your API is LIVE! 🎉**

---

## 💡 Tips for Free Hosting

### 1. Keep Render Free Tier Active
```bash
# Use a cron job or UptimeRobot to ping every 14 minutes
# This keeps your service from sleeping
# Sign up at uptimerobot.com (also free!)
```

### 2. Optimize for Free Tier
- Use SQLite for development (no database costs)
- Minimize outbound traffic
- Use caching to reduce compute time
- Compress responses

### 3. Database Backup (Render Free)
```bash
# Before your 90-day database expires, backup and recreate:
pg_dump $DATABASE_URL > backup.sql

# Create new free database
# Restore: psql $NEW_DATABASE_URL < backup.sql
```

---

## 🎁 Upgrade Path

When you're ready to upgrade from free:

| Platform | Next Tier | Cost | Benefits |
|----------|-----------|------|----------|
| **Render** | Starter | $7/mo | Always on, no sleep |
| **Fly.io** | Hobby | $0 | Stay on free tier! |
| **Railway** | Developer | $5/mo + usage | More resources |

---

## ✅ What You Can Do With Free Tier

- ✅ **Development and testing**
- ✅ **Demos and presentations**
- ✅ **Personal projects**
- ✅ **Low-traffic APIs** (< 10,000 requests/month)
- ✅ **Proof of concepts**
- ✅ **Learning and experimentation**

---

## 🚨 What You CANNOT Do With Free Tier

- ❌ High-traffic production (> 100,000 requests/month)
- ❌ Mission-critical services (99.9% uptime SLA)
- ❌ Large databases (> 1GB)
- ❌ Heavy compute workloads

---

## 🎯 YOUR NEXT STEP

**I recommend:** Deploy to **Render.com FREE tier** right now!

It's:
- ✅ Completely free
- ✅ No credit card needed
- ✅ 10 minutes to deploy
- ✅ Perfect for testing

**Follow these steps:**
1. Run the commands above to push to GitHub
2. Go to https://render.com
3. Follow "Quick Start: Deploy FREE on Render NOW" section above

**You'll have a live API in 10 minutes!** 🚀

---

## 📞 Need Help?

Just say: **"Let's deploy to Render for free"**

I'll walk you through every single step! 😊
