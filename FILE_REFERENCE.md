# Mandate Vault - File Reference Guide

Complete reference of key files organized by functionality.

---

## (a) DATABASE MODELS / TABLES

### Core Models
| File | Model | Purpose |
|------|-------|---------|
| `app/models/mandate.py` | `Mandate` | Main mandate storage with JWT-VC |
| `app/models/user.py` | `User` | User accounts with RBAC |
| `app/models/customer.py` | `Customer` | Tenant/organization data |
| `app/models/api_key.py` | `APIKey` | API key for M2M authentication |
| `app/models/webhook.py` | `Webhook`, `WebhookDelivery` | Webhook subscriptions & delivery logs |
| `app/models/audit.py` | `AuditLog` | Audit trail entries |
| `app/models/alert.py` | `Alert` | Alert configuration |

### Model Index
| File | Purpose |
|------|---------|
| `app/models/__init__.py` | Exports all models |

### Database Migrations
| File | Purpose |
|------|---------|
| `alembic/env.py` | Alembic configuration |
| `alembic/versions/001_initial_migration.py` | Initial schema |
| `alembic/versions/002_update_schema.py` | Schema updates |
| `alembic/versions/003_add_verification_fields.py` | Verification fields |
| `alembic/versions/004_add_webhooks_and_alerts.py` | Webhooks & alerts |

### Database Configuration
| File | Purpose |
|------|---------|
| `app/core/database.py` | Database engine, session, connection pooling |
| `alembic.ini` | Alembic configuration file |

---

## (b) MANDATE / API VERIFICATION

### JWT-VC Verification Core
| File | Purpose |
|------|---------|
| `app/services/verification_service.py` | Main verification service with VerificationResult |
| `app/utils/jwt_verification.py` | JWT parsing, structure validation |
| `app/services/truststore_service.py` | Issuer public key management, JWK handling |

### Verification Flow
```
1. app/services/verification_service.py (verify_mandate)
   ├─> 2. _verify_structure() - Basic JWT structure
   ├─> 3. _verify_signature() - Cryptographic signature (RSA/EC)
   ├─> 4. _verify_expiry() - Expiration check
   └─> 5. _verify_scope() - Scope validation
```

### Supporting Files
| File | Purpose |
|------|---------|
| `app/services/mandate_service.py` | Mandate business logic (calls verification) |
| `app/models/mandate.py` | Mandate model with verification_status field |

### Key Functions
- `verification_service.verify_mandate()` - Main entry point (line 59)
- `truststore_service.verify_signature()` - Signature verification (line ~200)
- `truststore_service.get_issuer_keys()` - Get JWK set for issuer

---

## (c) REST ROUTERS / API ENDPOINTS

### Main Router
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application instance |
| `app/api/v1/router.py` | API v1 main router (includes all endpoints) |

### Endpoint Files
| File | Endpoints | Purpose |
|------|-----------|---------|
| `app/api/v1/endpoints/mandates.py` | `/api/v1/mandates` | Mandate CRUD operations |
| `app/api/v1/endpoints/auth.py` | `/api/v1/auth` | Login, logout, token refresh |
| `app/api/v1/endpoints/users.py` | `/api/v1/users` | User management & invitations |
| `app/api/v1/endpoints/customers.py` | `/api/v1/customers` | Tenant/customer management |
| `app/api/v1/endpoints/webhooks.py` | `/api/v1/webhooks` | Webhook subscriptions |
| `app/api/v1/endpoints/audit.py` | `/api/v1/audit` | Audit log queries |
| `app/api/v1/endpoints/alerts.py` | `/api/v1/alerts` | Alert configuration |
| `app/api/v1/endpoints/admin.py` | `/api/v1/admin` | Admin operations |
| `app/api/v1/endpoints/health.py` | `/healthz`, `/readyz` | Health checks |
| `app/api/v1/endpoints/metrics.py` | `/api/v1/metrics` | Prometheus metrics |

### Key Endpoints Detail

**Mandates:**
```
POST   /api/v1/mandates              - Create mandate
GET    /api/v1/mandates/{id}         - Get mandate by ID
POST   /api/v1/mandates/search       - Search mandates
DELETE /api/v1/mandates/{id}         - Revoke mandate
```

**Authentication:**
```
POST   /api/v1/auth/login            - User login
POST   /api/v1/auth/refresh          - Refresh token
POST   /api/v1/auth/logout           - Logout
```

**Users:**
```
POST   /api/v1/users/register        - Register user
POST   /api/v1/users/invite          - Invite user
GET    /api/v1/users                 - List users
PATCH  /api/v1/users/{id}            - Update user
DELETE /api/v1/users/{id}            - Delete user
```

