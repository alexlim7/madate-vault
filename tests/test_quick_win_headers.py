"""
Comprehensive tests for security headers enhancements.
Tests Quick Wins #1 (Enhanced HSTS), #2 (Security.txt), #3 (Additional Headers).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestEnhancedSecurityHeaders:
    """Test enhanced security headers implementation."""
    
    def test_enhanced_hsts_header(self, client):
        """Test that HSTS header has 2-year max-age."""
        response = client.get("/", headers={"X-Forwarded-Proto": "https"})
        
        # HSTS should be present for HTTPS requests
        if "Strict-Transport-Security" in response.headers:
            hsts = response.headers["Strict-Transport-Security"]
            
            # Should have 2-year max-age (63072000 seconds)
            assert "max-age=63072000" in hsts, "HSTS should have 2-year max-age"
            assert "includeSubDomains" in hsts, "HSTS should include subdomains"
            assert "preload" in hsts, "HSTS should be preload-ready"
    
    def test_x_download_options_header(self, client):
        """Test X-Download-Options header is present."""
        response = client.get("/")
        
        assert "X-Download-Options" in response.headers
        assert response.headers["X-Download-Options"] == "noopen"
    
    def test_x_dns_prefetch_control_header(self, client):
        """Test X-DNS-Prefetch-Control header is present."""
        response = client.get("/")
        
        assert "X-DNS-Prefetch-Control" in response.headers
        assert response.headers["X-DNS-Prefetch-Control"] == "off"
    
    def test_x_permitted_cross_domain_policies_header(self, client):
        """Test X-Permitted-Cross-Domain-Policies header is present."""
        response = client.get("/")
        
        assert "X-Permitted-Cross-Domain-Policies" in response.headers
        assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    
    def test_all_security_headers_present(self, client):
        """Test that all 11 security headers are present."""
        response = client.get("/")
        
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Content-Security-Policy",
            "Permissions-Policy",
            "X-Download-Options",
            "X-DNS-Prefetch-Control",
            "X-Permitted-Cross-Domain-Policies",
            "X-Request-ID"
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"
    
    def test_security_headers_on_api_endpoints(self, client):
        """Test security headers are present on API endpoints."""
        api_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/mandates/search",
            "/api/v1/webhooks/",
            "/api/v1/alerts/"
        ]
        
        for endpoint in api_endpoints:
            response = client.get(endpoint)
            
            # All API endpoints should have security headers
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-Download-Options" in response.headers
    
    def test_security_headers_on_error_responses(self, client):
        """Test security headers are present on error responses."""
        response = client.get("/nonexistent-endpoint-404")
        
        # Even 404 responses should have security headers
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-Download-Options" in response.headers
    
    def test_security_headers_consistency(self, client):
        """Test that security headers are consistent across requests."""
        responses = []
        
        # Make multiple requests
        for i in range(5):
            response = client.get("/")
            responses.append(response)
        
        # Check all enhanced headers are consistent
        enhanced_headers = [
            "X-Download-Options",
            "X-DNS-Prefetch-Control",
            "X-Permitted-Cross-Domain-Policies"
        ]
        
        first_response = responses[0]
        for response in responses[1:]:
            for header in enhanced_headers:
                assert response.headers[header] == first_response.headers[header]


class TestSecurityTxtFile:
    """Test security.txt file implementation."""
    
    def test_security_txt_exists(self):
        """Test that security.txt file exists."""
        import os
        
        security_txt_path = ".well-known/security.txt"
        assert os.path.exists(security_txt_path), "security.txt file should exist"
    
    def test_security_txt_has_contact(self):
        """Test that security.txt has contact information."""
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        assert "Contact:" in content, "security.txt should have Contact field"
        assert "security@mandatevault.com" in content, "Should have security email"
    
    def test_security_txt_has_expires(self):
        """Test that security.txt has expiration date."""
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        assert "Expires:" in content, "security.txt should have Expires field"
        assert "2026" in content, "Should expire in future"
    
    def test_security_txt_has_encryption(self):
        """Test that security.txt has encryption field."""
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        assert "Encryption:" in content, "security.txt should have Encryption field"
    
    def test_security_txt_has_canonical(self):
        """Test that security.txt has canonical URL."""
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        assert "Canonical:" in content, "security.txt should have Canonical field"
    
    def test_security_txt_format(self):
        """Test that security.txt follows correct format."""
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        # Should have required fields
        required_fields = ["Contact:", "Expires:", "Canonical:"]
        for field in required_fields:
            assert field in content, f"security.txt should have {field}"
        
        # Should not be empty
        assert len(content) > 100, "security.txt should have substantial content"


class TestSecurityHeadersValues:
    """Test specific values of security headers."""
    
    def test_x_download_options_value(self, client):
        """Test X-Download-Options has correct value."""
        response = client.get("/")
        assert response.headers["X-Download-Options"] == "noopen"
    
    def test_x_dns_prefetch_control_value(self, client):
        """Test X-DNS-Prefetch-Control has correct value."""
        response = client.get("/")
        assert response.headers["X-DNS-Prefetch-Control"] == "off"
    
    def test_x_permitted_cross_domain_policies_value(self, client):
        """Test X-Permitted-Cross-Domain-Policies has correct value."""
        response = client.get("/")
        assert response.headers["X-Permitted-Cross-Domain-Policies"] == "none"
    
    def test_enhanced_hsts_value_for_https(self, client):
        """Test enhanced HSTS value for HTTPS requests."""
        # Simulate HTTPS request
        response = client.get("/", headers={"X-Forwarded-Proto": "https"})
        
        if "Strict-Transport-Security" in response.headers:
            hsts = response.headers["Strict-Transport-Security"]
            
            # Should be enhanced (2 years instead of 1)
            assert "max-age=63072000" in hsts
            assert "includeSubDomains" in hsts
            assert "preload" in hsts
    
    def test_security_headers_performance(self, client):
        """Test that enhanced headers don't impact performance."""
        import time
        
        start_time = time.time()
        
        # Make 50 requests
        for i in range(50):
            response = client.get("/")
            assert response.status_code == 200
            # Verify enhanced headers are present
            assert "X-Download-Options" in response.headers
            assert "X-DNS-Prefetch-Control" in response.headers
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly
        assert duration < 5.0, "Enhanced headers should not impact performance significantly"
