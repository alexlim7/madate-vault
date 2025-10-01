"""
Rate limiting configuration tests for Mandate Vault.

Note: These tests verify rate limiting configuration is present.
Actual rate limiting enforcement requires Redis in production.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.rate_limiting import RATE_LIMITS, get_rate_limit_for_endpoint


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestRateLimitingConfiguration:
    """Test rate limiting configuration."""
    
    def test_rate_limit_configuration_exists(self):
        """Test that rate limit configuration exists."""
        assert RATE_LIMITS is not None
        assert isinstance(RATE_LIMITS, dict)
        assert len(RATE_LIMITS) > 0
    
    def test_auth_rate_limits_configured(self):
        """Test that auth endpoints have rate limits."""
        assert "auth" in RATE_LIMITS
        assert "login" in RATE_LIMITS["auth"]
        assert RATE_LIMITS["auth"]["login"] == "5/minute"
    
    def test_mandate_rate_limits_configured(self):
        """Test that mandate endpoints have rate limits."""
        assert "mandates" in RATE_LIMITS
        assert "create" in RATE_LIMITS["mandates"]
        assert "search" in RATE_LIMITS["mandates"]
    
    def test_webhook_rate_limits_configured(self):
        """Test that webhook endpoints have rate limits."""
        assert "webhooks" in RATE_LIMITS
        assert "create" in RATE_LIMITS["webhooks"]
        assert "list" in RATE_LIMITS["webhooks"]
    
    def test_alert_rate_limits_configured(self):
        """Test that alert endpoints have rate limits."""
        assert "alerts" in RATE_LIMITS
        assert "create" in RATE_LIMITS["alerts"]
        assert "list" in RATE_LIMITS["alerts"]
    
    def test_admin_rate_limits_configured(self):
        """Test that admin endpoints have rate limits."""
        assert "admin" in RATE_LIMITS
        assert "cleanup" in RATE_LIMITS["admin"]
        assert "status" in RATE_LIMITS["admin"]
    
    def test_get_rate_limit_for_endpoint_auth(self):
        """Test getting rate limit for auth endpoint."""
        rate_limit = get_rate_limit_for_endpoint("auth", "login")
        assert rate_limit == "5/minute"
    
    def test_get_rate_limit_for_endpoint_mandate(self):
        """Test getting rate limit for mandate endpoint."""
        rate_limit = get_rate_limit_for_endpoint("mandates", "create")
        assert rate_limit == "20/minute"
    
    def test_get_rate_limit_for_endpoint_default(self):
        """Test getting rate limit for unknown endpoint."""
        rate_limit = get_rate_limit_for_endpoint("unknown", "unknown")
        assert rate_limit == "100/minute"  # Default rate limit
    
    def test_application_has_rate_limiter(self):
        """Test that application has rate limiter configured."""
        assert hasattr(app.state, 'limiter')
        assert app.state.limiter is not None
    
    def test_strict_rate_limits_configured(self):
        """Test that strict operations have low rate limits."""
        # Login should have strict limit
        assert RATE_LIMITS["auth"]["login"] == "5/minute"
        
        # Cleanup should have very strict limit
        assert RATE_LIMITS["admin"]["cleanup"] == "1/hour"
    
    def test_permissive_rate_limits_configured(self):
        """Test that read operations have higher rate limits."""
        # Search operations should allow more requests
        assert "100/minute" in RATE_LIMITS["mandates"]["search"]
        
        # Status checks should allow many requests
        assert "100/minute" in RATE_LIMITS["admin"]["status"]
