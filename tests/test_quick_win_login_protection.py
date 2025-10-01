"""
Comprehensive tests for failed login rate limiting.
Tests Quick Win #6 (Failed Login Protection).
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.login_protection import LoginProtection, login_protection
from app.core.auth import User, UserRole, UserStatus


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
        created_at=datetime.now()
    )


@pytest.fixture
def fresh_login_protection():
    """Fresh login protection instance for testing."""
    protection = LoginProtection(
        max_attempts=5,
        lockout_duration_minutes=15,
        tracking_window_hours=1
    )
    return protection


class TestLoginProtectionCore:
    """Test core login protection functionality."""
    
    def test_login_protection_configuration(self, fresh_login_protection):
        """Test login protection is properly configured."""
        assert fresh_login_protection.max_attempts == 5
        assert fresh_login_protection.lockout_duration == timedelta(minutes=15)
        assert fresh_login_protection.tracking_window == timedelta(hours=1)
    
    def test_record_failed_login(self, fresh_login_protection):
        """Test recording failed login attempt."""
        email = "test@example.com"
        
        # Initially no failed attempts
        assert fresh_login_protection.get_failed_attempts_count(email) == 0
        
        # Record a failed attempt
        fresh_login_protection.record_failed_login(email)
        
        # Should have 1 failed attempt
        assert fresh_login_protection.get_failed_attempts_count(email) == 1
    
    def test_multiple_failed_attempts(self, fresh_login_protection):
        """Test recording multiple failed login attempts."""
        email = "test@example.com"
        
        # Record 3 failed attempts
        for i in range(3):
            fresh_login_protection.record_failed_login(email)
        
        # Should have 3 failed attempts
        assert fresh_login_protection.get_failed_attempts_count(email) == 3
    
    def test_lockout_after_max_attempts(self, fresh_login_protection):
        """Test account is locked out after max attempts."""
        email = "test@example.com"
        
        # Record max attempts
        for i in range(5):
            fresh_login_protection.record_failed_login(email)
        
        # Should be locked out
        assert fresh_login_protection.is_locked_out(email) is True
    
    def test_not_locked_out_before_max_attempts(self, fresh_login_protection):
        """Test account is not locked out before max attempts."""
        email = "test@example.com"
        
        # Record 4 attempts (less than max)
        for i in range(4):
            fresh_login_protection.record_failed_login(email)
        
        # Should not be locked out yet
        assert fresh_login_protection.is_locked_out(email) is False
    
    def test_lockout_remaining_seconds(self, fresh_login_protection):
        """Test getting remaining lockout time."""
        email = "test@example.com"
        
        # Lock out the account
        for i in range(5):
            fresh_login_protection.record_failed_login(email)
        
        # Get remaining time
        remaining = fresh_login_protection.get_lockout_remaining_seconds(email)
        
        # Should have time remaining (close to 15 minutes = 900 seconds)
        assert remaining > 0
        assert remaining <= 900  # Should be at most 15 minutes
    
    def test_clear_failed_attempts(self, fresh_login_protection):
        """Test clearing failed attempts on successful login."""
        email = "test@example.com"
        
        # Record some failed attempts
        for i in range(3):
            fresh_login_protection.record_failed_login(email)
        
        assert fresh_login_protection.get_failed_attempts_count(email) == 3
        
        # Clear attempts
        fresh_login_protection.clear_failed_attempts(email)
        
        # Should have 0 attempts
        assert fresh_login_protection.get_failed_attempts_count(email) == 0
        assert fresh_login_protection.is_locked_out(email) is False
    
    def test_cleanup_old_attempts(self, fresh_login_protection):
        """Test that old attempts are cleaned up."""
        email = "test@example.com"
        
        # Record an attempt
        fresh_login_protection.record_failed_login(email)
        
        # Simulate old timestamp (2 hours ago)
        old_time = datetime.utcnow() - timedelta(hours=2)
        fresh_login_protection.failed_attempts[email] = [old_time]
        
        # Cleanup should remove old attempts
        fresh_login_protection._cleanup_old_attempts(email)
        
        # Should be cleaned up (tracking window is 1 hour)
        assert fresh_login_protection.get_failed_attempts_count(email) == 0
    
    def test_different_identifiers_tracked_separately(self, fresh_login_protection):
        """Test that different emails are tracked separately."""
        email1 = "user1@example.com"
        email2 = "user2@example.com"
        
        # Record attempts for email1
        for i in range(3):
            fresh_login_protection.record_failed_login(email1)
        
        # Record attempts for email2
        for i in range(2):
            fresh_login_protection.record_failed_login(email2)
        
        # Should be tracked separately
        assert fresh_login_protection.get_failed_attempts_count(email1) == 3
        assert fresh_login_protection.get_failed_attempts_count(email2) == 2


class TestLoginProtectionIntegration:
    """Test login protection integration with auth endpoint."""
    
    def test_login_with_valid_credentials_no_protection(self, client, sample_user):
        """Test that valid login is not affected by protection."""
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = sample_user
            
            login_data = {
                "email": "test@example.com",
                "password": "correct_password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            # Should succeed
            assert response.status_code == 200
    
    def test_login_shows_attempts_remaining(self, client):
        """Test that failed login shows attempts remaining."""
        # Clear any existing attempts
        login_protection.clear_failed_attempts("test@example.com")
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None  # Invalid credentials
            
            login_data = {
                "email": "test@example.com",
                "password": "wrong_password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            # Should show attempts remaining
            assert response.status_code == 401
            assert "attempts remaining" in response.json()["detail"]
        
        # Clear for other tests
        login_protection.clear_failed_attempts("test@example.com")
    
    def test_login_lockout_after_max_attempts(self, client):
        """Test that account is locked out after max attempts."""
        email = "lockout-test@example.com"
        
        # Clear any existing attempts
        login_protection.clear_failed_attempts(email)
        
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None  # Invalid credentials
            
            login_data = {
                "email": email,
                "password": "wrong_password"
            }
            
            # Make 5 failed attempts
            for i in range(5):
                response = client.post("/api/v1/auth/login", json=login_data)
                if i < 4:
                    assert response.status_code == 401
            
            # 6th attempt should be locked out
            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 429
            assert "locked" in response.json()["detail"].lower()
        
        # Clear for other tests
        login_protection.clear_failed_attempts(email)
    
    def test_login_clears_attempts_on_success(self, client, sample_user):
        """Test that successful login clears failed attempts."""
        email = "clear-test@example.com"
        
        # Record some failed attempts first
        for i in range(3):
            login_protection.record_failed_login(email)
        
        assert login_protection.get_failed_attempts_count(email) == 3
        
        # Now login successfully
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = sample_user
            
            login_data = {
                "email": email,
                "password": "correct_password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            # Should succeed
            assert response.status_code == 200
        
        # Failed attempts should be cleared
        assert login_protection.get_failed_attempts_count(email) == 0
    
    def test_lockout_prevents_further_attempts(self, client):
        """Test that locked out account cannot attempt login."""
        email = "prevent-test@example.com"
        
        # Clear and lock out
        login_protection.clear_failed_attempts(email)
        for i in range(5):
            login_protection.record_failed_login(email)
        
        assert login_protection.is_locked_out(email) is True
        
        # Try to login while locked out
        with patch('app.api.v1.endpoints.auth.AuthService.authenticate_user') as mock_auth:
            mock_auth.return_value = None
            
            login_data = {
                "email": email,
                "password": "any_password"
            }
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            # Should be rejected before authentication
            assert response.status_code == 429
            # Mock should not be called
            assert mock_auth.call_count == 0
        
        # Clear for other tests
        login_protection.clear_failed_attempts(email)


class TestLoginProtectionPerformance:
    """Test login protection performance."""
    
    def test_protection_minimal_overhead(self, fresh_login_protection):
        """Test that login protection has minimal overhead."""
        import time
        
        start_time = time.time()
        
        # Simulate 100 login attempts
        for i in range(100):
            email = f"user{i}@example.com"
            fresh_login_protection.record_failed_login(email)
            fresh_login_protection.is_locked_out(email)
            fresh_login_protection.get_failed_attempts_count(email)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be very fast (< 1 second for 100 operations)
        assert duration < 1.0, "Login protection should have minimal overhead"
    
    def test_cleanup_performance(self, fresh_login_protection):
        """Test that cleanup is efficient."""
        import time
        
        # Add 100 entries
        for i in range(100):
            email = f"user{i}@example.com"
            fresh_login_protection.record_failed_login(email)
        
        start_time = time.time()
        
        # Cleanup all
        for i in range(100):
            email = f"user{i}@example.com"
            fresh_login_protection._cleanup_old_attempts(email)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be fast
        assert duration < 0.5, "Cleanup should be efficient"
