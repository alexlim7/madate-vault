# Mandate Vault Documentation

Welcome to the Mandate Vault documentation! This guide will help you integrate, deploy, and operate the multi-protocol authorization platform.

---

## 🚀 Getting Started

### Quick Start Guides

- **[Customer Onboarding](./ONBOARDING.md)** - Get started in 5 minutes
- **[Multi-Protocol Guide](./MULTIPROTOCOL_GUIDE.md)** - AP2 vs ACP protocols explained
- **[Migration Guide](./MIGRATION_GUIDE.md)** - Migrate from /mandates to /authorizations

### Core Concepts

**What is AP2?**
- JWT-VC based digital mandates
- Cryptographically signed with RSA/EC
- DID-based issuers and subjects
- Self-contained, stateless credentials

**What is ACP?**
- Delegated token authorizations
- PSP-issued tokens
- Server-side validation
- Webhook-driven lifecycle

**[Read the full comparison →](./MULTIPROTOCOL_GUIDE.md#protocol-comparison)**

---

## 📖 Core Documentation

### Integration

- **[Multi-Protocol Guide](./MULTIPROTOCOL_GUIDE.md)** - Complete guide to AP2 and ACP protocols
  - Protocol comparison
  - Integration examples
  - Webhook handling
  - Evidence packs
  - Best practices

- **[Migration Guide](./MIGRATION_GUIDE.md)** - Migrate from legacy /mandates endpoints
  - Step-by-step migration
  - Code examples (Python, Node.js)
  - Troubleshooting
  - FAQ

### Operations

- **[Database Setup](./guides/DATABASE_SETUP.md)** - PostgreSQL configuration
  - Connection pooling
  - Backup/restore
  - Performance tuning

- **[Deployment Guide](./guides/DEPLOYMENT_GUIDE.md)** - Multi-cloud deployment
  - Google Cloud Platform
  - AWS ECS/Fargate
  - Azure App Service

- **[Deployment Infrastructure](./guides/DEPLOYMENT_INFRASTRUCTURE.md)** - Docker & Kubernetes
  - Docker Compose
  - Kubernetes manifests
  - Helm charts
  - CI/CD pipelines

- **[Secrets Management](./guides/SECRETS_MANAGEMENT.md)** - Secure configuration
  - Google Secret Manager
  - AWS Secrets Manager
  - Kubernetes Secrets
  - Environment variables

### Monitoring & Testing

- **[Monitoring Guide](./guides/MONITORING_GUIDE.md)** - Observability setup
  - Prometheus metrics
  - Grafana dashboards
  - Sentry error tracking
  - Structured logging

- **[Testing Guide](./guides/TESTING_GUIDE.md)** - Comprehensive testing strategy
  - Unit tests
  - Integration tests
  - Security tests
  - Load tests

---

## 🔧 API Reference

### Multi-Protocol Endpoints

**Authorizations (New - Recommended)**
```
POST   /api/v1/authorizations                      - Create authorization (AP2 or ACP)
GET    /api/v1/authorizations/{id}                 - Get authorization
POST   /api/v1/authorizations/{id}/verify          - Re-verify authorization
POST   /api/v1/authorizations/search               - Advanced search
DELETE /api/v1/authorizations/{id}                 - Revoke authorization
GET    /api/v1/authorizations/{id}/evidence-pack   - Export compliance package
```

**ACP Webhooks**
```
POST   /api/v1/acp/webhook                         - Receive ACP events
GET    /api/v1/acp/events/{id}                     - Get event status
```

**Mandates (Deprecated)**
```
POST   /api/v1/mandates                            - Create mandate (USE /authorizations)
GET    /api/v1/mandates/{id}                       - Get mandate (USE /authorizations)
POST   /api/v1/mandates/search                     - Search mandates (USE /authorizations/search)
DELETE /api/v1/mandates/{id}                       - Revoke mandate (USE /authorizations)
```

> **⚠️ Deprecation Notice:** `/mandates` endpoints will be removed in v2.0 (Q2 2026).
> Migrate to `/authorizations` for multi-protocol support.

**[Full API Documentation →](http://localhost:8000/docs)**

---

## 📚 Protocol Examples

### AP2: Create JWT-VC Authorization

```bash
curl -X POST "https://api.yourdomain.com/api/v1/authorizations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "AP2",
    "tenant_id": "tenant-123",
    "payload": {
      "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }'
```

### ACP: Create Delegated Token

```bash
curl -X POST "https://api.yourdomain.com/api/v1/authorizations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "ACP",
    "tenant_id": "tenant-123",
    "payload": {
      "token_id": "acp-token-123",
      "psp_id": "psp-stripe",
      "merchant_id": "merchant-acme",
      "max_amount": "5000.00",
      "currency": "USD",
      "expires_at": "2026-01-31T23:59:59Z",
      "constraints": {
        "merchant": "merchant-acme",
        "category": "retail"
      }
    }
  }'
```

### Search Multi-Protocol

```bash
curl -X POST "https://api.yourdomain.com/api/v1/authorizations/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-123",
    "protocol": "ACP",
    "issuer": "psp-stripe",
    "status": "VALID",
    "min_amount": "1000.00",
    "currency": "USD",
    "limit": 50,
    "sort_by": "created_at",
    "sort_order": "desc"
  }'
```

**[More examples →](./MULTIPROTOCOL_GUIDE.md#integration-examples)**

---

## 🔔 ACP Webhook Integration

### Event Types

**`token.used`** - Token used for transaction
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
    "merchant_id": "merchant-acme"
  }
}
```

**`token.revoked`** - Token revoked
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

### HMAC Signature Verification

```python
import hmac
import hashlib

def verify_acp_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# Usage
@app.post("/webhooks/acp")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-ACP-Signature")
    
    if not verify_acp_webhook(payload, signature, ACP_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process event...
```

**[Complete webhook guide →](./MULTIPROTOCOL_GUIDE.md#webhook-integration)**

---

## 📦 Evidence Packs

### What's Included?

**AP2 Evidence Pack:**
```
evidence_pack_AP2_auth-abc123_20251001_140000.zip
├── vc_jwt.txt              # Raw JWT token
├── credential.json         # Decoded JWT payload
├── verification.json       # Verification results
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

### Exporting

```bash
curl -X GET "https://api.yourdomain.com/api/v1/authorizations/{id}/evidence-pack" \
  -H "Authorization: Bearer $TOKEN" \
  --output evidence_pack.zip
```

**Use Cases:**
- Compliance audits
- Legal disputes
- Regulatory reporting
- Customer disputes
- Internal reviews

**[Evidence pack details →](./MULTIPROTOCOL_GUIDE.md#evidence-packs)**

---

## 🛠️ SDKs & Tools

### Official SDKs

- **[Python SDK](../sdks/python/README.md)** - Official Python client
  ```python
  from mandate_vault import MandateVaultClient
  
  client = MandateVaultClient(api_key="your-key")
  auth = client.authorizations.create(protocol="AP2", ...)
  ```

- **[Node.js SDK](../sdks/nodejs/README.md)** - Official TypeScript/JavaScript client
  ```javascript
  const { MandateVaultClient } = require('@mandate-vault/sdk');
  
  const client = new MandateVaultClient({ apiKey: 'your-key' });
  const auth = await client.authorizations.create({ protocol: 'AP2', ... });
  ```

### Example Applications

- **[Python Example](../examples/python/)** - FastAPI integration
- **[Node.js Example](../examples/nodejs/)** - Express.js integration
- **[Webhook Handler](../examples/webhooks/)** - ACP webhook receiver

---

## ⚙️ Configuration

### Environment Variables

**Core Settings:**
```bash
SECRET_KEY=your-secret-key-minimum-32-characters-long
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mandate_vault
```

**ACP Protocol:**
```bash
ACP_ENABLE=true
ACP_WEBHOOK_SECRET=your-webhook-secret-min-32-chars
ACP_PSP_ALLOWLIST=psp-stripe,psp-adyen,psp-worldpay
```

**Monitoring:**
```bash
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
```

**[Complete configuration guide →](../README.md#configuration)**

---

## 🔒 Security

### Best Practices

**AP2:**
- ✅ Validate issuer DIDs against truststore
- ✅ Check key revocation status
- ✅ Verify expiration dates
- ✅ Store audit logs for 7+ years

**ACP:**
- ✅ Always verify HMAC signatures
- ✅ Use PSP allowlist in production
- ✅ Implement webhook idempotency
- ✅ Monitor for suspicious patterns

**[Security guide →](./MULTIPROTOCOL_GUIDE.md#best-practices)**

---

## 📊 Monitoring

### Health Checks

```bash
# Liveness (Kubernetes)
GET /healthz

# Readiness (Comprehensive)
GET /readyz

# Deep Health Check
GET /healthz/deep
```

### Prometheus Metrics

```
# Multi-protocol metrics
authorizations_created_total{protocol="AP2"}
authorizations_created_total{protocol="ACP"}

# Evidence packs
evidence_packs_exported_total{protocol="AP2"}
evidence_packs_exported_total{protocol="ACP"}

# ACP webhooks
acp_webhook_events_received_total{event_type="token.used"}
acp_webhook_signature_failures_total{reason="invalid_signature"}
```

**[Monitoring guide →](./guides/MONITORING_GUIDE.md)**

---

## 🧪 Testing

### Test Statistics

- **Unit Tests:** 693 passing
- **Integration Tests:** 7 passing (multi-protocol)
- **Security Tests:** 13 passing
- **Performance Tests:** 8 passing
- **Total:** 700 passing, 5 skipped
- **Coverage:** 92%+

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific suites
pytest tests/acp/ -v
pytest tests/integration/ -v
pytest tests/security/ -v
```

**[Testing guide →](./guides/TESTING_GUIDE.md)**

---

## 🆘 Support

### Resources

- **Documentation:** https://docs.mandatevault.com
- **Email:** support@mandatevault.com
- **GitHub Issues:** https://github.com/mandate-vault/api/issues
- **Status Page:** https://status.mandatevault.com

### Common Issues

**See troubleshooting sections in:**
- [Migration Guide](./MIGRATION_GUIDE.md#troubleshooting)
- [Multi-Protocol Guide](./MULTIPROTOCOL_GUIDE.md#troubleshooting)
- [Testing Guide](./guides/TESTING_GUIDE.md)

---

## 📝 Changelog

### v1.0.0 (October 2025)

**Multi-Protocol Support:**
- ✅ Added ACP (Authorization Credential Protocol)
- ✅ New `/authorizations` endpoints
- ✅ Deprecated `/mandates` endpoints
- ✅ Evidence pack export
- ✅ Advanced search with JSON path queries

**Infrastructure:**
- ✅ Enhanced health checks (liveness, readiness, deep)
- ✅ Protocol-aware Prometheus metrics
- ✅ Comprehensive audit logging
- ✅ 700+ passing tests

---

## 📖 Document Index

### Getting Started
- [Customer Onboarding](./ONBOARDING.md)
- [Multi-Protocol Guide](./MULTIPROTOCOL_GUIDE.md)
- [Migration Guide](./MIGRATION_GUIDE.md)

### Operations
- [Database Setup](./guides/DATABASE_SETUP.md)
- [Deployment Guide](./guides/DEPLOYMENT_GUIDE.md)
- [Deployment Infrastructure](./guides/DEPLOYMENT_INFRASTRUCTURE.md)
- [Secrets Management](./guides/SECRETS_MANAGEMENT.md)
- [Monitoring Guide](./guides/MONITORING_GUIDE.md)
- [Testing Guide](./guides/TESTING_GUIDE.md)

### SDKs
- [Python SDK](../sdks/python/README.md)
- [Node.js SDK](../sdks/nodejs/README.md)

### Examples
- [Python Example](../examples/python/)
- [Node.js Example](../examples/nodejs/)
- [Webhook Handler](../examples/webhooks/)

---

**Updated:** October 2025  
**Version:** 1.0.0

**Built with ❤️ for secure digital authorization management**


