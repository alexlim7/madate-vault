# Multi-Protocol Guide: AP2 and ACP

## Table of Contents

1. [Overview](#overview)
2. [AP2 Protocol (JWT-VC Mandates)](#ap2-protocol)
3. [ACP Protocol (Delegated Tokens)](#acp-protocol)
4. [Protocol Comparison](#protocol-comparison)
5. [Configuration](#configuration)
6. [Integration Examples](#integration-examples)
7. [Webhook Integration](#webhook-integration)
8. [Evidence Packs](#evidence-packs)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Mandate Vault supports two authorization protocols:

- **AP2 (Account Provider Protocol 2)** - JWT-VC based digital mandates
- **ACP (Authorization Credential Protocol)** - Delegated token authorizations

Both protocols are fully integrated into the same unified API, database, and monitoring infrastructure.

---

## AP2 Protocol

### What is AP2?

AP2 is a cryptographically secure protocol for digital mandates based on JWT Verifiable Credentials (JWT-VC). It uses public-key cryptography to create tamper-proof authorization credentials.

### Key Concepts

**Decentralized Identifiers (DIDs)**
- Issuer: `did:example:bank123`
- Subject: `did:example:user456`

**Cryptographic Signatures**
- RSA-256, RSA-384, RSA-512
- ES-256, ES-384, ES-512

**Self-Contained Credentials**
- All data embedded in JWT
- Signature proves authenticity
- No server-side state required for verification

### Creating AP2 Authorizations

```bash
curl -X POST "https://api.yourdomain.com/api/v1/authorizations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "AP2",
    "tenant_id": "tenant-123",
    "payload": {
      "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImRpZDpleGFtcGxlOmlzc3VlcjEyMyNrZXktMSJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZTppc3N1ZXIxMjMiLCJzdWIiOiJkaWQ6ZXhhbXBsZTp1c2VyNDU2IiwiZXhwIjoxNzk1MzE1MjAwLCJpYXQiOjE3MzM3ODMyMDAsInZjIjp7IkBjb250ZXh0IjpbImh0dHBzOi8vd3d3LnczLm9yZy8yMDE4L2NyZWRlbnRpYWxzL3YxIl0sInR5cGUiOlsiVmVyaWZpYWJsZUNyZWRlbnRpYWwiLCJQYXltZW50TWFuZGF0ZSJdLCJjcmVkZW50aWFsU3ViamVjdCI6eyJpZCI6ImRpZDpleGFtcGxlOnVzZXI0NTYiLCJtYW5kYXRlIjp7InNjb3BlIjoicGF5bWVudC5yZWN1cnJpbmciLCJhbW91bnRMaW1pdCI6IjUwMC4wMCIsImN1cnJlbmN5IjoiVVNEIiwiZnJlcXVlbmN5IjoibW9udGhseSJ9fX19.signature..."
    }
  }'
```

### AP2 JWT Structure

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "did:example:issuer123#key-1"
}
```

**Payload:**
```json
{
  "iss": "did:example:issuer123",
  "sub": "did:example:user456",
  "exp": 1795315200,
  "iat": 1733783200,
  "vc": {
    "@context": [
      "https://www.w3.org/2018/credentials/v1"
    ],
    "type": ["VerifiableCredential", "PaymentMandate"],
    "credentialSubject": {
      "id": "did:example:user456",
      "mandate": {
        "scope": "payment.recurring",
        "amountLimit": "500.00",
        "currency": "USD",
        "frequency": "monthly"
      }
    }
  }
}
```

### AP2 Verification Process

1. **Extract JWT** from request
2. **Decode header** and identify signing key (`kid`)
3. **Fetch public key** from issuer's DID document
4. **Verify signature** using public key
5. **Validate claims** (expiration, issuer, etc.)
6. **Check business rules** (amount limits, scope, etc.)

### AP2 Response

```json
{
  "id": "auth-abc123",
  "protocol": "AP2",
  "issuer": "did:example:issuer123",
  "subject": "did:example:user456",
  "scope": {
    "scope": "payment.recurring"
  },
  "amount_limit": "500.00",
  "currency": null,
  "expires_at": "2026-12-31T23:59:59Z",
  "status": "VALID",
  "verification_status": "VALID",
  "verification_reason": "Signature verified successfully",
  "verified_at": "2025-10-01T12:00:00Z",
  "created_at": "2025-10-01T12:00:00Z",
  "updated_at": "2025-10-01T12:00:00Z",
  "tenant_id": "tenant-123"
}
```

---

## ACP Protocol

### What is ACP?

ACP (Authorization Credential Protocol) is a delegated token protocol for payment authorizations. Unlike AP2, ACP uses server-side validation and webhook-based lifecycle management.

### Key Concepts

**PSP-Issued Tokens**
- `psp_id`: Payment Service Provider identifier
- `token_id`: Unique token identifier
- `merchant_id`: Authorized merchant

**Server-Side Validation**
- Rules evaluated on Mandate Vault server
- No cryptographic signature in token
- Webhook events for lifecycle management

**Webhook-Driven Lifecycle**
- `token.used` - Token used for transaction
- `token.revoked` - Token revoked

### Creating ACP Authorizations

```bash
curl -X POST "https://api.yourdomain.com/api/v1/authorizations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "ACP",
    "tenant_id": "tenant-123",
    "payload": {
      "token_id": "acp-token-xyz789",
      "psp_id": "psp-stripe",
      "merchant_id": "merchant-acme",
      "max_amount": "5000.00",
      "currency": "USD",
      "expires_at": "2026-01-31T23:59:59Z",
      "constraints": {
        "merchant": "merchant-acme",
        "category": "retail",
        "item": "electronics"
      }
    }
  }'
```

### ACP Token Structure

```json
{
  "token_id": "acp-token-xyz789",
  "psp_id": "psp-stripe",
  "merchant_id": "merchant-acme",
  "max_amount": "5000.00",
  "currency": "USD",
  "expires_at": "2026-01-31T23:59:59Z",
  "constraints": {
    "merchant": "merchant-acme",
    "category": "retail",
    "item": "electronics"
  }
}
```

### ACP Verification Process

1. **Parse token** from request
2. **Validate schema** (Pydantic strict validation)
3. **Check expiration** (expires_at > now)
4. **Validate amount** (max_amount > 0)
5. **Check constraints** (if merchant constraint set, must match merchant_id)
6. **Check PSP allowlist** (if configured)

### ACP Response

```json
{
  "id": "auth-xyz789",
  "protocol": "ACP",
  "issuer": "psp-stripe",
  "subject": "merchant-acme",
  "scope": {
    "constraints": {
      "merchant": "merchant-acme",
      "category": "retail",
      "item": "electronics"
    }
  },
  "amount_limit": "5000.00",
  "currency": "USD",
  "expires_at": "2026-01-31T23:59:59Z",
  "status": "VALID",
  "verification_status": "VALID",
  "verification_reason": "ACP token verification successful",
  "verified_at": "2025-10-01T12:00:00Z",
  "created_at": "2025-10-01T12:00:00Z",
  "updated_at": "2025-10-01T12:00:00Z",
  "tenant_id": "tenant-123"
}
```

---

## Protocol Comparison

### Technical Comparison

| Feature | AP2 (JWT-VC) | ACP (Delegated Tokens) |
|---------|--------------|------------------------|
| **Authentication** | Cryptographic signature (RSA/EC) | HMAC webhook signatures |
| **Verification** | Public key cryptography | Server-side rule validation |
| **Issuer Format** | DID (`did:example:bank`) | PSP ID (`psp-stripe`) |
| **State** | Stateless (self-contained) | Stateful (server-managed) |
| **Revocation** | Manual API call | Webhook event |
| **Lifecycle Events** | None (self-contained) | `token.used`, `token.revoked` |
| **Currency** | Optional | Required |
| **Constraints** | In scope (flexible) | Structured (merchant, category, item) |
| **Token Size** | Large (JWT ~2KB) | Small (JSON ~500B) |
| **Offline Verification** | Possible (with cached keys) | Not possible |

### Use Case Comparison

| Scenario | Recommended Protocol | Reason |
|----------|---------------------|---------|
| Open Banking mandate | AP2 | Regulatory compliance, cryptographic proof |
| Recurring subscription | AP2 | Long-term, self-contained |
| Card tokenization | ACP | PSP-managed, webhook lifecycle |
| One-time payment auth | ACP | Short-term, simple validation |
| Multi-merchant delegation | ACP | Constraint-based authorization |
| Legal compliance | AP2 | Cryptographic evidence |
| Real-time usage tracking | ACP | Webhook events |

---

## Configuration

### Environment Variables

```bash
# Enable/Disable ACP Protocol
ACP_ENABLE=true

# HMAC Secret for ACP Webhook Signature Verification
ACP_WEBHOOK_SECRET=your-webhook-secret-min-32-chars

# PSP Allowlist (comma-separated, optional)
# If set, only these PSPs can create ACP authorizations
ACP_PSP_ALLOWLIST=psp-stripe,psp-adyen,psp-checkout,psp-worldpay
```

### Configuration Examples

**Disable ACP (AP2 Only):**
```bash
ACP_ENABLE=false
```

**Enable ACP with Security:**
```bash
ACP_ENABLE=true
ACP_WEBHOOK_SECRET=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
ACP_PSP_ALLOWLIST=psp-stripe,psp-adyen
```

**Enable ACP for All PSPs (Less Secure):**
```bash
ACP_ENABLE=true
ACP_WEBHOOK_SECRET=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
# No ACP_PSP_ALLOWLIST = all PSPs allowed
```

---

## Integration Examples

### Python SDK

```python
from mandate_vault import MandateVaultClient

client = MandateVaultClient(
    api_key="your-api-key",
    base_url="https://api.yourdomain.com"
)

# Create AP2 Authorization
ap2_auth = client.authorizations.create(
    protocol="AP2",
    payload={
        "vc_jwt": "eyJhbGc..."
    },
    tenant_id="tenant-123"
)

# Create ACP Authorization
acp_auth = client.authorizations.create(
    protocol="ACP",
    payload={
        "token_id": "acp-token-123",
        "psp_id": "psp-stripe",
        "merchant_id": "merchant-acme",
        "max_amount": "5000.00",
        "currency": "USD",
        "expires_at": "2026-01-31T23:59:59Z",
        "constraints": {
            "category": "retail"
        }
    },
    tenant_id="tenant-123"
)

# Search All Authorizations
results = client.authorizations.search(
    tenant_id="tenant-123",
    protocol="ACP",  # or "AP2" or None for both
    min_amount="1000.00",
    currency="USD"
)

# Re-Verify Authorization
verification = client.authorizations.verify(auth.id)

# Export Evidence Pack
evidence_pack = client.authorizations.export_evidence_pack(auth.id)
with open("evidence.zip", "wb") as f:
    f.write(evidence_pack)
```

### Node.js SDK

```javascript
const { MandateVaultClient } = require('@mandate-vault/sdk');

const client = new MandateVaultClient({
  apiKey: 'your-api-key',
  baseURL: 'https://api.yourdomain.com'
});

// Create AP2 Authorization
const ap2Auth = await client.authorizations.create({
  protocol: 'AP2',
  payload: {
    vcJwt: 'eyJhbGc...'
  },
  tenantId: 'tenant-123'
});

// Create ACP Authorization
const acpAuth = await client.authorizations.create({
  protocol: 'ACP',
  payload: {
    tokenId: 'acp-token-123',
    pspId: 'psp-stripe',
    merchantId: 'merchant-acme',
    maxAmount: '5000.00',
    currency: 'USD',
    expiresAt: '2026-01-31T23:59:59Z',
    constraints: {
      category: 'retail'
    }
  },
  tenantId: 'tenant-123'
});

// Search Authorizations
const results = await client.authorizations.search({
  tenantId: 'tenant-123',
  protocol: 'ACP',
  minAmount: '1000.00',
  currency: 'USD'
});

// Re-Verify Authorization
const verification = await client.authorizations.verify(auth.id);

// Export Evidence Pack
const evidencePack = await client.authorizations.exportEvidencePack(auth.id);
fs.writeFileSync('evidence.zip', evidencePack);
```

---

## Webhook Integration

### ACP Webhook Events

ACP tokens emit lifecycle events that your system must handle:

#### Event: `token.used`

Triggered when a token is used for a transaction.

```json
{
  "event_id": "evt_abc123",
  "event_type": "token.used",
  "timestamp": "2025-10-01T15:30:00Z",
  "data": {
    "token_id": "acp-token-xyz789",
    "amount": "150.00",
    "currency": "USD",
    "transaction_id": "txn_def456",
    "merchant_id": "merchant-acme",
    "metadata": {
      "order_id": "order-789",
      "description": "Product purchase",
      "customer_id": "cust-123"
    }
  }
}
```

**Mandate Vault Action:**
- Logs `USED` event in audit log
- **Does not change status** (token remains `VALID`)
- Records transaction details

#### Event: `token.revoked`

Triggered when a token is revoked by the PSP or user.

```json
{
  "event_id": "evt_xyz456",
  "event_type": "token.revoked",
  "timestamp": "2025-10-01T16:00:00Z",
  "data": {
    "token_id": "acp-token-xyz789",
    "reason": "User requested revocation",
    "revoked_by": "user-123"
  }
}
```

**Mandate Vault Action:**
- Sets status to `REVOKED`
- Logs `REVOKED` event in audit log
- Records revocation timestamp and reason

### Implementing Webhook Handler

**Python (FastAPI):**
```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json

app = FastAPI()

ACP_WEBHOOK_SECRET = os.getenv("ACP_WEBHOOK_SECRET")

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        ACP_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhooks/acp")
async def handle_acp_webhook(request: Request):
    # Get raw body
    payload = await request.body()
    
    # Verify signature
    signature = request.headers.get("X-ACP-Signature")
    if not signature or not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse event
    event = json.loads(payload)
    
    # Handle event
    if event["event_type"] == "token.used":
        print(f"Token used: {event['data']['token_id']}")
        print(f"Amount: {event['data']['amount']} {event['data']['currency']}")
    elif event["event_type"] == "token.revoked":
        print(f"Token revoked: {event['data']['token_id']}")
        print(f"Reason: {event['data']['reason']}")
    
    return {"status": "processed"}
```

**Node.js (Express):**
```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const ACP_WEBHOOK_SECRET = process.env.ACP_WEBHOOK_SECRET;

function verifySignature(payload, signature) {
  const expected = crypto
    .createHmac('sha256', ACP_WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expected)
  );
}

app.post('/webhooks/acp',
  express.raw({ type: 'application/json' }),
  (req, res) => {
    const signature = req.headers['x-acp-signature'];
    
    if (!signature || !verifySignature(req.body, signature)) {
      return res.status(401).send('Invalid signature');
    }
    
    const event = JSON.parse(req.body.toString());
    
    if (event.event_type === 'token.used') {
      console.log(`Token used: ${event.data.token_id}`);
      console.log(`Amount: ${event.data.amount} ${event.data.currency}`);
    } else if (event.event_type === 'token.revoked') {
      console.log(`Token revoked: ${event.data.token_id}`);
      console.log(`Reason: ${event.data.reason}`);
    }
    
    res.status(200).send('OK');
  }
);
```

### Testing Webhooks

```bash
# Test webhook with valid signature
curl -X POST "http://localhost:8000/api/v1/acp/webhook" \
  -H "Content-Type: application/json" \
  -H "X-ACP-Signature: $(echo -n '{"event_id":"evt_test","event_type":"token.used","timestamp":"2025-10-01T12:00:00Z","data":{"token_id":"acp-token-123"}}' | openssl dgst -sha256 -hmac 'your-secret' | awk '{print $2}')" \
  -d '{
    "event_id": "evt_test",
    "event_type": "token.used",
    "timestamp": "2025-10-01T12:00:00Z",
    "data": {
      "token_id": "acp-token-123",
      "amount": "50.00",
      "currency": "USD",
      "transaction_id": "txn_test",
      "merchant_id": "merchant-acme"
    }
  }'
```

---

## Evidence Packs

Evidence packs provide compliance-ready exports of authorization data.

### What's Included?

**AP2 Evidence Pack:**
```
evidence_pack_AP2_auth-abc123_20251001_140000.zip
├── vc_jwt.txt              # Raw JWT token
├── credential.json         # Decoded JWT payload
├── verification.json       # Verification results (signature, expiry)
├── audit.json             # Full audit trail
└── summary.txt            # Human-readable summary
```

**ACP Evidence Pack:**
```
evidence_pack_ACP_auth-xyz789_20251001_140000.zip
├── token.json             # Token data + metadata
├── verification.json      # Verification results
├── audit.json            # Audit trail + usage events
└── summary.txt           # Human-readable summary
```

### Exporting Evidence Packs

```bash
curl -X GET "https://api.yourdomain.com/api/v1/authorizations/auth-abc123/evidence-pack" \
  -H "Authorization: Bearer $TOKEN" \
  --output evidence_pack.zip
```

### Use Cases

- **Compliance Audits**: Provide to auditors
- **Legal Disputes**: Evidence of authorization
- **Regulatory Reporting**: PSD2, GDPR compliance
- **Customer Disputes**: Proof of consent
- **Internal Reviews**: Fraud investigation

---

## Best Practices

### Protocol Selection

**Use AP2 when:**
- ✅ Regulatory compliance required (PSD2, Open Banking)
- ✅ Long-term mandates (months/years)
- ✅ Cryptographic proof needed
- ✅ Offline verification desired
- ✅ Decentralized architecture

**Use ACP when:**
- ✅ Short-term delegations (days/weeks)
- ✅ Real-time lifecycle tracking needed
- ✅ PSP-managed tokens
- ✅ Simple validation rules
- ✅ Webhook-driven workflows

### Security Best Practices

**AP2:**
1. Validate issuer DID against truststore
2. Check key revocation status
3. Verify expiration dates
4. Validate scope and amount limits
5. Store audit logs for 7+ years

**ACP:**
1. Always verify HMAC signatures
2. Use PSP allowlist in production
3. Implement webhook idempotency
4. Validate all constraints
5. Monitor for suspicious patterns

### Performance Optimization

**AP2:**
- Cache public keys (JWKs)
- Use connection pooling for DID resolution
- Batch verification when possible

**ACP:**
- Index `token_id` and `psp_id` columns
- Use database-level constraints
- Implement webhook retry with exponential backoff

---

## Troubleshooting

### AP2 Issues

**Issue:** Signature verification fails
```
Error: "JWT signature verification failed"
```

**Solutions:**
1. Verify issuer DID is in truststore
2. Check key ID (`kid`) matches public key
3. Ensure JWT hasn't been modified
4. Validate algorithm matches (`alg`)

**Issue:** Token expired
```
Error: "JWT has expired"
```

**Solutions:**
1. Check `exp` claim value
2. Verify system clock is synchronized
3. Re-issue credential with new expiration

### ACP Issues

**Issue:** PSP not allowed
```
Error: "PSP 'psp-unknown' is not in the allowlist"
```

**Solutions:**
1. Add PSP to `ACP_PSP_ALLOWLIST`
2. Or remove allowlist (less secure)

**Issue:** Webhook signature invalid
```
Error: "Invalid webhook signature"
```

**Solutions:**
1. Verify `ACP_WEBHOOK_SECRET` matches
2. Use raw request body (don't parse JSON first)
3. Check signature header name: `X-ACP-Signature`

**Issue:** Constraint mismatch
```
Error: "Merchant constraint does not match merchant_id"
```

**Solutions:**
1. Ensure `constraints.merchant` == `merchant_id`
2. Or remove merchant constraint

---

## Monitoring

### Prometheus Metrics

```
# Authorizations by protocol
authorizations_created_total{protocol="AP2"}
authorizations_created_total{protocol="ACP"}

# Verifications by protocol
authorizations_verified_total{protocol="AP2",status="VALID"}
authorizations_verified_total{protocol="ACP",status="EXPIRED"}

# Evidence packs by protocol
evidence_packs_exported_total{protocol="AP2"}
evidence_packs_exported_total{protocol="ACP"}

# ACP webhook events
acp_webhook_events_received_total{event_type="token.used",status="success"}
acp_webhook_signature_failures_total{reason="invalid_signature"}
```

---

## Further Reading

- [Migration Guide](./MIGRATION_GUIDE.md) - Migrate from /mandates to /authorizations
- [API Reference](http://localhost:8000/docs) - Full OpenAPI documentation
- [Python SDK](../sdks/python/README.md) - Official Python client
- [Node.js SDK](../sdks/nodejs/README.md) - Official Node.js client

---

**Updated:** October 2025  
**Version:** 1.0


