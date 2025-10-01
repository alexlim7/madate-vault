"""
Comprehensive tests for security logging, cleanup, and configuration.
Tests Quick Wins #8 (Security Logging), #9 (Token Cleanup), #10 (Environment Config).
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from app.core.security_logging import SecurityLogger, security_log, security_logger
from app.core.cleanup_service import (
    TokenCleanupService, 
    SessionCleanupService,
    token_cleanup_service,
    session_cleanup_service
)
from app.core.security_config import SecurityConfig, Environment


class TestSecurityLogging:
    """Test security logging functionality."""
    
    def test_security_logger_exists(self):
        """Test that security logger is configured."""
        assert security_logger is not None
        assert security_logger.name == "security"
        assert security_logger.level == logging.INFO
    
    def test_log_auth_success(self, caplog):
        """Test logging successful authentication."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_auth_success(
                user_id="user-123",
                email="test@example.com",
                ip_address="203.0.113.1",
                user_agent="TestClient/1.0"
            )
            
            # Check log was created
            assert len(caplog.records) > 0
            assert "AUTH_SUCCESS" in caplog.text
    
    def test_log_auth_failure(self, caplog):
        """Test logging failed authentication."""
        with caplog.at_level(logging.WARNING, logger="security"):
            security_log.log_auth_failure(
                email="test@example.com",
                ip_address="203.0.113.1",
                reason="Invalid credentials",
                attempts_remaining=3
            )
            
            assert len(caplog.records) > 0
            assert "AUTH_FAILURE" in caplog.text
    
    def test_log_account_lockout(self, caplog):
        """Test logging account lockout."""
        with caplog.at_level(logging.ERROR, logger="security"):
            security_log.log_account_lockout(
                email="test@example.com",
                ip_address="203.0.113.1",
                lockout_duration_seconds=900,
                failed_attempts=5
            )
            
            assert len(caplog.records) > 0
            assert "ACCOUNT_LOCKOUT" in caplog.text
    
    def test_log_permission_denied(self, caplog):
        """Test logging permission denial."""
        with caplog.at_level(logging.WARNING, logger="security"):
            security_log.log_permission_denied(
                user_id="user-123",
                resource="/api/v1/admin/cleanup",
                action="POST",
                reason="Insufficient permissions"
            )
            
            assert len(caplog.records) > 0
            assert "PERMISSION_DENIED" in caplog.text
    
    def test_log_suspicious_activity(self, caplog):
        """Test logging suspicious activity."""
        with caplog.at_level(logging.ERROR, logger="security"):
            security_log.log_suspicious_activity(
                user_id="user-123",
                activity_type="unusual_access_pattern",
                details={"endpoint": "/api/v1/admin", "count": 100},
                ip_address="203.0.113.1"
            )
            
            assert len(caplog.records) > 0
            assert "SUSPICIOUS_ACTIVITY" in caplog.text
    
    def test_log_token_created(self, caplog):
        """Test logging token creation."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_token_created(
                user_id="user-123",
                token_type="access"
            )
            
            assert len(caplog.records) > 0
            assert "TOKEN_CREATED" in caplog.text
    
    def test_log_token_refreshed(self, caplog):
        """Test logging token refresh."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_token_refreshed(user_id="user-123")
            
            assert len(caplog.records) > 0
            assert "TOKEN_REFRESHED" in caplog.text
    
    def test_log_token_invalid(self, caplog):
        """Test logging invalid token usage."""
        with caplog.at_level(logging.WARNING, logger="security"):
            security_log.log_token_invalid(
                reason="Token expired",
                ip_address="203.0.113.1"
            )
            
            assert len(caplog.records) > 0
            assert "TOKEN_INVALID" in caplog.text
    
    def test_log_rate_limit_exceeded(self, caplog):
        """Test logging rate limit exceeded."""
        with caplog.at_level(logging.WARNING, logger="security"):
            security_log.log_rate_limit_exceeded(
                identifier="user-123",
                endpoint="/api/v1/auth/login",
                ip_address="203.0.113.1"
            )
            
            assert len(caplog.records) > 0
            assert "RATE_LIMIT_EXCEEDED" in caplog.text
    
    def test_log_password_changed(self, caplog):
        """Test logging password change."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_password_changed(
                user_id="user-123",
                ip_address="203.0.113.1"
            )
            
            assert len(caplog.records) > 0
            assert "PASSWORD_CHANGED" in caplog.text
    
    def test_log_data_access(self, caplog):
        """Test logging data access."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_data_access(
                user_id="user-123",
                resource_type="mandate",
                resource_id="mandate-456",
                action="read"
            )
            
            assert len(caplog.records) > 0
            assert "DATA_ACCESS" in caplog.text


