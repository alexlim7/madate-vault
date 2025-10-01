# Customer Onboarding Guide

Welcome to Mandate Vault! This guide will help you get started in minutes.

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Get Your Credentials

After signing up, you'll receive:
- **Account Email**: Your login credentials
- **Tenant ID**: Your unique organization identifier
- **API Base URL**: `https://api.mandatevault.com`

### Step 2: Create Your First API Key

```bash
# Login to dashboard
https://app.mandatevault.com/login

# Navigate to Settings → API Keys
# Click "Create API Key"
# Save your key securely (shown only once!)
```

**Your API key looks like:**
```
mvk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **Important:** Store this key securely - it won't be shown again!

### Step 3: Make Your First API Call

**Using cURL:**
```bash
curl -X POST https://api.mandatevault.com/api/v1/mandates \
  -H "X-API-Key: mvk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tenant_id": "your-tenant-id"
  }'
```

**Success Response:**
```json
{
  "id": "mandate-123",
  "status": "active",
  "verification_status": "VALID",
  "created_at": "2025-10-01T12:00:00Z"
}
```

---

## 📚 Complete Setup Guide

### 1. Understanding the Flow

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Issuer    │──┬──>│ Mandate Vault│──┬──>│  Your App   │
│  (Bank)     │  │   │   (Verify)   │  │   │             │
└─────────────┘  │   └──────────────┘  │   └─────────────┘
                 │                      │
            JWT-VC Token           Webhook Event
         (Digital Mandate)      (Real-time Update)
```

**Key Concepts:**
- **JWT-VC**: Digitally signed mandate (JSON Web Token - Verifiable Credential)
- **Issuer**: The bank or financial institution (did:web:bank.example.com)
- **Subject**: The customer granting the mandate (did:example:customer-123)
- **Scope**: What the mandate allows (e.g., "payment.recurring")

### 2. Register Trusted Issuers

Before accepting mandates, register the issuers you trust:

```bash
POST /api/v1/admin/truststore/issuers
{
  "issuer_did": "did:web:bank.example.com",
  "jwk_set": {
    "keys": [{
      "kty": "RSA",
      "use": "sig",
      "kid": "bank-key-1",
      "n": "...",
      "e": "AQAB"
    }]
  }
}
```

### 3. Configure Webhooks

Get real-time notifications when mandates are created:

```bash
POST /api/v1/webhooks
{
  "name": "My Webhook",
  "url": "https://your-app.com/webhooks/mandates",
  "events": ["MandateCreated", "MandateVerificationFailed"],
  "secret": "your-webhook-secret"
}
```

**Your webhook will receive:**
```json
{
  "event_type": "MandateCreated",
  "mandate": {
    "id": "mandate-123",
    "issuer_did": "did:web:bank.example.com",
    "subject_did": "did:example:customer-456",
    "scope": "payment.recurring",
    "amount_limit": "5000.00 USD"
  },
  "timestamp": "2025-10-01T12:00:00Z"
}
```

### 4. Verify Webhook Signatures

Always verify webhook signatures for security:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

# Usage
is_valid = verify_webhook(
    request.body,
    request.headers['X-Signature'],
    'your-webhook-secret'
)
```

---

## 🔑 Authentication Methods

### Option 1: API Keys (Recommended for M2M)

```bash
curl -H "X-API-Key: mvk_your_key" \
  https://api.mandatevault.com/api/v1/mandates
```

**Use Cases:**
- Server-to-server communication
- Background jobs
- Automated scripts

### Option 2: JWT Tokens (For User Sessions)

```bash
# 1. Login
curl -X POST https://api.mandatevault.com/api/v1/auth/login \
  -d '{"email": "user@company.com", "password": "..."}' \
  -H "Content-Type: application/json"

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# 2. Use token
curl -H "Authorization: Bearer eyJhbGc..." \
  https://api.mandatevault.com/api/v1/mandates
```

**Use Cases:**
- Web applications
- Mobile apps
- User-specific operations

---

## 📖 Common Use Cases

### Use Case 1: Store a Payment Mandate

```python
import requests

response = requests.post(
    'https://api.mandatevault.com/api/v1/mandates',
    headers={'X-API-Key': 'mvk_your_key'},
    json={
        'vc_jwt': jwt_token,  # From bank
        'tenant_id': 'your-tenant-id',
        'retention_days': 90
    }
)

