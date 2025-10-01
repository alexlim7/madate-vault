"""
Environment-based security configuration for Mandate Vault.
Adjusts security settings based on deployment environment.
"""
from enum import Enum
from typing import List


class Environment(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class SecurityConfig:
    """
    Environment-specific security configuration.
    
    Provides different security settings based on environment:
    - Development: Relaxed for testing
    - Staging: Similar to production but with some relaxations
    - Production: Strictest security settings
    """
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize security config for environment.
        
        Args:
            environment: Deployment environment
        """
        self.environment = environment
    
    @property
    def require_https(self) -> bool:
        """Whether to require HTTPS connections."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def token_expiry_minutes(self) -> int:
        """Access token expiry time in minutes."""
        return {
            Environment.DEVELOPMENT: 1440,  # 24 hours (convenient for dev)
            Environment.STAGING: 60,        # 1 hour
            Environment.PRODUCTION: 30      # 30 minutes (most secure)
        }[self.environment]
    
    @property
    def refresh_token_expiry_days(self) -> int:
        """Refresh token expiry time in days."""
        return {
            Environment.DEVELOPMENT: 30,    # 30 days
            Environment.STAGING: 14,        # 14 days
            Environment.PRODUCTION: 7       # 7 days
        }[self.environment]
    
    @property
    def allowed_origins(self) -> List[str]:
        """CORS allowed origins."""
        if self.environment == Environment.PRODUCTION:
            return [
                "https://app.mandatevault.com",
                "https://www.mandatevault.com"
            ]
        elif self.environment == Environment.STAGING:
            return [
                "https://staging-app.mandatevault.com",
                "https://staging.mandatevault.com"
            ]
        else:  # Development
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ]
    
    @property
    def enable_debug_endpoints(self) -> bool:
        """Whether to enable debug endpoints."""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def enable_swagger_ui(self) -> bool:
        """Whether to enable Swagger UI documentation."""
        return self.environment != Environment.PRODUCTION
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return {
            Environment.DEVELOPMENT: "DEBUG",
            Environment.STAGING: "INFO",
            Environment.PRODUCTION: "WARNING"
        }[self.environment]
    
    @property
    def session_cookie_secure(self) -> bool:
        """Whether session cookies require HTTPS."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def session_cookie_samesite(self) -> str:
        """SameSite policy for session cookies."""
        return {
            Environment.DEVELOPMENT: "lax",
            Environment.STAGING: "strict",
            Environment.PRODUCTION: "strict"
        }[self.environment]
    
    @property
    def max_login_attempts(self) -> int:
        """Maximum failed login attempts before lockout."""
        return {
            Environment.DEVELOPMENT: 10,    # Relaxed for testing
            Environment.STAGING: 5,
            Environment.PRODUCTION: 5
        }[self.environment]
    
    @property
    def lockout_duration_minutes(self) -> int:
        """Account lockout duration in minutes."""
        return {
            Environment.DEVELOPMENT: 5,     # Short lockout for dev
            Environment.STAGING: 15,
            Environment.PRODUCTION: 30      # Longer lockout for production
        }[self.environment]
    
    @property
    def password_min_length(self) -> int:
        """Minimum password length."""
        return {
            Environment.DEVELOPMENT: 8,     # Relaxed for testing
            Environment.STAGING: 12,
            Environment.PRODUCTION: 12
        }[self.environment]
    
    @property
    def require_mfa(self) -> bool:
        """Whether to require multi-factor authentication."""
        # This would be configurable per user/tenant in real implementation
        return False  # Not yet implemented
    
    @property
    def rate_limit_enabled(self) -> bool:
        """Whether rate limiting is enabled."""
        return self.environment in [Environment.STAGING, Environment.PRODUCTION]
    
    @property
    def audit_log_retention_days(self) -> int:
        """How long to retain audit logs."""
        return {
            Environment.DEVELOPMENT: 30,
            Environment.STAGING: 90,
            Environment.PRODUCTION: 365     # 1 year for compliance
        }[self.environment]
    
    @property
    def enable_ip_whitelist(self) -> bool:
        """Whether IP whitelisting is enabled for admin endpoints."""
        return self.environment == Environment.PRODUCTION
    
    @property
    def allowed_admin_ips(self) -> List[str]:
        """IP addresses allowed for admin endpoints."""
        if not self.enable_ip_whitelist:
            return []
        
        # In production, configure via environment variables
        return [
            # Example: "10.0.0.0/8", "203.0.113.0/24"
        ]
    
    @property
    def security_headers_enabled(self) -> bool:
        """Whether to enable security headers."""
        return True  # Always enabled
    
    @property
    def hsts_max_age_seconds(self) -> int:
        """HSTS max-age in seconds."""
        return {
            Environment.DEVELOPMENT: 3600,          # 1 hour
            Environment.STAGING: 86400,             # 1 day
            Environment.PRODUCTION: 63072000        # 2 years
        }[self.environment]
    
    @property
    def enable_blockchain_audit(self) -> bool:
        """Whether to enable blockchain-based audit trail."""
        return False  # Not yet implemented
    
    @property
    def enable_data_encryption_at_rest(self) -> bool:
        """Whether to encrypt sensitive data at rest."""
        return self.environment == Environment.PRODUCTION
    
    def get_config_summary(self) -> dict:
        """
        Get summary of all security configuration.
        
        Returns:
            Dictionary of all security settings
        """
        return {
            "environment": self.environment.value,
            "require_https": self.require_https,
            "token_expiry_minutes": self.token_expiry_minutes,
            "refresh_token_expiry_days": self.refresh_token_expiry_days,
            "allowed_origins": self.allowed_origins,
            "enable_debug_endpoints": self.enable_debug_endpoints,
            "enable_swagger_ui": self.enable_swagger_ui,
            "log_level": self.log_level,
            "max_login_attempts": self.max_login_attempts,
            "lockout_duration_minutes": self.lockout_duration_minutes,
            "password_min_length": self.password_min_length,
            "rate_limit_enabled": self.rate_limit_enabled,
            "audit_log_retention_days": self.audit_log_retention_days,
            "enable_ip_whitelist": self.enable_ip_whitelist,
            "hsts_max_age_seconds": self.hsts_max_age_seconds
        }
