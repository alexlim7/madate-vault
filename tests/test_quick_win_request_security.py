"""
Comprehensive tests for request security features.
Tests Quick Win #4 (Secure Cookies) and #5 (Request Size Limits).
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import Response
from app.main import app
from app.core.request_security import RequestSecurityMiddleware, SecureCookieHelper


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestRequestSizeLimits:
    """Test request size limit enforcement."""
    
    def test_request_size_limit_configured(self):
        """Test that request size limit is configured."""
        middleware = RequestSecurityMiddleware(app=None)
        
        assert middleware.MAX_REQUEST_SIZE == 10 * 1024 * 1024  # 10MB
        assert middleware.MAX_URL_LENGTH == 2048
    
    def test_normal_request_size_accepted(self, client):
        """Test that normal-sized requests are accepted."""
        # Small request should work
        data = {"email": "test@example.com", "password": "password123"}
        response = client.post("/api/v1/auth/login", json=data)
        
        # Should not be rejected for size
        assert response.status_code != 413
    
    def test_large_request_rejected(self, client):
        """Test that oversized requests are rejected."""
        # Simulate large request with content-length header
        headers = {"Content-Length": str(15 * 1024 * 1024)}  # 15MB (exceeds 10MB)
        
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        
        # Should be rejected with 413
        assert response.status_code == 413
        assert "Request Entity Too Large" in response.json()["error"]
    
    def test_request_size_limit_error_message(self, client):
        """Test that size limit error message is informative."""
        headers = {"Content-Length": str(15 * 1024 * 1024)}
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        
        assert response.status_code == 413
        data = response.json()
        assert "error" in data
        assert "detail" in data
        assert "exceeds maximum" in data["detail"]
    
    def test_url_length_limit_configured(self):
        """Test that URL length limit is configured."""
        middleware = RequestSecurityMiddleware(app=None)
        assert middleware.MAX_URL_LENGTH == 2048
    
    def test_long_url_rejected(self, client):
        """Test that excessively long URLs are rejected."""
        # Create a very long URL
        long_param = "a" * 3000  # Exceeds 2048 character limit
        response = client.get(f"/api/v1/mandates/search?tenant_id={long_param}")
        
        # Should be rejected with 414
        assert response.status_code == 414
        assert "URI Too Long" in response.json()["error"]
    
    def test_normal_url_length_accepted(self, client):
        """Test that normal URLs are accepted."""
        # Normal URL should work
        response = client.get("/api/v1/mandates/search?tenant_id=test-tenant")
        
        # Should not be rejected for URL length
        assert response.status_code != 414
    
    def test_multiple_size_limit_checks(self, client):
        """Test that size limits are checked for all requests."""
        # Test POST
        headers_post = {"Content-Length": str(15 * 1024 * 1024)}
        response_post = client.post("/api/v1/auth/login", headers=headers_post, json={})
        assert response_post.status_code == 413
        
        # Test PUT
        headers_put = {"Content-Length": str(15 * 1024 * 1024)}
        response_put = client.put("/api/v1/mandates/test-id?tenant_id=test", headers=headers_put, json={})
        assert response_put.status_code == 413


class TestSecureCookieSettings:
    """Test secure cookie settings implementation."""
    
    def test_secure_cookie_helper_exists(self):
        """Test that SecureCookieHelper class exists."""
        assert SecureCookieHelper is not None
    
    def test_secure_cookie_default_settings(self):
        """Test that secure cookie has correct default settings."""
        from fastapi import Response
        
        response = Response()
        
        # Test that the helper sets secure defaults
        SecureCookieHelper.set_secure_cookie(
            response=response,
            key="test_cookie",
            value="test_value"
        )
        
        # Check cookie was set
        assert "set-cookie" in response.headers
        cookie_header = response.headers["set-cookie"]
        
        # Check security attributes
        assert "httponly" in cookie_header.lower()
        assert "samesite=strict" in cookie_header.lower()
    
    def test_secure_cookie_httponly(self):
        """Test that cookies are set with httponly flag."""
        response = Response()
        
        SecureCookieHelper.set_secure_cookie(
            response=response,
            key="session",
            value="abc123",
            httponly=True
        )
        
        cookie_header = response.headers["set-cookie"]
        assert "httponly" in cookie_header.lower()
    
    def test_secure_cookie_samesite_strict(self):
        """Test that cookies use SameSite=Strict."""
        response = Response()
        
        SecureCookieHelper.set_secure_cookie(
            response=response,
            key="session",
            value="abc123",
            samesite="strict"
        )
        
        cookie_header = response.headers["set-cookie"]
        assert "samesite=strict" in cookie_header.lower()
    
    def test_secure_cookie_max_age(self):
        """Test that cookies have appropriate max-age."""
        response = Response()
        
        SecureCookieHelper.set_secure_cookie(
            response=response,
            key="session",
            value="abc123",
            max_age=3600
        )
        
        cookie_header = response.headers["set-cookie"]
        assert "max-age=3600" in cookie_header.lower()
    
    def test_secure_cookie_custom_settings(self):
        """Test that cookies can be customized."""
        response = Response()
        
        SecureCookieHelper.set_secure_cookie(
            response=response,
            key="custom",
            value="value",
            max_age=7200,
            httponly=False,
            samesite="lax"
        )
        
        cookie_header = response.headers["set-cookie"]
        assert "max-age=7200" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()


class TestRequestSecurityMiddleware:
    """Test RequestSecurityMiddleware functionality."""
    
    def test_middleware_rejects_oversized_requests(self, client):
        """Test middleware rejects oversized requests."""
        headers = {"Content-Length": str(20 * 1024 * 1024)}  # 20MB
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        
        assert response.status_code == 413
    
    def test_middleware_rejects_long_urls(self, client):
        """Test middleware rejects excessively long URLs."""
        long_param = "x" * 3000
        response = client.get(f"/?param={long_param}")
        
        assert response.status_code == 414
    
    def test_middleware_allows_normal_requests(self, client):
        """Test middleware allows normal requests."""
        response = client.get("/")
        
        # Should not be blocked
        assert response.status_code == 200
    
    def test_error_response_format(self, client):
        """Test that error responses have correct format."""
        headers = {"Content-Length": str(20 * 1024 * 1024)}
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        
        assert response.status_code == 413
        data = response.json()
        
        # Should have error and detail fields
        assert "error" in data
        assert "detail" in data
        assert "Request Entity Too Large" in data["error"]
        assert "exceeds maximum" in data["detail"]


class TestSecurityHeadersIntegration:
    """Test integration of all security header enhancements."""
    
    def test_complete_security_header_suite(self, client):
        """Test that complete security header suite is present."""
        response = client.get("/")
        
        # Original headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
        
        # Enhanced headers
        assert response.headers["X-Download-Options"] == "noopen"
        assert response.headers["X-DNS-Prefetch-Control"] == "off"
        assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
        
        # Request tracking
        assert "X-Request-ID" in response.headers
    
    def test_security_score_validation(self, client):
        """Test that application passes security header validation."""
        response = client.get("/")
        
        # Count security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy",
            "X-Download-Options",
            "X-DNS-Prefetch-Control",
            "X-Permitted-Cross-Domain-Policies"
        ]
        
        present_count = sum(1 for h in security_headers if h in response.headers)
        
        # Should have at least 9 out of 9 security headers
        assert present_count >= 9, f"Should have all 9 security headers, found {present_count}"
    
    def test_no_sensitive_info_in_headers(self, client):
        """Test that headers don't expose sensitive information."""
        response = client.get("/")
        
        # Check that we don't expose sensitive info
        sensitive_patterns = ["password", "secret", "key", "token", "database"]
        
        for header_name, header_value in response.headers.items():
            for pattern in sensitive_patterns:
                assert pattern not in header_value.lower(), f"Header {header_name} may expose sensitive info"