mandate = response.json()
print(f"Mandate created: {mandate['id']}")
```

### Use Case 2: Search Mandates

```python
response = requests.post(
    'https://api.mandatevault.com/api/v1/mandates/search',
    headers={'X-API-Key': 'mvk_your_key'},
    json={
        'tenant_id': 'your-tenant-id',
        'issuer_did': 'did:web:bank.example.com',
        'status': 'active',
        'limit': 50
    }
)

mandates = response.json()['mandates']
print(f"Found {len(mandates)} mandates")
```

### Use Case 3: Revoke a Mandate

```python
response = requests.delete(
    f'https://api.mandatevault.com/api/v1/mandates/{mandate_id}',
    headers={'X-API-Key': 'mvk_your_key'}
)

print("Mandate revoked successfully")
```

### Use Case 4: Audit Trail

```python
response = requests.get(
    'https://api.mandatevault.com/api/v1/audit',
    headers={'X-API-Key': 'mvk_your_key'},
    params={
        'tenant_id': 'your-tenant-id',
        'event_type': 'CREATE',
        'limit': 100
    }
)

logs = response.json()
for log in logs:
    print(f"{log['timestamp']}: {log['event_type']} - {log['mandate_id']}")
```

---

## 🔒 Security Best Practices

### 1. Protect Your API Keys

✅ **DO:**
- Store keys in environment variables
- Use secrets management (AWS Secrets Manager, GCP Secret Manager)
- Rotate keys every 90 days
- Use different keys for dev/staging/production

❌ **DON'T:**
- Commit keys to git
- Share keys via email/Slack
- Hardcode keys in source code
- Use the same key across environments

### 2. Validate Webhooks

Always verify webhook signatures:

```python
# Python
def verify_signature(payload, signature, secret):
    import hmac
    import hashlib
    
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
```

```javascript
// Node.js
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(signature)
  );
}
```

### 3. Use HTTPS

All API calls **must** use HTTPS. HTTP requests will be rejected.

### 4. Implement Rate Limiting

Respect rate limits to avoid throttling:
- **Default:** 100 requests/minute per API key
- **Burst:** Up to 200 requests in a 10-second window

**Rate limit headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

---

## 📊 Monitoring & Alerts

### View Metrics

Access your metrics dashboard:
```
https://app.mandatevault.com/metrics
```

**Key Metrics:**
- Total mandates stored
- Verification success rate
- API response times
- Webhook delivery rate

### Set Up Alerts

Configure alerts for critical events:

1. Navigate to **Settings → Alerts**
2. Create alert rules:
   - Verification failures > 10%
   - Webhook delivery failures
   - API error rate > 1%
   - Approaching rate limits

**Alert Channels:**
- Email
- Slack
- PagerDuty
- Webhook

---

## 🚀 Going to Production

### Pre-Launch Checklist

- [ ] API keys created and secured
- [ ] Trusted issuers registered
- [ ] Webhooks configured and tested
- [ ] Signature verification implemented
- [ ] Error handling in place
- [ ] Monitoring & alerts configured
- [ ] Team trained on dashboard
- [ ] Backup plan documented

### Production Settings

**Recommended Configuration:**
```json
{
  "rate_limits": {
    "per_minute": 1000,
    "per_hour": 10000
  },
  "retention_days": 90,
  "webhook_timeout": 30,
  "webhook_retries": 3
}
```

### Load Testing

Test your integration before launch:

```bash
# Using k6
k6 run --vus 50 --duration 2m load_test.js

# Expected performance:
# - P95 response time: < 500ms
# - Error rate: < 0.1%
# - Throughput: 100+ req/s
```

---

## 📞 Support & Resources

### Documentation
- **API Reference**: https://docs.mandatevault.com/api
- **SDKs**: https://docs.mandatevault.com/sdks
- **Examples**: https://github.com/mandate-vault/examples

### Support Channels
- **Email**: support@mandatevault.com
- **Slack**: mandatevault.slack.com
- **Phone**: +1 (555) 123-4567 (Enterprise only)

### Status & SLA
- **Status Page**: https://status.mandatevault.com
- **Uptime SLA**: 99.9% (Enterprise: 99.99%)
- **Support SLA**: 
  - Critical: < 1 hour
  - High: < 4 hours
  - Normal: < 24 hours

---

## 🎓 Next Steps

1. **Complete Setup** → Follow this guide
2. **Integrate SDKs** → Use our Python/Node.js libraries
3. **Test Integration** → Use staging environment
4. **Go Live** → Deploy to production
5. **Monitor** → Track metrics & alerts
6. **Optimize** → Review and improve

**Need Help?** Contact our team at support@mandatevault.com

---

**Welcome to Mandate Vault! 🚀**

