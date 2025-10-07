# CI/CD Pipeline

Automated testing, security scanning, and deployment for Mandate Vault.

## Overview

The CI/CD pipeline runs on every push and pull request, ensuring code quality, security, and performance.

## Pipeline Stages

### 1. **Unit & Integration Tests** 
- Runs all unit tests (700+ tests)
- Runs integration tests
- Generates code coverage report
- Uploads to Codecov

**Pass Criteria:**
- All tests must pass
- Coverage > 90% (recommended)

### 2. **Performance & Smoke Tests**
- Runs k6 load test with mixed AP2/ACP traffic
- Runs Python smoke test (end-to-end)
- Validates performance thresholds

**Pass Criteria:**
- **p95 latency for POST /authorizations < 200ms** ⚠️ **CRITICAL**
- Error rate < 1%
- All smoke tests pass (9/9)

### 3. **Security Scanning**
- **Snyk**: Python dependency vulnerability scanning
- **Trivy**: Filesystem and Docker image scanning
- Uploads results to GitHub Security tab

**Pass Criteria:**
- **No critical CVEs** ⚠️ **CRITICAL** - Pipeline fails if critical vulnerabilities found
- High severity CVEs are reported but don't fail build (for now)

### 4. **Code Quality**
- Black (code formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking - non-blocking)

**Pass Criteria:**
- Code must be formatted with `black`
- Imports must be sorted with `isort`
- No critical flake8 errors (F-series)

### 5. **Build & Publish** (main/develop only)
- Builds Docker image
- Pushes to Docker Hub
- Tags with branch name, SHA, and semver

### 6. **Deploy** (develop only)
- Deploys to staging environment
- Updates Cloud Run service

---

## Required Secrets

Configure these in GitHub Settings → Secrets and variables → Actions:

| Secret | Required | Description |
|--------|----------|-------------|
| `SNYK_TOKEN` | Yes | Snyk API token for vulnerability scanning |
| `DOCKER_USERNAME` | Yes (for deploy) | Docker Hub username |
| `DOCKER_PASSWORD` | Yes (for deploy) | Docker Hub password or token |
| `GCP_SERVICE_ACCOUNT_KEY` | Optional | For Cloud Run deployment |

---

## Running Locally

### Unit Tests
```bash
python -m pytest tests/ \
  --ignore=tests/integration \
  --ignore=tests/e2e \
  --ignore=tests/security \
  --ignore=tests/performance \
  --ignore=tests/load \
  -v --cov=app
```

### Integration Tests
```bash
python -m pytest tests/integration/ -v
```

### Performance Smoke Test
```bash
# 1. Start server
SECRET_KEY="test-key" DATABASE_URL="sqlite+aiosqlite:///./test.db" \
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 2. Create smoke test user
python scripts/create_smoke_test_user.py

# 3. Run k6 test
k6 run tests/load/smoke_multiprotocol.js

# 4. Run Python smoke test
export API_BASE_URL="http://localhost:8000"
export TEST_EMAIL="smoketest@example.com"
export TEST_PASSWORD="SmokeTest2025Pass"
export ACP_WEBHOOK_SECRET="test-acp-webhook-secret-key"
python3 ./scripts/smoke_authorizations.py
```

### Security Scanning

**Snyk:**
```bash
# Install Snyk CLI
npm install -g snyk

# Authenticate
snyk auth

# Test for vulnerabilities
snyk test --severity-threshold=critical
```

**Trivy:**
```bash
# Install Trivy
brew install aquasecurity/trivy/trivy  # macOS
# or
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy  # Linux

# Scan filesystem
trivy fs . --severity CRITICAL,HIGH

# Scan Docker image
docker build -t mandate-vault:latest .
trivy image mandate-vault:latest --severity CRITICAL
```

---

## Performance Thresholds

| Metric | Threshold | Impact |
|--------|-----------|--------|
| **POST /authorizations p95** | < 200ms | ❌ **Pipeline fails** |
| Error rate | < 1% | ❌ Pipeline fails |
| Check success rate | > 99% | ❌ Pipeline fails |

### Why 200ms?

- User experience: Sub-200ms feels instant
- API SLA: Allows for network latency and still meet 250ms SLA
- Scalability: Ensures efficient resource usage

If p95 exceeds 200ms:
1. Check database query performance
2. Review JWT verification caching
3. Optimize Pydantic validation
4. Check external service calls

---

## Security Scanning Details