class TestTokenCleanupService:
    """Test token cleanup service."""
    
    def test_token_cleanup_service_configuration(self):
        """Test token cleanup service is configured."""
        assert token_cleanup_service is not None
        assert token_cleanup_service.cleanup_interval == 3600  # 1 hour
        assert token_cleanup_service.retention_days == 7
    
    async def test_cleanup_expired_tokens(self):
        """Test cleanup of expired tokens."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        service = TokenCleanupService(
            cleanup_interval_seconds=60,
            token_retention_days=7
        )
        
        stats = await service.cleanup_expired_tokens(mock_db)
        
        # Should return stats
        assert isinstance(stats, dict)
        assert "tokens_removed" in stats
        assert "sessions_removed" in stats
        assert "cleanup_time" in stats
    
    def test_cleanup_service_can_be_stopped(self):
        """Test that cleanup service can be stopped."""
        service = TokenCleanupService()
        
        service.stop()
        
        assert service.is_running is False


class TestSessionCleanupService:
    """Test session cleanup service."""
    
    def test_session_cleanup_service_configuration(self):
        """Test session cleanup service is configured."""
        assert session_cleanup_service is not None
        assert session_cleanup_service.cleanup_interval == 300  # 5 minutes
    
    async def test_cleanup_login_protection_data(self):
        """Test cleanup of login protection data."""
        service = SessionCleanupService(cleanup_interval_seconds=60)
        
        stats = await service.cleanup_login_protection_data()
        
        # Should return stats
        assert isinstance(stats, dict)
        assert "attempts_cleaned" in stats
        assert "lockouts_cleaned" in stats
        assert "cleanup_time" in stats
    
    def test_session_cleanup_can_be_stopped(self):
        """Test that session cleanup can be stopped."""
        service = SessionCleanupService()
        
        service.stop()
        
        assert service.is_running is False


class TestEnvironmentBasedConfig:
    """Test environment-based security configuration."""
    
    def test_development_config(self):
        """Test development environment configuration."""
        config = SecurityConfig(Environment.DEVELOPMENT)
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.token_expiry_minutes == 1440  # 24 hours
        assert config.max_login_attempts == 10
        assert config.lockout_duration_minutes == 5
        assert config.password_min_length == 8
        assert config.require_https is False
        assert config.enable_swagger_ui is True
        assert config.enable_debug_endpoints is True
    
    def test_staging_config(self):
        """Test staging environment configuration."""
        config = SecurityConfig(Environment.STAGING)
        
        assert config.environment == Environment.STAGING
        assert config.token_expiry_minutes == 60  # 1 hour
        assert config.max_login_attempts == 5
        assert config.lockout_duration_minutes == 15
        assert config.password_min_length == 12
        assert config.require_https is False
        assert config.enable_swagger_ui is True
    
    def test_production_config(self):
        """Test production environment configuration."""
        config = SecurityConfig(Environment.PRODUCTION)
        
        assert config.environment == Environment.PRODUCTION
        assert config.token_expiry_minutes == 30  # 30 minutes
        assert config.max_login_attempts == 5
        assert config.lockout_duration_minutes == 30
        assert config.password_min_length == 12
        assert config.require_https is True
        assert config.enable_swagger_ui is False
        assert config.enable_debug_endpoints is False
    
    def test_allowed_origins_by_environment(self):
        """Test CORS allowed origins vary by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        staging_config = SecurityConfig(Environment.STAGING)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Development allows localhost
        assert any("localhost" in origin for origin in dev_config.allowed_origins)
        
        # Staging has staging domains
        assert any("staging" in origin for origin in staging_config.allowed_origins)
        
        # Production has production domains only
        assert not any("localhost" in origin for origin in prod_config.allowed_origins)
        assert all("https://" in origin for origin in prod_config.allowed_origins)
    
    def test_log_level_by_environment(self):
        """Test logging level varies by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        staging_config = SecurityConfig(Environment.STAGING)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        assert dev_config.log_level == "DEBUG"
        assert staging_config.log_level == "INFO"
        assert prod_config.log_level == "WARNING"
    
    def test_refresh_token_expiry_by_environment(self):
        """Test refresh token expiry varies by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Development has longer expiry
        assert dev_config.refresh_token_expiry_days == 30
        
        # Production has shorter expiry
        assert prod_config.refresh_token_expiry_days == 7
    
    def test_audit_retention_by_environment(self):
        """Test audit log retention varies by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Development has shorter retention
        assert dev_config.audit_log_retention_days == 30
        
        # Production has longer retention (compliance)
        assert prod_config.audit_log_retention_days == 365
    
    def test_session_cookie_settings_by_environment(self):
        """Test session cookie settings vary by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Development more relaxed
        assert dev_config.session_cookie_samesite == "lax"
        
        # Production stricter
        assert prod_config.session_cookie_secure is True
        assert prod_config.session_cookie_samesite == "strict"
    
    def test_hsts_max_age_by_environment(self):
        """Test HSTS max-age varies by environment."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Development has shorter HSTS
        assert dev_config.hsts_max_age_seconds == 3600  # 1 hour
        
        # Production has longer HSTS
        assert prod_config.hsts_max_age_seconds == 63072000  # 2 years
    
    def test_config_summary(self):
        """Test configuration summary method."""
        config = SecurityConfig(Environment.PRODUCTION)
        summary = config.get_config_summary()
        
        # Should be a dictionary
        assert isinstance(summary, dict)
        
        # Should contain key settings
        assert "environment" in summary
        assert "token_expiry_minutes" in summary
        assert "max_login_attempts" in summary
        assert "require_https" in summary
        
        # Values should match
        assert summary["environment"] == "production"
        assert summary["token_expiry_minutes"] == 30
        assert summary["max_login_attempts"] == 5
    
    def test_security_features_flags(self):
        """Test security feature flags."""
        config = SecurityConfig(Environment.PRODUCTION)
        
        # Check feature flags
        assert config.security_headers_enabled is True
        assert config.rate_limit_enabled is True
        assert config.enable_ip_whitelist is True
        
        # Future features (not yet implemented)
        assert config.require_mfa is False
        assert config.enable_blockchain_audit is False


class TestCleanupServicesIntegration:
    """Test cleanup services integration."""
    
    async def test_token_cleanup_service_runs(self):
        """Test that token cleanup service can run."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        service = TokenCleanupService(cleanup_interval_seconds=1)
        
        # Run cleanup once
        stats = await service.cleanup_expired_tokens(mock_db)
        
        assert stats is not None
        assert "cleanup_time" in stats
    
    async def test_session_cleanup_service_runs(self):
        """Test that session cleanup service can run."""
        service = SessionCleanupService(cleanup_interval_seconds=1)
        
        # Run cleanup once
        stats = await service.cleanup_login_protection_data()
        
        assert stats is not None
        assert "cleanup_time" in stats
    
    def test_cleanup_services_global_instances(self):
        """Test that global cleanup service instances exist."""
        assert token_cleanup_service is not None
        assert session_cleanup_service is not None
        
        assert isinstance(token_cleanup_service, TokenCleanupService)
        assert isinstance(session_cleanup_service, SessionCleanupService)


