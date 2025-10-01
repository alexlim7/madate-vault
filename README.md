# Mandate Vault

Enterprise-grade API for managing and verifying JWT-VC (Verifiable Credential) mandates with cryptographic security.

[![Tests](https://img.shields.io/badge/tests-624%20passing-success)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-90%25-success)](./tests)
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
- ✅ **Cryptographic JWT-VC Verification** - RSA/EC signature validation
- ✅ **Multi-Tenant Architecture** - Complete tenant isolation
- ✅ **User Management & RBAC** - 4 role levels with granular permissions
- ✅ **Real-Time Webhooks** - HMAC-signed event notifications
- ✅ **Comprehensive Audit Logging** - Complete activity trail
- ✅ **API Key Authentication** - Machine-to-machine access

### Enterprise Features
- ✅ **PostgreSQL with Connection Pooling** - Production-ready database
- ✅ **Prometheus Metrics** - 14+ metric types
- ✅ **Sentry Integration** - Automatic error tracking
- ✅ **Rate Limiting** - DDoS protection
- ✅ **Auto-Scaling** - Kubernetes HPA (3-10 pods)
- ✅ **CI/CD Pipeline** - GitHub Actions automation

### Security
- ✅ **Cryptographic Signature Verification** - RSA-256/384/512, ES-256/384/512
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

### Mandates
```
POST   /api/v1/mandates             - Create mandate
GET    /api/v1/mandates/{id}        - Get mandate
POST   /api/v1/mandates/search      - Search mandates
DELETE /api/v1/mandates/{id}        - Revoke mandate
```

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
GET    /api/v1/metrics              - Prometheus metrics
GET    /healthz                     - Health check
GET    /readyz                      - Readiness check
```

**Full API Documentation:** http://localhost:8000/docs

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
- Unit Tests: 624 passing
- Integration Tests: 4 passing
- Security Tests: 13 passing  
- Performance Tests: 8 passing
- **Total Coverage:** 90%+

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
