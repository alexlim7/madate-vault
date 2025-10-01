# Testing & QA Guide

Comprehensive testing strategy and documentation for Mandate Vault.

---

## 📋 Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [End-to-End Tests](#end-to-end-tests)
5. [Load Testing](#load-testing)
6. [Security Testing](#security-testing)
7. [Performance Benchmarks](#performance-benchmarks)
8. [Running Tests](#running-tests)

---

## 🎯 Testing Strategy

### Test Pyramid

```
         /\
        /E2E\      10% - End-to-End Tests
       /------\
      /Integr-\   20% - Integration Tests
     /----------\
    /   Unit     \  70% - Unit Tests
   /--------------\
```

### Coverage Goals

- **Unit Tests**: 80%+ code coverage
- **Integration Tests**: All critical paths
- **E2E Tests**: Key user journeys
- **Load Tests**: Performance under expected load
- **Security Tests**: OWASP Top 10 coverage

---

## 🧪 Unit Tests

### Overview

Unit tests validate individual components in isolation using mocks.

**Location:** `tests/test_*.py`  
**Framework:** pytest + pytest-asyncio  
**Count:** 624 tests

### Key Test Suites

| Suite | File | Tests | Coverage |
|-------|------|-------|----------|
| User Management | `test_user_management.py` | 27 | User CRUD, auth |
| JWT Verification | `test_jwt_verification.py` | 19 | Signature validation |
| Webhook Delivery | `test_webhook_delivery.py` | 16 | Webhook system |
| Authentication | `test_auth_comprehensive.py` | 24 | Login, tokens |
| Password Policy | `test_quick_win_password_policy.py` | 25 | Password rules |

### Running Unit Tests

```bash
# All unit tests
pytest tests/ --ignore=tests/integration --ignore=tests/e2e -v

# With coverage
pytest tests/ --ignore=tests/integration --cov=app --cov-report=html

# Specific suite
pytest tests/test_user_management.py -v

# Fast mode (parallel)
pytest tests/ -n auto
```

### Writing Unit Tests

```python
import pytest

@pytest.mark.asyncio
async def test_create_user(db_session, test_customer):
    """Test user creation."""
    user_service = UserService(db_session)
    
    user = await user_service.create_user(
        email="test@example.com",
        password="SecurePass123!",
        tenant_id=test_customer.tenant_id
    )
    
    assert user.id is not None
    assert user.email == "test@example.com"
```

---

## 🔗 Integration Tests

### Overview

Integration tests validate interactions between components using real database.

**Location:** `tests/integration/`  
**Database:** Real PostgreSQL (or SQLite for local)  
**Fixtures:** Shared in `conftest.py`

### Test Scenarios

**Complete Mandate Flow:**
1. Register issuer in truststore
2. Create signed JWT-VC
3. Submit mandate via API
4. Verify mandate created
5. Search for mandate
6. Revoke mandate
7. Verify revoked status

**User Flow:**
1. Register user
2. Login to get token
3. Create mandate with auth
4. Access audit logs
5. Receive webhook notification

### Running Integration Tests

```bash
# All integration tests
pytest tests/integration/ -v

# With real PostgreSQL
DATABASE_URL="postgresql+asyncpg://user:pass@localhost/test_db" \
  pytest tests/integration/ -v

# Specific scenario
pytest tests/integration/test_mandate_flow_integration.py -v
```

### Configuration

```python
# tests/integration/conftest.py
@pytest.fixture
async def test_client(test_engine):
    """HTTP client with real database."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

---

## 🌐 End-to-End Tests

### Overview

E2E tests validate complete user journeys from API to database.

**Location:** `tests/e2e/`  
**Scope:** Full application stack  
**Tools:** pytest + httpx

### Test Scenarios

#### Scenario 1: Customer Onboarding

```python
async def test_complete_customer_onboarding():
    """Test full customer onboarding flow."""
    # 1. Create customer tenant
    # 2. Create admin user
    # 3. Send invitation email
    # 4. Accept invitation
    # 5. Setup webhook
    # 6. Create first mandate
    # 7. Verify webhook received
```

#### Scenario 2: Mandate Lifecycle

```python
async def test_mandate_lifecycle():
    """Test complete mandate lifecycle."""
    # 1. Create mandate
    # 2. Mandate is active
    # 3. Query mandate
    # 4. Update mandate
    # 5. Mandate expires
    # 6. Alert generated
    # 7. Revoke mandate
    # 8. Audit log created
```

### Running E2E Tests

```bash
# All E2E tests
pytest tests/e2e/ -v --tb=short

# Specific journey
pytest tests/e2e/test_customer_journey.py::test_complete_onboarding -v
```

---

## 📊 Load Testing

### Overview

Load tests validate system performance under expected load.

**Tool:** k6 (https://k6.io)  
**Location:** `tests/load/`  
**Scenarios:** Smoke, Load, Stress, Spike

### Test Scenarios

#### Smoke Test
```
1 VU for 30 seconds
Validates basic functionality
```

#### Load Test
```
Ramp 0 → 100 VUs over 10 minutes
Maintain 100 VUs for 5 minutes
Tests normal production load
```

#### Stress Test
```
Ramp 0 → 300 VUs
Push system to breaking point
Identify capacity limits
```

#### Spike Test
```
Sudden jump 10 → 500 VUs
Test auto-scaling & recovery
```

### Running Load Tests

```bash
# Install k6
brew install k6  # macOS
# or download from https://k6.io/docs/getting-started/installation

# Run smoke test
k6 run tests/load/mandate_creation_load_test.js

# Run with custom target
k6 run --vus 50 --duration 2m tests/load/mandate_creation_load_test.js

# Output to Cloud
k6 run --out cloud tests/load/mandate_creation_load_test.js
```

### Performance Targets

| Metric | Target |
|--------|--------|
| Response Time (P95) | < 2s |
| Response Time (P99) | < 5s |
| Error Rate | < 1% |
| Throughput | 100 req/s |
| Concurrent Users | 100 VUs |

### Sample k6 Script

```javascript
export const options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '5m', target: 10 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],
    'errors': ['rate<0.01'],
  },
};
```

---

## 🔐 Security Testing

### Overview

Security tests validate protection against common vulnerabilities (OWASP Top 10).

**Location:** `tests/security/`  
**Coverage:** SQL Injection, XSS, Auth, CSRF, etc.

### Test Categories

#### 1. Injection Attacks

```python
@pytest.mark.asyncio
async def test_sql_injection_protection():
    """Test SQL injection protection."""
    payloads = ["'; DROP TABLE users; --", "1' OR '1'='1"]
    # Verify payloads are safely handled
```

#### 2. Authentication & Authorization

```python
@pytest.mark.asyncio
async def test_authentication_required():
    """Test protected endpoints require auth."""
    response = await client.get("/api/v1/mandates")
    assert response.status_code == 401
```

#### 3. Brute Force Protection

```python
@pytest.mark.asyncio
async def test_account_lockout():
    """Test account locks after failed attempts."""
    # Make 6 failed login attempts
    # Verify account is locked
```

#### 4. Security Headers

```python
@pytest.mark.asyncio
async def test_secure_headers():
    """Test security headers are set."""
    assert "X-Content-Type-Options" in response.headers
    assert "Content-Security-Policy" in response.headers
```

### Running Security Tests

```bash
# All security tests
pytest tests/security/ -v

# Specific category
pytest tests/security/test_security_vulnerabilities.py::test_sql_injection_protection -v

# Generate security report
pytest tests/security/ --html=security_report.html
```

### Security Checklist

- [ ] SQL Injection protection
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Authentication required
- [ ] Authorization enforced
- [ ] Rate limiting active
- [ ] Brute force protection
- [ ] Secure headers set
- [ ] JWT validation
- [ ] Sensitive data not exposed
- [ ] Password requirements
- [ ] Path traversal protection

---

## ⚡ Performance Benchmarks

### Overview

Performance tests ensure system meets SLAs.

**Location:** `tests/performance/`  
**Tool:** pytest-benchmark  

### Benchmark Suites

#### API Response Times

```python
@pytest.mark.benchmark
async def test_mandate_creation_performance(benchmark):
    """Benchmark mandate creation."""
    result = benchmark(create_mandate)
    assert benchmark.stats.mean < 0.5  # < 500ms
```

#### Database Queries

```python
@pytest.mark.benchmark
async def test_database_query_performance():
    """Benchmark database query time."""
    start = time.time()
    result = await db.execute(query)
    assert (time.time() - start) < 0.1  # < 100ms
```

#### Concurrent Performance

```python
@pytest.mark.benchmark
async def test_concurrent_requests():
    """Test performance under concurrent load."""
    tasks = [make_request() for _ in range(50)]
    responses = await asyncio.gather(*tasks)
    # All should complete in < 5s
```

### Running Benchmarks

```bash
# All benchmarks
pytest tests/performance/ -v

# With comparison
pytest tests/performance/ --benchmark-compare

# Save baseline
pytest tests/performance/ --benchmark-save=baseline

# Compare to baseline
pytest tests/performance/ --benchmark-compare=baseline
```

### Performance Targets

| Operation | Target |
|-----------|--------|
| Mandate Creation | < 500ms |
| Search Query | < 100ms |
| Login | < 500ms |
| JWT Verification | < 200ms |
| Database Query | < 100ms |

---

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific category
pytest tests/integration/ -v

# Run with markers
pytest -m "not slow" -v

# Parallel execution
pytest -n auto
```

### Test Configuration

**pytest.ini:**
```ini
[pytest]
asyncio_mode = auto
markers =
    slow: marks tests as slow
    integration: integration tests
    e2e: end-to-end tests
    security: security tests
    benchmark: performance benchmarks
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Environment Setup

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Set test environment
export SECRET_KEY="test-secret-key-minimum-32-characters"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export ENVIRONMENT="testing"

# Run tests
pytest
```

### CI/CD Integration

**GitHub Actions:**
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📊 Test Coverage

### Current Coverage

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
app/core/auth.py                145     12    92%
app/services/user_service.py    203     18    91%
app/services/mandate_service.py 267     24    91%
app/api/v1/endpoints/users.py   156     14    91%
app/core/monitoring.py          112     23    79%
-------------------------------------------------
TOTAL                          2847    285    90%
```

### Coverage Reports

```bash
# Generate HTML report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Generate XML for CI
pytest --cov=app --cov-report=xml

# Terminal report
pytest --cov=app --cov-report=term-missing
```

---

## 🐛 Debugging Tests

### Debug Failed Test

```bash
# Verbose output
pytest tests/test_user.py::test_create_user -vv

# Drop into debugger on failure
pytest tests/test_user.py --pdb

# Show print statements
pytest tests/test_user.py -s

# Last failed tests only
pytest --lf
```

### Common Issues

**1. Database Locked**
```bash
# Clear test database
rm test.db test_integration.db
pytest
```

**2. Async Issues**
```python
# Ensure proper async fixtures
@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
```

**3. Import Errors**
```bash
# Install in development mode
pip install -e .
```

---

## 📚 Best Practices

### 1. Test Naming
```python
# Good: Descriptive, clear intent
def test_user_creation_requires_valid_email()

# Bad: Vague
def test_user()
```

### 2. Test Independence
```python
# Each test should be independent
# Use fixtures for setup, not shared state
```

### 3. Arrange-Act-Assert
```python
def test_example():
    # Arrange
    user = create_test_user()
    
    # Act
    result = user_service.login(user)
    
    # Assert
    assert result.success is True
```

### 4. Use Fixtures
```python
@pytest.fixture
async def test_user(db_session):
    """Reusable test user fixture."""
    return await create_user(db_session)
```

### 5. Meaningful Assertions
```python
# Good
assert user.email == "test@example.com"
assert user.is_active is True

# Bad
assert user
```

---

## 🎯 Test Checklist

Before Release:

- [ ] All unit tests passing (624+)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Load tests meet SLA
- [ ] Security tests passing
- [ ] Code coverage > 80%
- [ ] No critical linter errors
- [ ] Performance benchmarks met
- [ ] Documentation updated

---

**Last Updated:** October 2025  
**Test Count:** 624+ unit, 20+ integration, 15+ security  
**Coverage:** 90%+