### Pydantic Schemas (Request/Response)
| File | Purpose |
|------|---------|
| `app/schemas/mandate.py` | Mandate request/response schemas |
| `app/schemas/user.py` | User request/response schemas |
| `app/schemas/customer.py` | Customer schemas |
| `app/schemas/webhook.py` | Webhook schemas |
| `app/schemas/audit.py` | Audit log schemas |
| `app/schemas/alert.py` | Alert schemas |

---

## (d) EVIDENCE PACK EXPORTER

### Status: ❌ NOT IMPLEMENTED

**Note:** There is currently NO evidence pack exporter in the codebase.

**If you need this feature, it would typically be:**
- A new endpoint: `GET /api/v1/mandates/{id}/evidence-pack`
- A new service: `app/services/evidence_pack_service.py`
- Export formats: PDF, JSON, ZIP

**Would you like me to implement this feature?**

---

## (e) NEXT.JS DASHBOARD PAGES

### Status: ❌ NOT IMPLEMENTED

**Note:** There is NO Next.js frontend dashboard in this repository.

**Current State:**
- This is a **backend API only**
- Documentation available at `/docs` (Swagger UI)
- Customers interact via:
  - Direct API calls (cURL, Postman)
  - Python SDK (`sdks/python/`)
  - Node.js SDK (`sdks/nodejs/`)

**If you want a dashboard, you would need to:**
1. Create a separate Next.js project
2. Connect to this API
3. Build UI for mandate management

**Would you like me to create a Next.js dashboard?**

---

## 📋 ADDITIONAL KEY FILES

### Services (Business Logic)
| File | Purpose |
|------|---------|
| `app/services/mandate_service.py` | Mandate business logic |
| `app/services/user_service.py` | User management logic |
| `app/services/webhook_service.py` | Webhook delivery |
| `app/services/audit_service.py` | Audit logging |
| `app/services/alert_service.py` | Alert management |
| `app/services/customer_service.py` | Customer/tenant management |
| `app/services/api_key_service.py` | API key management |

### Core Infrastructure
| File | Purpose |
|------|---------|
| `app/core/auth.py` | Authentication (JWT, password hashing) |
| `app/core/config.py` | Application settings |
| `app/core/monitoring.py` | Prometheus metrics, Sentry |
| `app/core/rate_limiting.py` | Rate limiting |
| `app/core/security_middleware.py` | Security headers |
| `app/core/monitoring_middleware.py` | Request monitoring |

### Background Workers
| File | Purpose |
|------|---------|
| `app/workers/webhook_worker.py` | Webhook delivery worker |
| `app/core/cleanup_service.py` | Session cleanup service |

---

## 🗂️ FILE ORGANIZATION SUMMARY

```
Total Files:
├── Models (7):          User, Mandate, Customer, APIKey, Webhook, Alert, Audit
├── Services (10):       Business logic layer
├── Endpoints (10):      REST API handlers
├── Schemas (6):         Request/response validation
├── Core (8):            Auth, config, database, monitoring
├── Workers (2):         Background tasks
├── Utilities (1):       JWT verification helpers
└── Tests (45+):         Comprehensive test suite

Missing Components:
├── Evidence Pack Exporter:  ❌ NOT IMPLEMENTED
└── Next.js Dashboard:       ❌ NOT IMPLEMENTED
```

---

## 🎯 IMPLEMENTATION STATUS

### ✅ Fully Implemented
- Database models (all 7 tables)
- JWT-VC verification (RSA/EC signatures)
- REST API (40+ endpoints)
- Authentication & authorization
- Webhook system
- Monitoring & logging

### ❌ Not Implemented
- Evidence pack exporter
- Frontend dashboard (Next.js)
- Client portal UI

---

## 💡 RECOMMENDATIONS

### For Your Next Steps:

**If you need evidence export:**
- I can implement in ~30 minutes
- Formats: JSON, PDF, ZIP
- Include: Mandate + verification details + audit logs

**If you need a dashboard:**
- Separate Next.js project (4-6 hours)
- Features: View mandates, manage users, configure webhooks
- Authentication via this API

**If you want to launch now:**
- **You don't need either!**
- Deploy API as-is
- Customers use SDKs or direct API calls
- Add dashboard later based on demand

---

## 📞 **What Would You Like?**

1. **Implement Evidence Pack Exporter** (30 min)
2. **Create Next.js Dashboard** (4-6 hours)
3. **Deploy to Production** (proceed with API only)
4. **Something else?**

Let me know and I'll help you implement it!

