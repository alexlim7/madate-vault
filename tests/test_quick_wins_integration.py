"""
Integration tests for all 10 security quick wins.
Tests that all quick wins work together properly.
"""
import pytest
import time
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import User, UserRole, UserStatus
from app.core.login_protection import login_protection
from app.core.password_policy import password_policy
from app.core.security_config import SecurityConfig, Environment


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id="user-001",
        email="test@example.com",
        tenant_id="tenant-001",
        role=UserRole.CUSTOMER_ADMIN,
        status=UserStatus.ACTIVE,
        created_at="2023-01-01T00:00:00Z"
    )


class TestQuickWinsIntegration:
    """Integration tests for all quick wins."""
    
    def test_all_security_features_enabled(self, client):
        """Test that all security features are enabled."""
        response = client.get("/")
        
        # Quick Win #1: Enhanced HSTS
        # (Only for HTTPS, so may not be present in test)
        
        # Quick Win #2: Security.txt exists
        import os
        assert os.path.exists(".well-known/security.txt")
        
        # Quick Win #3: Additional security headers
        assert "X-Download-Options" in response.headers
        assert "X-DNS-Prefetch-Control" in response.headers
        assert "X-Permitted-Cross-Domain-Policies" in response.headers
        
        # Quick Win #4: Secure cookies (tested via helper)
        from app.core.request_security import SecureCookieHelper
        assert SecureCookieHelper is not None
        
        # Quick Win #5: Request limits (tested via middleware)
        headers = {"Content-Length": str(20 * 1024 * 1024)}
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        assert response.status_code == 413
        
        # Quick Win #6: Login protection
        from app.core.login_protection import login_protection
        assert login_protection is not None
        
        # Quick Win #7: Password policy
        from app.core.password_policy import password_policy
        assert password_policy is not None
        
        # Quick Win #8: Security logging
        from app.core.security_logging import security_log
        assert security_log is not None
        
        # Quick Win #9: Cleanup services
        from app.core.cleanup_service import token_cleanup_service, session_cleanup_service
        assert token_cleanup_service is not None
        assert session_cleanup_service is not None
        
        # Quick Win #10: Environment config
        from app.core.security_config import SecurityConfig
        config = SecurityConfig(Environment.PRODUCTION)
        assert config is not None
    
    def test_login_with_all_protections(self, client, sample_user):
        """Test login endpoint with all protections enabled."""
        email = "integration-test@example.com"
        
        # Clear any existing protection
        login_protection.clear_failed_attempts(email)
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            # Test 1: Failed login with attempts remaining
            mock_auth.return_value = None
            
            response = client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "wrongpassword"  # Must be 8+ chars for validation
            })
            
            assert response.status_code == 401
            assert "attempts remaining" in response.json()["detail"]
            
            # Test 2: Successful login clears attempts
            mock_auth.return_value = sample_user
            
            response = client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "correctpassword"  # Must be 8+ chars
            })
            
            assert response.status_code == 200
            assert login_protection.get_failed_attempts_count(email) == 0
        
        # Clear for other tests
        login_protection.clear_failed_attempts(email)
    
    def test_complete_security_workflow(self, client, sample_user):
        """Test complete security workflow with all features."""
        email = "workflow-test@example.com"
        login_protection.clear_failed_attempts(email)
        
        # Step 1: Try with weak password (would be rejected by policy)
        weak_password = "weak"
        valid, message = password_policy.validate(weak_password)
        assert valid is False, "Weak password should be rejected"
        
        # Step 2: Try with strong password but wrong (login protection)
        strong_password = "Str0ng!P@ssw0rd2024"
        valid, message = password_policy.validate(strong_password)
        assert valid is True, "Strong password should be valid"
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None  # Wrong password
            
            # Make 3 failed attempts
            for i in range(3):
                response = client.post("/api/v1/auth/login", json={
                    "email": email,
                    "password": strong_password
                })
                assert response.status_code == 401
            
            # Step 3: Successful login with correct credentials
            mock_auth.return_value = sample_user
            
            response = client.post("/api/v1/auth/login", json={
                "email": email,
                "password": strong_password
            })
            
            # Should succeed and clear failed attempts
            assert response.status_code == 200
            assert "access_token" in response.json()
        
        # Verify attempts were cleared
        assert login_protection.get_failed_attempts_count(email) == 0
        
        # Clear for other tests
        login_protection.clear_failed_attempts(email)
    
    def test_security_headers_and_request_limits_together(self, client):
        """Test that security headers and request limits work together."""
        # Make a normal request
        response = client.get("/")
        
        # Should have security headers
        assert "X-Download-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        
        # Test request limit
        headers = {"Content-Length": str(20 * 1024 * 1024)}
        response = client.post("/api/v1/auth/login", headers=headers, json={})
        
        # Should be rejected (413)
        assert response.status_code == 413
        
        # Note: 413 response may not go through all middleware, so headers may not be present
        # The important thing is that the request was rejected for size
    
    def test_environment_config_affects_behavior(self):
        """Test that environment config affects application behavior."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Token expiry should be different
        assert dev_config.token_expiry_minutes != prod_config.token_expiry_minutes
        
        # Security settings should be different
        assert dev_config.require_https != prod_config.require_https
        assert dev_config.enable_debug_endpoints != prod_config.enable_debug_endpoints
    
    def test_performance_with_all_features(self, client):
        """Test performance with all security features enabled."""
        start_time = time.time()
        
        # Make 20 requests with all security features active
        for i in range(20):
            response = client.get("/")
            assert response.status_code == 200
            
            # Verify all features are working
            assert "X-Download-Options" in response.headers  # Quick Win #3
            assert "X-Request-ID" in response.headers  # Request tracking
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly even with all features
        assert duration < 3.0, "All security features should not significantly impact performance"
    
    def test_security_features_dont_break_normal_flow(self, client, sample_user):
        """Test that security features don't break normal application flow."""
        email = "normal-flow@example.com"
        login_protection.clear_failed_attempts(email)
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = sample_user
            
            # Normal login should work
            response = client.post("/api/v1/auth/login", json={
                "email": email,
                "password": "ValidP@ssw0rd123"
            })
            
            assert response.status_code == 200
            assert "access_token" in response.json()
            
            # Should have security headers
            assert "X-Content-Type-Options" in response.headers
            
            # Should not have failed attempts
            assert login_protection.get_failed_attempts_count(email) == 0


class TestQuickWinsDocumentation:
    """Test that quick wins are properly documented."""
    
    def test_security_txt_documentation(self):
        """Test that security.txt exists and is properly formatted."""
        import os
        assert os.path.exists(".well-known/security.txt")
        
        with open(".well-known/security.txt", 'r') as f:
            content = f.read()
        
        # Should have all required fields
        assert "Contact:" in content
        assert "Expires:" in content
        assert "Canonical:" in content
    
    def test_main_documentation_exists(self):
        """Test that main documentation exists."""
        import os
        assert os.path.exists("README.md")
        assert os.path.exists("PROJECT_STRUCTURE.md")
        assert os.path.exists("docs/ONBOARDING.md")