### Snyk
- Scans `requirements.txt` dependencies
- Checks for known CVEs in Python packages
- Provides fix recommendations
- **Fails on:** Critical vulnerabilities

### Trivy
- Scans filesystem for vulnerabilities
- Scans Docker base image (python:3.9-slim)
- Checks for misconfigurations
- **Fails on:** Critical CVEs in dependencies or base image

### What Fails the Build

**Critical (Pipeline Fails):**
- CVE-2024-XXXXX with CVSS >= 9.0
- Known RCE vulnerabilities
- SQL injection vectors in dependencies
- Authentication bypass vulnerabilities

**High (Reported, Doesn't Fail):**
- CVE with CVSS 7.0-8.9
- XSS vulnerabilities
- CSRF vectors

---

## Fixing Failures

### Test Failures
```bash
# Run specific test
pytest tests/test_name.py::TestClass::test_method -v

# Run with debugging
pytest tests/test_name.py -vv --pdb

# Check coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Performance Failures
```bash
# Profile authorization endpoint
python -m cProfile -s cumtime app/api/v1/endpoints/authorizations.py

# Check database query performance
# Enable SQL query logging in app/core/database.py

# Run k6 with detailed output
k6 run tests/load/smoke_multiprotocol.js --out json=results.json

# Analyze results
jq '.metrics' results.json
```

### Security Failures
```bash
# Update dependencies
pip install --upgrade package-name

# Check for updates
pip list --outdated

# Update all (carefully)
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt

# Re-run security scan
snyk test
trivy fs .
```

---

## CI/CD Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Push/PR Trigger                                             │
└────────────┬────────────────────────────────────────────────┘
             │
      ┌──────┴──────┬────────────┬──────────────┐
      │             │            │              │
      v             v            v              v
┌──────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐
│  Test    │  │  Perf   │  │ Security │  │   Lint      │
│  700+    │  │  k6 +   │  │ Snyk +   │  │  black +    │
│  tests   │  │  Smoke  │  │ Trivy    │  │  flake8     │
└─────┬────┘  └────┬────┘  └────┬─────┘  └──────┬──────┘
      │            │            │               │
      └────────────┴────────────┴───────────────┘
                   │
              All Pass? ──No──> ❌ Fail Pipeline
                   │
                  Yes
                   │
                   v
           ┌───────────────┐
           │  Build Docker │
           │  & Push       │
           └───────┬───────┘
                   │
           main/develop?
                   │
                  Yes
                   │
                   v
           ┌───────────────┐
           │  Deploy       │
           │  Staging      │
           └───────────────┘
```

---

## Troubleshooting

### "No authentication token available"
**Problem:** Login failed in k6 test

**Solution:**
```bash
# Ensure smoke test user exists
python scripts/create_smoke_test_user.py

# Verify credentials
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoketest@example.com","password":"SmokeTest2025Pass"}'
```

### "p95 latency exceeds 200ms"
**Problem:** Authorization creation is too slow

**Solutions:**
1. Add database indexes
2. Cache JWT public keys
3. Optimize Pydantic validation
4. Use connection pooling

### "Critical CVE found"
**Problem:** Snyk or Trivy found critical vulnerability

**Solutions:**
1. Update affected package: `pip install --upgrade package-name`
2. Check for security patch
3. If no fix available, add to exception list (with justification)
4. Consider alternative package

---

## Branch Protection

Recommended GitHub branch protection rules for `main`:

- ✅ Require pull request before merging
- ✅ Require approvals: 1
- ✅ Require status checks to pass:
  - `test` (Unit & Integration Tests)
  - `performance` (Performance & Smoke Tests)
  - `security` (Security Scans)
  - `lint` (Code Quality)
- ✅ Require branches to be up to date
- ✅ Do not allow bypassing the above settings

---

## Monitoring CI/CD

### GitHub Actions
- View runs: https://github.com/[org]/mandate-vault/actions
- Check logs for failures
- Download artifacts (test results, k6 results, security scans)

### Codecov
- View coverage reports
- Track coverage trends
- See uncovered lines

### Security Tab
- View Trivy scan results
- See dependency vulnerabilities
- Track security alerts

---

## Next Steps

1. **Configure Secrets**: Add SNYK_TOKEN, DOCKER credentials
2. **Set Branch Protection**: Require CI checks on main
3. **Monitor First Run**: Check for environment-specific issues
4. **Tune Thresholds**: Adjust p95 threshold based on actual performance

---

**Updated:** October 2025  
**Pipeline Version:** 1.0


