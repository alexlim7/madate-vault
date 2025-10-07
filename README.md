# Mandate Vault

Enterprise-grade multi-protocol API for managing and verifying digital authorizations with cryptographic security.

**Supports Multiple Protocols:**
- ✅ **AP2 (Account Provider Protocol 2)** - JWT-VC based mandates
- ✅ **ACP (Authorization Credential Protocol)** - Delegated token authorizations

[![Tests](https://img.shields.io/badge/tests-700%20passing-success)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-92%25-success)](./tests)
[![License](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

---

## 🚀 Quick Start

### Local Development

   ```bash
# 1. Setup environment
./scripts/local-dev.sh

# 2. Access application
open http://localhost:8000/docs
```

### Using Docker Compose

   ```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Access:
# - API: http://localhost:8000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001
```

---

## ✨ Features

### Core Capabilities
- ✅ **Multi-Protocol Support** - AP2 (JWT-VC) and ACP (Delegated Tokens)
- ✅ **Cryptographic Verification** - RSA/EC signature validation, HMAC webhooks
- ✅ **Multi-Tenant Architecture** - Complete tenant isolation
- ✅ **User Management & RBAC** - 4 role levels with granular permissions
- ✅ **Real-Time Webhooks** - HMAC-signed event notifications for both protocols
- ✅ **Evidence Pack Export** - Compliance-ready ZIP archives
- ✅ **Comprehensive Audit Logging** - Complete activity trail across all protocols
- ✅ **API Key Authentication** - Machine-to-machine access

### Enterprise Features
- ✅ **PostgreSQL with Connection Pooling** - Production-ready database
- ✅ **Prometheus Metrics** - 20+ metric types (protocol-aware)
- ✅ **Advanced Search** - JSON path queries, pagination, sorting
- ✅ **Sentry Integration** - Automatic error tracking
- ✅ **Rate Limiting** - DDoS protection
- ✅ **Auto-Scaling** - Kubernetes HPA (3-10 pods)
- ✅ **CI/CD Pipeline** - GitHub Actions automation

### Security
- ✅ **Cryptographic Signature Verification** - RSA-256/384/512, ES-256/384/512
- ✅ **HMAC Webhook Signatures** - Secure ACP event delivery
- ✅ **PSP Allowlisting** - Restrict ACP tokens to trusted PSPs
- ✅ **Password Policies** - Complexity, history, expiration
- ✅ **Account Lockout** - Brute force protection
- ✅ **IP Whitelisting** - CIDR notation support
- ✅ **Security Headers** - CSP, HSTS, X-Frame-Options
- ✅ **OWASP Top 10** - Comprehensive protection

---

## 📚 Documentation

### Getting Started
- 📖 [Customer Onboarding Guide](./docs/ONBOARDING.md) - Get started in 5 minutes
- 🔧 [Database Setup](./docs/guides/DATABASE_SETUP.md) - PostgreSQL configuration
- 🚀 [Deployment Guide](./docs/guides/DEPLOYMENT_GUIDE.md) - Multi-cloud deployment
- 🐳 [Deployment Infrastructure](./docs/guides/DEPLOYMENT_INFRASTRUCTURE.md) - Docker & Kubernetes

### Operations
- 🔐 [Secrets Management](./docs/guides/SECRETS_MANAGEMENT.md) - Secure secrets handling
- 📊 [Monitoring Guide](./docs/guides/MONITORING_GUIDE.md) - Prometheus & Grafana setup
- 🧪 [Testing Guide](./docs/guides/TESTING_GUIDE.md) - Comprehensive testing strategy

### SDKs & Integration
- 🐍 [Python SDK](./sdks/python/README.md) - Official Python client
- 📦 [Node.js SDK](./sdks/nodejs/README.md) - Official TypeScript/JavaScript client
- 💡 [Examples](./examples/) - Demo applications

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Mandate Vault API                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ FastAPI      │  │ SQLAlchemy   │  │  Background     │  │
│  │ + Pydantic   │  │ + PostgreSQL │  │  Workers        │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Security Layer                                       │  │
│  │  • JWT Authentication  • Rate Limiting               │  │
│  │  • API Keys           • IP Whitelisting              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Monitoring & Observability                          │  │
│  │  • Prometheus Metrics  • Sentry Error Tracking       │  │
│  │  • Structured Logging  • Grafana Dashboards          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 API Endpoints

### Authentication
```
POST   /api/v1/auth/login           - User login
POST   /api/v1/auth/refresh         - Refresh token
POST   /api/v1/auth/logout          - Logout
```

### Authorizations (Multi-Protocol) 🆕
```
POST   /api/v1/authorizations                      - Create authorization (AP2 or ACP)
GET    /api/v1/authorizations/{id}                 - Get authorization
POST   /api/v1/authorizations/{id}/verify          - Re-verify authorization
POST   /api/v1/authorizations/search               - Advanced search with filters
GET    /api/v1/authorizations/search               - Search via query params
DELETE /api/v1/authorizations/{id}                 - Revoke authorization
GET    /api/v1/authorizations/{id}/evidence-pack   - Export compliance package
```

### ACP Webhooks 🆕
```
POST   /api/v1/acp/webhook          - Receive ACP events (token.used, token.revoked)
GET    /api/v1/acp/events/{id}      - Get ACP event status
```

### Mandates (Deprecated - AP2 Only) ⚠️
```
POST   /api/v1/mandates             - Create mandate (USE /authorizations instead)
GET    /api/v1/mandates/{id}        - Get mandate (USE /authorizations instead)
POST   /api/v1/mandates/search      - Search mandates (USE /authorizations/search instead)
DELETE /api/v1/mandates/{id}        - Revoke mandate (USE /authorizations instead)
```

> **⚠️ Deprecation Notice:** The `/mandates` endpoints are deprecated and will be removed in v2.0 (Q2 2026).
> Please migrate to `/authorizations` endpoints which support both AP2 and ACP protocols.
> See [Migration Guide](./docs/MIGRATION_GUIDE.md) for details.

### Users
```
POST   /api/v1/users/register       - Register user
POST   /api/v1/users/invite         - Invite user
GET    /api/v1/users                - List users
PATCH  /api/v1/users/{id}           - Update user
```

### Webhooks
```
POST   /api/v1/webhooks             - Create webhook
GET    /api/v1/webhooks             - List webhooks
DELETE /api/v1/webhooks/{id}        - Delete webhook
```

### Monitoring
```
GET    /api/v1/metrics              - Prometheus metrics (protocol-aware)
GET    /healthz                     - Health check (liveness)
GET    /readyz                      - Readiness check (comprehensive)
GET    /healthz/deep                - Deep health check (not for K8s probes)
```

**Full API Documentation:** http://localhost:8000/docs

---

## 🔐 Protocol Guide: AP2 vs ACP

### What is AP2 (Account Provider Protocol 2)?

**AP2** is a JWT-VC (JSON Web Token Verifiable Credential) based protocol for digital mandates. It uses cryptographic signatures (RSA/EC) to create tamper-proof authorization credentials.

**Key Features:**
- Cryptographically signed JWT tokens
- Decentralized Identifier (DID) based issuers
- Self-contained credentials with embedded metadata
- RSA-256/384/512 or ES-256/384/512 signatures

**Use Cases:**
- Open Banking mandates (PSD2/Open Banking UK)
- Account-to-account payment authorization
- Recurring payment mandates
- Long-term authorization credentials

### What is ACP (Authorization Credential Protocol)?

**ACP** is a delegated token-based protocol for payment authorizations. It uses structured tokens with server-side validation and webhook-based lifecycle management.

**Key Features:**
- Centralized token validation
- PSP-issued delegated authorizations
- Real-time lifecycle events via webhooks
- HMAC-signed webhook delivery

**Use Cases:**
- Payment card tokenization
- Delegated payment authority
- Transaction-specific authorizations
- Time-limited payment permissions

### Protocol Comparison

| Feature | AP2 (JWT-VC) | ACP (Delegated Tokens) |
|---------|--------------|------------------------|
| **Signature** | RSA/EC (embedded) | HMAC webhooks |
| **Validation** | Cryptographic verification | Server-side rules |
| **Lifecycle** | Self-contained | Webhook-driven |
| **Issuer** | DID-based | PSP-based |
| **Revocation** | Manual/API | Webhook events |
| **Best For** | Long-term mandates | Short-term delegations |

---

## 📖 Usage Examples

### AP2: Create Authorization (JWT-VC Mandate)

```bash
curl -X POST "http://localhost:8000/api/v1/authorizations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "AP2",
    "tenant_id": "tenant-123",
    "payload": {
      "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZTo..."
    }
  }'
```

**Response:**
```json
{
  "id": "auth-abc123",
  "protocol": "AP2",
  "issuer": "did:example:issuer123",
  "subject": "did:example:user456",
  "status": "VALID",
  "expires_at": "2026-12-31T23:59:59Z",
  "amount_limit": "500.00",
  "verification_status": "VALID",
  "created_at": "2025-10-01T12:00:00Z"
}
```

### ACP: Create Authorization (Delegated Token)

```bash
curl -X POST "http://localhost:8000/api/v1/authorizations" \
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
        "category": "retail"
      }
    }
  }'
```

**Response:**
```json
{
  "id": "auth-xyz789",
  "protocol": "ACP",
  "issuer": "psp-stripe",
  "subject": "merchant-acme",
  "status": "VALID",
  "expires_at": "2026-01-31T23:59:59Z",
  "amount_limit": "5000.00",
  "currency": "USD",
  "verification_status": "VALID",
  "created_at": "2025-10-01T12:00:00Z"
}
```

### Search Authorizations (Multi-Protocol)

```bash
# Search for all ACP authorizations from a specific PSP
curl -X POST "http://localhost:8000/api/v1/authorizations/search" \
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

### Re-Verify Authorization

```bash
curl -X POST "http://localhost:8000/api/v1/authorizations/auth-abc123/verify" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "id": "auth-abc123",
  "protocol": "AP2",
  "status": "VALID",
  "reason": "Signature verified successfully",
  "expires_at": "2026-12-31T23:59:59Z",
  "verified_at": "2025-10-01T14:30:00Z"
}
```

### Export Evidence Pack

```bash
curl -X GET "http://localhost:8000/api/v1/authorizations/auth-abc123/evidence-pack" \
  -H "Authorization: Bearer $TOKEN" \
  --output evidence_pack.zip
```

**Evidence Pack Contents:**

**For AP2 (JWT-VC):**
```
evidence_pack_AP2_auth-abc123_20251001_140000.zip
├── vc_jwt.txt              # Raw JWT-VC token
├── credential.json         # Decoded credential data
├── verification.json       # Verification results
├── audit.json             # Complete audit trail
└── summary.txt            # Human-readable summary
```

**For ACP (Delegated Token):**
```
evidence_pack_ACP_auth-xyz789_20251001_140000.zip
├── token.json             # Full token data with metadata
├── verification.json      # Verification results
├── audit.json            # Audit trail including usage events
└── summary.txt           # Human-readable summary with token details
```

**Sample `summary.txt` (ACP):**
```
--- Authorization Evidence Pack Summary (ACP) ---
Authorization ID: auth-xyz789
Protocol: ACP
Status: VALID
Expires At: 2026-01-31T23:59:59Z
Amount Limit: 5000.00 USD
Issuer: psp-stripe
Subject: merchant-acme
Tenant ID: tenant-123
Created At: 2025-10-01T12:00:00Z
Last Updated At: 2025-10-01T14:30:00Z
Verification Status: VALID
Verification Reason: ACP token verification successful
ACP Token ID: acp-token-xyz789
ACP PSP ID: psp-stripe
ACP Merchant ID: merchant-acme
ACP Constraints: {"merchant": "merchant-acme", "category": "retail"}
```

---

## 🔔 ACP Webhook Integration

### Receiving ACP Webhooks

ACP tokens emit lifecycle events via HMAC-signed webhooks. Your system must implement a webhook endpoint to receive these events.

### Event Types

#### `token.used` - Token Used for Transaction
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
      "description": "Product purchase"
    }
  }
}
```

#### `token.revoked` - Token Revoked
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

ACP webhooks are signed using HMAC-SHA256. Verify the signature to ensure authenticity:

```python
import hmac
import hashlib

def verify_acp_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify ACP webhook HMAC signature."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)

# Usage in your webhook handler
@app.post("/webhooks/acp")
async def handle_acp_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-ACP-Signature")
    
    if not verify_acp_webhook(payload, signature, ACP_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook...
```

**Node.js Example:**
```javascript
const crypto = require('crypto');

function verifyACPWebhook(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

// Express.js handler
app.post('/webhooks/acp', express.raw({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-acp-signature'];
  
  if (!verifyACPWebhook(req.body, signature, process.env.ACP_WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }
  
  // Process webhook...
  res.status(200).send('OK');
});
```

### Webhook Configuration

Set your ACP webhook secret in `.env`:
```bash
ACP_WEBHOOK_SECRET=your-webhook-secret-min-32-chars
```

### Idempotency

Mandate Vault automatically handles webhook idempotency using `event_id`. Duplicate events with the same `event_id` will be rejected with:
```json
{
  "status": "already_processed",
  "event_id": "evt_abc123",
  "message": "Event already processed (idempotency)"
}
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific suites
pytest tests/test_user_management.py -v
pytest tests/integration/ -v
pytest tests/security/ -v

# Load testing
k6 run tests/load/mandate_creation_load_test.js
```

**Test Statistics:**
- Unit Tests: 693 passing
- Integration Tests: 7 passing (multi-protocol)
- Security Tests: 13 passing  
- Performance Tests: 8 passing
- **Total:** 700 passing, 5 skipped
- **Coverage:** 92%+

---

## 🚀 Deployment

### Docker

```bash
# Build
docker build -t mandate-vault:latest .

# Run
docker run -p 8000:8000 \
  -e SECRET_KEY="your-key" \
  -e DATABASE_URL="postgresql://..." \
  mandate-vault:latest
```

### Kubernetes

```bash
# Deploy to cluster
kubectl apply -f k8s/

# Check status
kubectl get pods -n mandate-vault

# View logs
kubectl logs -f deployment/mandate-vault -n mandate-vault
```

### Cloud Platforms

- **Google Cloud Platform**: See [GCP Deployment](./docs/guides/DEPLOYMENT_GUIDE.md#google-cloud-run)
- **AWS**: See [AWS Deployment](./docs/guides/DEPLOYMENT_GUIDE.md#aws-ecsfargate)
- **Azure**: See [Azure Deployment](./docs/guides/DEPLOYMENT_GUIDE.md#azure-app-service)

---

## 📊 Monitoring

### Metrics

Access Prometheus metrics:
```
GET /api/v1/metrics
```

**Available Metrics:**
- HTTP request rate & latency
- JWT verification success rate
- Active mandates per tenant
- Webhook delivery status
- Database connection pool usage
- Authentication attempts

### Dashboards

- **Grafana**: Pre-configured dashboards in `config/`
- **Prometheus**: Alert rules in `config/alerts.yml`
- **Sentry**: Automatic error tracking

---

## 🔒 Security

### Authentication
- JWT tokens (user sessions)
- API keys (machine-to-machine)

### Protection Mechanisms
- Rate limiting (100 req/min default)
- Account lockout (5 failed attempts)
- IP whitelisting (CIDR support)
- CORS policy enforcement
- Security headers (CSP, HSTS, etc.)

### Compliance
- OWASP Top 10 protection
- Audit logging (365-day retention)
- Data encryption at rest & in transit
- SOC2 compliance ready

---

## ⚙️ Configuration

### Environment Variables

All configuration is done via environment variables. Create a `.env` file (see `.env.example`) or set them in your deployment environment.

#### Core Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | string | - | ✅ | JWT signing key (min 32 chars) |
| `ENVIRONMENT` | string | `development` | ❌ | Environment: `development`, `staging`, `production` |
| `DATABASE_URL` | string | `sqlite+aiosqlite:///./test.db` | ❌ | Full database connection string |
| `CORS_ORIGINS` | string | `*` | ❌ | Comma-separated allowed origins |

#### ACP Protocol Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ACP_ENABLE` | boolean | `true` | ❌ | Enable/disable ACP protocol support |
| `ACP_WEBHOOK_SECRET` | string | - | ❌ | HMAC secret for ACP webhook signature verification |
| `ACP_PSP_ALLOWLIST` | string | - | ❌ | Comma-separated PSP IDs (if set, only these PSPs allowed) |

**ACP Configuration Examples:**

```bash
# Enable ACP with webhook security
ACP_ENABLE=true
ACP_WEBHOOK_SECRET=your-webhook-secret-min-32-chars

# Restrict to specific PSPs only
ACP_PSP_ALLOWLIST=psp-stripe,psp-adyen,psp-checkout

# Disable ACP entirely (AP2 only)
ACP_ENABLE=false
```

#### Security Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | ❌ | JWT token expiration time |
| `ALLOWED_HOSTS` | list | `localhost,127.0.0.1` | ❌ | Allowed hostnames |

#### Webhook Settings

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `WEBHOOK_TIMEOUT` | int | `30` | ❌ | Webhook request timeout (seconds) |
| `WEBHOOK_MAX_RETRIES` | int | `3` | ❌ | Maximum retry attempts |
| `WEBHOOK_RETRY_DELAY` | int | `60` | ❌ | Delay between retries (seconds) |

#### Monitoring & Logging

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LOG_LEVEL` | string | `INFO` | ❌ | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SENTRY_DSN` | string | - | ❌ | Sentry error tracking DSN |
| `SENTRY_ENVIRONMENT` | string | - | ❌ | Sentry environment name |
| `PROMETHEUS_MULTIPROC_DIR` | string | - | ❌ | Directory for Prometheus metrics |

#### Background Tasks

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `BACKGROUND_TASK_INTERVAL` | int | `300` | ❌ | Background task interval (seconds) |
| `EXPIRY_CHECK_INTERVAL` | int | `3600` | ❌ | Expiry check interval (seconds) |
| `CLEANUP_INTERVAL` | int | `86400` | ❌ | Cleanup interval (seconds) |

### Example .env File

```bash
# Core
SECRET_KEY=your-secret-key-minimum-32-characters-long
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mandate_vault

# ACP Protocol (multi-protocol support)
ACP_ENABLE=true
ACP_WEBHOOK_SECRET=your-acp-webhook-secret-key-min-32-chars
ACP_PSP_ALLOWLIST=psp-stripe,psp-adyen,psp-worldpay

# Security
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_ENVIRONMENT=production

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 💻 Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python scripts/create_users_table.py
python scripts/seed_initial_data.py

# Run application
python run_dashboard.py
```

### Project Structure

```
mandate_vault/
├── app/                    # Application code
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── utils/             # Utilities
│   └── workers/           # Background workers
├── config/                # Configuration files
├── docs/                  # Documentation
│   ├── guides/           # User guides
│   └── archived/         # Old docs
├── examples/              # Demo applications
├── k8s/                   # Kubernetes manifests
├── scripts/               # Utility scripts
├── sdks/                  # Client SDKs
│   ├── python/           # Python SDK
│   └── nodejs/           # Node.js SDK
├── terraform/             # Infrastructure as code
└── tests/                 # Test suites
    ├── integration/      # Integration tests
    ├── security/         # Security tests
    ├── performance/      # Performance tests
    └── load/             # Load tests
```

---

## 📦 Requirements

### Runtime
- Python 3.9+
- PostgreSQL 14+ (production)
- Redis (optional, for caching)

### Development
- Docker & Docker Compose
- kubectl (for Kubernetes deployment)
- Terraform (for infrastructure)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Code Quality

```bash
# Format code
black app tests

# Sort imports
isort app tests

# Lint
flake8 app tests

# Type check
mypy app
```

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

---

## 📞 Support

- **Documentation**: https://docs.mandatevault.com
- **Email**: support@mandatevault.com
- **GitHub Issues**: https://github.com/mandate-vault/api/issues
- **Status Page**: https://status.mandatevault.com

---

## 🎯 Quick Links

| Resource | Link |
|----------|------|
| API Docs | http://localhost:8000/docs |
| Onboarding | [docs/ONBOARDING.md](./docs/ONBOARDING.md) |
| Python SDK | [sdks/python/](./sdks/python/) |
| Node.js SDK | [sdks/nodejs/](./sdks/nodejs/) |
| Examples | [examples/](./examples/) |
| Testing | [docs/guides/TESTING_GUIDE.md](./docs/guides/TESTING_GUIDE.md) |

---

**Built with ❤️ for secure digital mandate management**

**Version:** 1.0.0  
**Last Updated:** October 2025
