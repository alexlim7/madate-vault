"""
Security Vulnerability Tests
============================

Tests for common security vulnerabilities (OWASP Top 10).
"""
import pytest


@pytest.mark.asyncio
async def test_sql_injection_protection(test_client, auth_headers):
    """Test SQL injection protection."""
    
    # Attempt SQL injection in search
    malicious_payloads = [
        "'; DROP TABLE mandates; --",
        "1' OR '1'='1",
        "admin'--",
        "' OR 1=1--",
        "' UNION SELECT * FROM users--"
    ]
    
    for payload in malicious_payloads:
        response = await test_client.post(
            "/api/v1/mandates/search",
            json={
                "tenant_id": payload,
                "issuer_did": payload
            },
            headers=auth_headers
        )
        
        # Should either return empty results or validation error, not 500
        assert response.status_code in [200, 400, 422]
        
        # Should not contain error with SQL syntax
        if response.status_code != 200:
            assert "syntax" not in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_xss_protection(test_client, auth_headers, test_customer):
    """Test Cross-Site Scripting (XSS) protection."""
    
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
    ]
    
    for payload in xss_payloads:
        response = await test_client.post(
            "/api/v1/customers",
            json={
                "name": payload,
                "email": f"test-{payload}@example.com"
            },
            headers=auth_headers
        )
        
        # Should either create or reject, not execute
        assert response.status_code in [201, 400, 422]
        
        # If created, check that payload is escaped
        if response.status_code == 201:
            data = response.json()
            assert "<script>" not in str(data)


@pytest.mark.asyncio
async def test_authentication_required(test_client):
    """Test that endpoints require authentication."""
    
    protected_endpoints = [
        ("GET", "/api/v1/mandates/search"),
        ("POST", "/api/v1/mandates"),
        ("GET", "/api/v1/audit"),
        ("GET", "/api/v1/customers"),
        ("POST", "/api/v1/users"),
    ]
    
    for method, endpoint in protected_endpoints:
        if method == "GET":
            response = await test_client.get(endpoint)
        else:
            response = await test_client.post(endpoint, json={})
        
        # Should return 401 Unauthorized
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_authorization_enforcement(test_client, user_auth_headers):
    """Test that non-admin users cannot access admin endpoints."""
    
    # Regular user should not access admin endpoints
    response = await test_client.get(
        "/api/v1/admin/stats",
        headers=user_auth_headers
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rate_limiting(test_client):
    """Test rate limiting protection."""
    
    # Make many rapid requests
    responses = []
    for i in range(150):  # Exceed rate limit
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password"
            }
        )
        responses.append(response.status_code)
    
    # Should see 429 Too Many Requests
    assert 429 in responses


@pytest.mark.asyncio
async def test_brute_force_protection(test_client, test_regular_user):
    """Test account lockout after failed login attempts."""
    
    # Attempt multiple failed logins
    for i in range(6):  # Exceeds lockout threshold
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_regular_user.email,
                "password": "wrongpassword"
            }
        )
    
    # Final attempt should indicate account is locked
    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_regular_user.email,
            "password": "UserPassword123!"  # Correct password
        }
    )
    
    assert response.status_code == 403
    assert "locked" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_jwt_token_expiration(test_client, test_admin_user):
    """Test that expired JWT tokens are rejected."""
    import time
    import jwt as pyjwt
    from app.core.config import settings
    
    # Create expired token
    payload = {
        "sub": test_admin_user.email,
        "exp": int(time.time()) - 3600  # Expired 1 hour ago
    }
    
    expired_token = pyjwt.encode(payload, settings.secret_key, algorithm="HS256")
    
    response = await test_client.get(
        "/api/v1/mandates/search",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_token_tampering(test_client, auth_headers):
    """Test that tampered JWT tokens are rejected."""
    
    # Get valid token and tamper with it
    token = auth_headers["Authorization"].replace("Bearer ", "")
    tampered_token = token[:-5] + "XXXXX"  # Change last 5 chars
    
    response = await test_client.get(
        "/api/v1/mandates/search",
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_csrf_token_protection(test_client):
    """Test CSRF protection for state-changing operations."""
    
    # State-changing operations should require proper headers
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@test.com", "password": "pass"},
        headers={
            "Origin": "http://malicious-site.com",
            "Referer": "http://malicious-site.com"
        }
    )
    
    # Should be rejected due to CORS/origin mismatch
    # Or succeed but with proper CORS headers
    if response.status_code == 200:
        assert "Access-Control-Allow-Origin" in response.headers


@pytest.mark.asyncio
async def test_sensitive_data_exposure(test_client, auth_headers):
    """Test that sensitive data is not exposed in responses."""
    
    response = await test_client.get(
        "/api/v1/users/",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    users = response.json()
    
    # Password fields should never be in response
    for user in users:
        assert "password" not in user
        assert "password_hash" not in user


@pytest.mark.asyncio
async def test_secure_headers(test_client):
    """Test that secure HTTP headers are set."""
    
    response = await test_client.get("/healthz")
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    
    assert "Content-Security-Policy" in response.headers
    
    assert "Strict-Transport-Security" in response.headers


@pytest.mark.asyncio
async def test_file_upload_validation(test_client, auth_headers):
    """Test file upload size and type validation."""
    
    # Test with oversized payload
    large_payload = "A" * (11 * 1024 * 1024)  # 11MB (exceeds 10MB limit)
    
    response = await test_client.post(
        "/api/v1/mandates",
        json={
            "vc_jwt": large_payload,
            "tenant_id": "test"
        },
        headers=auth_headers
    )
    
    # Should reject large payloads
    assert response.status_code in [400, 413, 422]


@pytest.mark.asyncio
async def test_path_traversal_protection(test_client, auth_headers):
    """Test protection against path traversal attacks."""
    
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "%2e%2e%2f%2e%2e%2f",
    ]
    
    for path in malicious_paths:
        response = await test_client.get(
            f"/api/v1/mandates/{path}",
            headers=auth_headers
        )
        
        # Should return 404 or 400, not 500 or file contents
        assert response.status_code in [400, 404, 422]


@pytest.mark.asyncio
async def test_information_disclosure(test_client):
    """Test that error messages don't disclose sensitive information."""
    
    # Invalid endpoint
    response = await test_client.get("/api/v1/nonexistent")
    
    assert response.status_code == 404
    error = response.json()
    
    # Should not reveal internal paths, stack traces, or database info
    error_str = str(error).lower()
    assert "/users/" not in error_str  # No file paths
    assert "traceback" not in error_str
    assert "sql" not in error_str
    assert "database" not in error_str


@pytest.mark.asyncio
async def test_password_requirements(test_client, test_customer):
    """Test password strength requirements."""
    
    weak_passwords = [
        "12345678",
        "password",
        "qwerty",
        "abc123",
        "short",
    ]
    
    for weak_pass in weak_passwords:
        response = await test_client.post(
            "/api/v1/users/register",
            json={
                "email": f"test-{weak_pass}@example.com",
                "password": weak_pass,
                "full_name": "Test User",
                "tenant_id": test_customer.tenant_id
            }
        )
        
        # Should reject weak passwords
        assert response.status_code in [400, 422]

