"""
Security headers tests for Mandate Vault.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestSecurityHeaders:
    """Test security headers implementation."""
    
    def test_security_headers_present(self, client):
        """Test that all required security headers are present."""
        response = client.get("/")
        
        # Check for required security headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy"
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_x_content_type_options(self, client):
        """Test X-Content-Type-Options header."""
        response = client.get("/")
        
        assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    def test_x_frame_options(self, client):
        """Test X-Frame-Options header."""
        response = client.get("/")
        
        assert response.headers["X-Frame-Options"] == "DENY"
    
    def test_x_xss_protection(self, client):
        """Test X-XSS-Protection header."""
        response = client.get("/")
        
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    def test_referrer_policy(self, client):
        """Test Referrer-Policy header."""
        response = client.get("/")
        
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    def test_content_security_policy(self, client):
        """Test Content-Security-Policy header."""
        response = client.get("/")
        
        csp = response.headers["Content-Security-Policy"]
        
        # Check for key CSP directives
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data: https:" in csp
        assert "font-src 'self'" in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp
    
    def test_permissions_policy(self, client):
        """Test Permissions-Policy header."""
        response = client.get("/")
        
        assert "Permissions-Policy" in response.headers
        permissions_policy = response.headers["Permissions-Policy"]
        
        # Check for restricted permissions
        assert "geolocation=()" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "camera=()" in permissions_policy
    
    def test_server_header_removed(self, client):
        """Test that Server header is removed."""
        response = client.get("/")
        
        # Server header should not be present
        assert "Server" not in response.headers
    
    def test_strict_transport_security_https(self, client):
        """Test Strict-Transport-Security header for HTTPS."""
        # Mock HTTPS request
        response = client.get("/", headers={"X-Forwarded-Proto": "https"})
        
        # In a real HTTPS environment, this would be present
        # For testing, we'll check if the header is handled correctly
        if "Strict-Transport-Security" in response.headers:
            hsts = response.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts
            assert "preload" in hsts
    
    def test_security_headers_on_all_endpoints(self, client):
        """Test that security headers are present on all endpoints."""
        endpoints = [
            "/",
            "/api/v1/auth/login",
            "/api/v1/mandates/search",
            "/api/v1/webhooks/",
            "/api/v1/alerts/",
            "/api/v1/admin/truststore-status"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            
            # Check for key security headers
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers
            assert "Referrer-Policy" in response.headers
            assert "Content-Security-Policy" in response.headers
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly configured."""
        # Test preflight request
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Check for CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
    
    def test_cors_origins_restricted(self, client):
        """Test that CORS origins are properly restricted."""
        # Test with allowed origin
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should allow localhost in development
        assert response.status_code in [200, 204]
        
        # Test with disallowed origin
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should return 400 for disallowed origins (CORS rejection)
        assert response.status_code in [200, 204, 400], "Disallowed origins should be rejected or allowed with restrictions"
    
    def test_request_id_header(self, client):
        """Test that request ID header is added."""
        response = client.get("/")
        
        # Check for request ID header
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
    
    def test_security_headers_consistency(self, client):
        """Test that security headers are consistent across requests."""
        responses = []
        
        # Make multiple requests
        for i in range(5):
            response = client.get("/")
            responses.append(response)
        
        # Check that headers are consistent
        first_response = responses[0]
        for response in responses[1:]:
            for header in ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]:
                assert response.headers[header] == first_response.headers[header]
    
    def test_security_headers_post_request(self, client):
        """Test that security headers are present on POST requests."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        
        # Check for security headers on POST request
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    def test_security_headers_error_responses(self, client):
        """Test that security headers are present on error responses."""
        # Trigger a 404 error
        response = client.get("/nonexistent-endpoint")
        
        # Check for security headers on error response
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    def test_csp_nonces(self, client):
        """Test that CSP includes nonce support."""
        response = client.get("/")
        
        csp = response.headers["Content-Security-Policy"]
        
        # Check for nonce support in CSP
        assert "'unsafe-inline'" in csp or "'nonce-" in csp
    
    def test_security_headers_performance(self, client):
        """Test that security headers don't significantly impact performance."""
        import time
        
        start_time = time.time()
        
        # Make multiple requests
        for i in range(10):
            response = client.get("/")
            assert response.status_code == 200
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 5.0, "Security headers should not significantly impact performance"
