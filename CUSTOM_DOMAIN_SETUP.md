# 🌐 Custom Domain Setup - mandatevault.com

You have **mandatevault.com** on GoDaddy. Let's configure it for your production deployment!

---

## 🎯 Domain Strategy

We'll set up:
- **www.mandatevault.com** → Landing page (Vercel)
- **api.mandatevault.com** → API (Render)
- **mandatevault.com** → Redirect to www (Landing page)

---

## 📋 STEP 1: Configure DNS in GoDaddy

### 1.1 Login to GoDaddy

1. Go to https://dnsmanagement.godaddy.com
2. Find **mandatevault.com**
3. Click **"DNS"** or **"Manage DNS"**

### 1.2 Add DNS Records

**Delete any existing A/CNAME records first, then add these:**

#### For Landing Page (Vercel):

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | www | cname.vercel-dns.com | 600 |
| A | @ | 76.76.21.21 | 600 |

#### For API (Render):

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | api | mandate-vault.onrender.com | 600 |

**Save all records.**

---

## 📋 STEP 2: Configure Vercel

### 2.1 Add Custom Domain

1. **In Vercel**, click on your `mandate-vault` project

2. Go to **"Settings"** → **"Domains"**

3. **Add these domains:**
   - `mandatevault.com`
   - `www.mandatevault.com`

4. Click **"Add"** for each

5. Vercel will show:
   - ✅ If configured correctly
   - ❌ If DNS needs updating (follow their instructions)

6. **Vercel automatically provides FREE SSL certificates!** 🔒

### 2.2 Set Primary Domain

- Set **www.mandatevault.com** as primary
- Vercel will auto-redirect **mandatevault.com** → **www.mandatevault.com**

---

## 📋 STEP 3: Configure Render

### 3.1 Add Custom Domain

1. **In Render**, click on your `mandate-vault` service

2. Go to **"Settings"** → **"Custom Domain"**

3. **Add domain:**
   ```
   api.mandatevault.com
   ```

4. Click **"Save"**

5. Render will show you the DNS record needed (should match what you added in GoDaddy)

6. **Render automatically provides FREE SSL certificates!** 🔒

---

## 📋 STEP 4: Update Environment Variables

### Update Render Environment:

Go to **Environment** tab and update:

```
ALLOWED_HOSTS=api.mandatevault.com,mandate-vault.onrender.com,localhost,127.0.0.1
```

**(We can't use the ALLOWED_HOSTS env var due to parsing, so we'll update the code instead)**

Actually, let me update the security middleware code to include your domain...

---

## 📋 STEP 5: Update Landing Page URLs

Once domains are configured, we'll update:
- Landing page CTAs to point to `https://api.mandatevault.com/docs`
- Code examples to use `api.mandatevault.com`

---

## ⏱️ DNS Propagation

DNS changes take:
- **GoDaddy → Vercel**: 5-15 minutes
- **GoDaddy → Render**: 5-15 minutes
- **Full propagation**: Up to 48 hours (usually < 1 hour)

---

## ✅ When It's Working:

You'll be able to access:
- **Landing Page**: https://www.mandatevault.com
- **API**: https://api.mandatevault.com
- **API Docs**: https://api.mandatevault.com/docs
- **Health**: https://api.mandatevault.com/healthz

---

## 🎯 Your Professional URLs:

| Service | Old URL | New URL |
|---------|---------|---------|
| Landing | madate-vault.vercel.app | **www.mandatevault.com** |
| API | mandate-vault.onrender.com | **api.mandatevault.com** |
| Docs | mandate-vault.onrender.com/docs | **api.mandatevault.com/docs** |

---

Let me know when you've:
1. ✅ Configured DNS in GoDaddy
2. ✅ Added domain to Vercel
3. ✅ Added domain to Render

Then I'll update the code with your custom domains!

