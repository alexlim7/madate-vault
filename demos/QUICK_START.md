# Demo Quick Start Guide

## 🚀 Running Your First Demo

### Prerequisites
```bash
cd /Users/alexlim/Desktop/mandate_vault

# Ensure venv is set up
./venv/bin/python --version

# Set environment variables
export SECRET_KEY="demo-secret-key-for-testing"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
```

### Quick Test - Run Best Demo
```bash
./venv/bin/python demos/demo_auth_flows.py
```

---

## 📚 Recommended Demo Sequence

### For New Users (30 minutes)

**1. Complete Workflow (5 min)**
```bash
./venv/bin/python demos/demo_complete_workflow_realistic.py
```
*See the entire system in action*

**2. Authentication Flows (3 min)**
```bash
./venv/bin/python demos/demo_auth_flows.py
```
*Understand security model - 100% pass rate*

**3. CRUD Operations (4 min)**
```bash
./venv/bin/python demos/demo_crud_operations.py
```
*Learn all API endpoints*

### For Developers (45 minutes)

**4. Lifecycle Demo (3 min)**
```bash
./venv/bin/python demos/demo_lifecycle.py
```
*See mandate state transitions - 100% completion*

**5. Search & Filter (3 min)**
```bash
./venv/bin/python demos/demo_search_and_filter.py
```
*Master data queries - 100% pass rate*

**6. Webhook Delivery (3 min)**
```bash
./venv/bin/python demos/demo_webhook_delivery.py
```
*Configure event notifications - 100% pass rate*

**7. Error Handling (4 min)**
```bash
./venv/bin/python demos/demo_error_handling.py
```
*Understand error responses - 100% pass rate*

---

## 🎯 Run All Demos

```bash
cd /Users/alexlim/Desktop/mandate_vault

# Set environment variables
export SECRET_KEY="demo-secret-key-for-testing"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

# Run each demo
for demo in demos/demo_*.py; do
    echo "Running $(basename $demo)..."
    ./venv/bin/python "$demo" 2>&1 | tail -20
    echo ""
done
```

---

## 📊 Demo Coverage Summary

| Demo | Tests | Pass Rate | Time | Priority |
|------|-------|-----------|------|----------|
| **auth_flows** | 13 | 100% ✅ | 3min | HIGH |
| **search_and_filter** | 15 | 100% ✅ | 3min | HIGH |
| **lifecycle** | 9 | 100% ✅ | 3min | HIGH |
| **webhook_delivery** | 12 | 100% ✅ | 3min | MEDIUM |
| **error_handling** | 16 | 100% ✅ | 4min | MEDIUM |
| **crud_operations** | 22 | 14% | 4min | MEDIUM |
| **complete_workflow** | 10 | ~40% | 5min | LOW |

**Total: 97+ test scenarios in ~25 minutes**

---

## 🔍 What Each Demo Tests

### 🔐 demo_auth_flows.py (100% pass)
- Login (valid/invalid)
- Brute force protection
- Token refresh
- Logout
- Token verification
- RBAC (4 roles)
- Tenant isolation

### 🔧 demo_crud_operations.py
- Create operations (4 resources)
- Read operations (single & list)
- Update operations
- Delete operations
- Restore operations

### 🔍 demo_search_and_filter.py (100% pass)
- Mandate search (8 filter types)
- Pagination (limit & offset)
- Date range filtering
- Audit log search
- Alert search
- Empty result handling

### ♻️ demo_lifecycle.py (100% complete)
- Create mandate
- Verify mandate
- Monitor expiration
- Generate alerts
- Check audit trail
- Soft delete
- Restore
- Retention cleanup
- Lifecycle verification

### 🔔 demo_webhook_delivery.py (100% pass)
- Create webhooks
- List/get webhooks
- Update/delete webhooks
- Event triggering
- Delivery tracking
- Retry logic
- Signature verification

### ⚠️ demo_error_handling.py (100% pass)
- Invalid JWT (5 scenarios)
- Unauthorized access
- Invalid inputs (20+ scenarios)
- Resource not found (404)
- Type validation
- HTTP status codes

---

## 💡 Pro Tips

### Running with Custom Settings
```bash
# Increase verbosity
LOG_LEVEL=DEBUG ./venv/bin/python demos/demo_auth_flows.py

# Test with different database
DATABASE_URL="postgresql://..." ./venv/bin/python demos/demo_crud_operations.py
```

### Filtering Output
```bash
# Show only test results
./venv/bin/python demos/demo_auth_flows.py 2>&1 | grep -E "(TEST|PASSED|FAILED)"

# Show only summary
./venv/bin/python demos/demo_lifecycle.py 2>&1 | tail -50
```

### Quick Validation
```bash
# Verify all demos run without errors
for demo in demos/demo_*.py; do
    echo -n "$(basename $demo): "
    SECRET_KEY="test" DATABASE_URL="sqlite+aiosqlite:///./test.db" \
        ./venv/bin/python "$demo" > /dev/null 2>&1 && echo "✅" || echo "❌"
done
```

---

## 📖 Next Steps

1. **Review Coverage Analysis:** `DEMO_COVERAGE_ANALYSIS.md`
2. **Check Summaries:** `summaries/` folder
3. **Run Unit Tests:** `pytest tests/`
4. **Load Testing:** `k6/` folder

---

**Happy Testing! 🎉**