class TestSecurityLoggingContent:
    """Test security logging content and format."""
    
    def test_log_includes_timestamp(self, caplog):
        """Test that logs include timestamps."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_auth_success(
                user_id="user-123",
                email="test@example.com",
                ip_address="203.0.113.1"
            )
            
            # Check timestamp in log
            assert len(caplog.records) > 0
            record = caplog.records[0]
            assert hasattr(record, 'created')
    
    def test_log_includes_event_type(self, caplog):
        """Test that logs include event type."""
        with caplog.at_level(logging.INFO, logger="security"):
            security_log.log_auth_success(
                user_id="user-123",
                email="test@example.com",
                ip_address="203.0.113.1"
            )
            
            assert "AUTH_SUCCESS" in caplog.text
    
    def test_log_does_not_include_sensitive_data(self, caplog):
        """Test that logs don't include sensitive data."""
        with caplog.at_level(logging.INFO, logger="security"):
            # Log an event
            security_log.log_auth_success(
                user_id="user-123",
                email="test@example.com",
                ip_address="203.0.113.1"
            )
            
            # Should not contain sensitive patterns
            log_text = caplog.text.lower()
            sensitive_patterns = ["password", "secret", "token", "key"]
            
            for pattern in sensitive_patterns:
                assert pattern not in log_text, f"Log should not contain {pattern}"


