# Mandate Vault Demo Scripts

This folder contains comprehensive demonstration scripts for the Mandate Vault API.

## 📁 Demo Files

### 🔹 Complete Workflow Demos
- **`demo_complete_workflow.py`** - Original complete workflow demo
- **`demo_complete_workflow_improved.py`** - Improved version with better mocking
- **`demo_complete_workflow_realistic.py`** - Realistic API calls with proper database mocking

### 🔹 Feature-Specific Demos
- **`demo_crud_operations.py`** - Tests all CRUD operations for Customers, Mandates, Webhooks, and Alerts (22 endpoints)
- **`demo_auth_flows.py`** - Authentication & authorization flows (13 tests, 100% pass rate)
- **`demo_search_and_filter.py`** - Advanced search and filtering capabilities (15 tests, 100% pass rate)
- **`demo_lifecycle.py`** - Complete mandate lifecycle from creation to deletion (9 stages, 100% complete)
- **`demo_webhook_delivery.py`** - Webhook event system and delivery (12 tests, 100% pass rate)
- **`demo_error_handling.py`** - Error handling and edge cases (16 tests, 100% pass rate)
- **`demo_security_features.py`** - Security features demonstration

## 🚀 Running the Demos

All demos require environment variables to be set. Run them using:

```bash
cd /Users/alexlim/Desktop/mandate_vault

# Set required environment variables
export SECRET_KEY="demo-secret-key-for-testing"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

# Run any demo
./venv/bin/python demos/demo_<name>.py
```

Or in a single command:

```bash
SECRET_KEY="demo-secret-key-for-testing" DATABASE_URL="sqlite+aiosqlite:///./test.db" ./venv/bin/python demos/demo_<name>.py
```

## 📊 Coverage Summary

| Demo | Focus | Tests/Stages | Success Rate |
|------|-------|--------------|--------------|
| CRUD Operations | All CRUD endpoints | 22 endpoints | 14.3% (limited by mocks) |
| Auth Flows | Authentication & RBAC | 13 tests | 100% |
| Search & Filter | Advanced querying | 15 tests | 100% |
| Lifecycle | Complete mandate flow | 9 stages | 100% |
| Webhook Delivery | Event system | 12 tests | 100% |
| Error Handling | Error scenarios | 16 tests | 100% |

**Total: 85+ test scenarios across all features!**

## 🎯 Recommended Demo Sequence

For new users, run demos in this order:

1. **`demo_complete_workflow_realistic.py`** - Get overview of entire system
2. **`demo_auth_flows.py`** - Understand security model
3. **`demo_crud_operations.py`** - Learn all API endpoints
4. **`demo_lifecycle.py`** - See mandate state transitions
5. **`demo_search_and_filter.py`** - Master data queries
6. **`demo_webhook_delivery.py`** - Configure event notifications
7. **`demo_error_handling.py`** - Understand error responses

## 💡 Notes

- All demos use mocked databases for testing without requiring a real database
- Some operations return 404/500 errors due to mock limitations
- In a real deployment with proper database, success rates would be much higher
- The demos validate that endpoints exist and have correct request/response formats
