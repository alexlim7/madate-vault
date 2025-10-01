# Project Structure

This document describes the organization of the Mandate Vault codebase.

---

## 📁 Directory Organization

```
mandate_vault/
│
├── app/                        # Main application code
│   ├── api/                   # API layer
│   │   └── v1/               # API version 1
│   │       ├── endpoints/    # Route handlers
│   │       └── router.py     # Main router
│   ├── core/                  # Core functionality
│   │   ├── auth.py           # Authentication
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database setup
│   │   ├── monitoring.py     # Monitoring & metrics
│   │   └── security*.py      # Security middleware
│   ├── models/                # SQLAlchemy models
│   │   ├── user.py           # User model
│   │   ├── mandate.py        # Mandate model
│   │   ├── api_key.py        # API key model
│   │   └── ...               # Other models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   │   ├── user_service.py
│   │   ├── mandate_service.py
│   │   ├── webhook_service.py
│   │   └── ...
│   ├── utils/                 # Utility functions
│   ├── workers/               # Background workers
│   └── main.py                # Application entry point
│
├── config/                     # Configuration files
│   ├── prometheus.yml         # Prometheus config
│   ├── alerts.yml             # Alert rules
│   ├── env.*.template         # Environment templates
│   └── grafana/               # Grafana dashboards
│
├── docs/                       # Documentation
│   ├── ONBOARDING.md          # Customer onboarding
│   ├── guides/                # Comprehensive guides
│   │   ├── DATABASE_SETUP.md
│   │   ├── DEPLOYMENT_GUIDE.md
│   │   ├── DEPLOYMENT_INFRASTRUCTURE.md
│   │   ├── MONITORING_GUIDE.md
│   │   ├── SECRETS_MANAGEMENT.md
│   │   └── TESTING_GUIDE.md
│   └── archived/              # Old documentation
│
├── examples/                   # Example applications
│   ├── demo_jwt_verification.py
│   ├── demo_webhook_system.py
│   └── demo_monitoring_system.py
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml               # Auto-scaling
│   └── ...
│
├── scripts/                    # Utility scripts
│   ├── setup_postgres.sh      # Database setup
│   ├── backup_database.sh     # Backup script
│   ├── deploy.sh              # Deployment script
│   ├── local-dev.sh           # Local development setup
│   ├── generate_secret_key.py # Key generation
│   ├── create_users_table.py  # Table creation
│   ├── seed_initial_data.py   # Data seeding
│   └── ...
│
├── sdks/                       # Client SDKs
│   ├── python/                # Python SDK
│   │   ├── mandate_vault/
│   │   ├── setup.py
│   │   └── README.md
│   └── nodejs/                # Node.js SDK
│       ├── src/
│       ├── package.json
│       └── README.md
│
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                # Main Terraform config
│   └── README.md
│
├── tests/                      # Test suites
│   ├── integration/           # Integration tests
│   ├── security/              # Security tests
│   ├── performance/           # Performance benchmarks
│   ├── load/                  # Load tests (k6)
│   └── test_*.py              # Unit tests
│
├── .github/                    # GitHub configuration
│   └── workflows/             # CI/CD pipelines
│       ├── ci.yml            # Continuous Integration
│       └── cd.yml            # Continuous Deployment
│
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   └── env.py
│
├── docker-compose.yml          # Local development stack
├── Dockerfile                  # Production container
├── .dockerignore              # Docker build exclusions
├── requirements.txt            # Python dependencies
├── README.md                   # Main documentation
└── PROJECT_STRUCTURE.md        # This file
```

---

## 📄 Key Files

### Root Level

| File | Purpose |
|------|---------|
| `README.md` | Main documentation & quick start |
| `PROJECT_STRUCTURE.md` | This file - project organization |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Production container image |
| `docker-compose.yml` | Local development stack |
| `run_dashboard.py` | Start application locally |
| `start.py` | Alternative startup script |

### Configuration

| File | Purpose |
|------|---------|
| `config/prometheus.yml` | Prometheus scraping config |
| `config/alerts.yml` | Alert rules |
| `config/env.*.template` | Environment templates |

### Documentation

| File | Purpose |
|------|---------|
| `docs/ONBOARDING.md` | Customer getting started |
| `docs/guides/DATABASE_SETUP.md` | Database configuration |
| `docs/guides/DEPLOYMENT_GUIDE.md` | Cloud deployment |
| `docs/guides/DEPLOYMENT_INFRASTRUCTURE.md` | Docker/K8s deployment |
| `docs/guides/MONITORING_GUIDE.md` | Observability setup |
| `docs/guides/SECRETS_MANAGEMENT.md` | Secrets handling |
| `docs/guides/TESTING_GUIDE.md` | Testing strategy |

---

## 🔍 Finding Things

### "I need to..."

**Add a new API endpoint:**
→ `app/api/v1/endpoints/` - Create or edit endpoint file
→ `app/api/v1/router.py` - Register in router

**Add a database model:**
→ `app/models/` - Create model file
→ `app/models/__init__.py` - Export model
→ `alembic/` - Create migration

**Add business logic:**
→ `app/services/` - Create or edit service file

**Add a test:**
→ `tests/` - Add test file
→ `tests/integration/` - For integration tests
→ `tests/security/` - For security tests

**Configure deployment:**
→ `k8s/` - Kubernetes manifests
→ `terraform/` - Infrastructure code
→ `.github/workflows/` - CI/CD pipelines

**Update documentation:**
→ `docs/` - User-facing documentation
→ `README.md` - Main project readme

---

## 🧹 File Naming Conventions

### Python Files
- `snake_case.py` for all Python files
- `test_*.py` for test files
- `*_service.py` for service classes
- `*_middleware.py` for middleware

### Documentation
- `UPPERCASE.md` for main docs (README, LICENSE)
- `Title_Case.md` for guides
- `lowercase.md` for supporting docs

### Configuration
- `*.yml` or `*.yaml` for YAML files
- `*.template` for environment templates
- `*.json` for JSON configs

---

## 📊 Code Statistics

```
Total Files: 200+
Python Files: 150+
Tests: 45 files
Documentation: 15 guides
Total Lines: 25,000+
Test Coverage: 90%+
```

---

## 🔄 Maintenance

### Adding New Features

1. Create feature branch
2. Add models (if needed) → `app/models/`
3. Add services → `app/services/`
4. Add endpoints → `app/api/v1/endpoints/`
5. Add tests → `tests/`
6. Update docs → `docs/`
7. Create PR

### Database Changes

1. Edit model → `app/models/`
2. Create migration → `alembic revision -m "description"`
3. Test migration → `alembic upgrade head`
4. Update tests

### Deployment Updates

1. Update version → `app/main.py`
2. Tag release → `git tag v1.x.x`
3. Push tag → CI/CD auto-deploys
4. Verify deployment

---

**Last Updated:** October 2025