class TestEnvironmentConfigEdgeCases:
    """Test edge cases for environment configuration."""
    
    def test_all_environments_have_valid_config(self):
        """Test that all environments have valid configuration."""
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
            config = SecurityConfig(env)
            
            # All should have positive values
            assert config.token_expiry_minutes > 0
            assert config.max_login_attempts > 0
            assert config.lockout_duration_minutes > 0
            assert config.password_min_length > 0
            
            # All should have allowed origins
            assert len(config.allowed_origins) > 0
    
    def test_production_is_most_restrictive(self):
        """Test that production has strictest settings."""
        dev_config = SecurityConfig(Environment.DEVELOPMENT)
        prod_config = SecurityConfig(Environment.PRODUCTION)
        
        # Production should be stricter
        assert prod_config.token_expiry_minutes < dev_config.token_expiry_minutes
        assert prod_config.lockout_duration_minutes > dev_config.lockout_duration_minutes
        assert prod_config.require_https is True
        assert dev_config.require_https is False
    
    def test_config_summary_completeness(self):
        """Test that config summary includes all important settings."""
        config = SecurityConfig(Environment.PRODUCTION)
        summary = config.get_config_summary()
        
        required_keys = [
            "environment",
            "require_https",
            "token_expiry_minutes",
            "max_login_attempts",
            "lockout_duration_minutes",
            "password_min_length",
            "rate_limit_enabled",
            "audit_log_retention_days"
        ]
        
        for key in required_keys:
            assert key in summary, f"Config summary should include {key}"


class TestSecurityEnhancementsIntegration:
    """Test integration of all security enhancements."""
    
    def test_all_services_initialized(self):
        """Test that all security services are initialized."""
        # Check global instances exist
        assert security_log is not None
        assert token_cleanup_service is not None
        assert session_cleanup_service is not None
        
        # Check they are correct types
        assert isinstance(security_log, SecurityLogger)
        assert isinstance(token_cleanup_service, TokenCleanupService)
        assert isinstance(session_cleanup_service, SessionCleanupService)
    
    def test_security_config_can_create_all_environments(self):
        """Test that SecurityConfig works for all environments."""
        configs = []
        
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
            config = SecurityConfig(env)
            configs.append(config)
            
            # Each should be valid
            assert config.environment == env
        
        # Should have 3 different configs
        assert len(configs) == 3
    
    def test_logging_and_cleanup_work_together(self, caplog):
        """Test that logging and cleanup services work together."""
        with caplog.at_level(logging.INFO, logger="security"):
            # Log an event
            security_log.log_auth_success(
                user_id="user-123",
                email="test@example.com",
                ip_address="203.0.113.1"
            )
            
            # Service should exist
            assert session_cleanup_service is not None
            
            # Log should be created
            assert "AUTH_SUCCESS" in caplog.text
