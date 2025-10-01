"""
Security-focused logging for Mandate Vault.
Logs security events for monitoring and audit purposes.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json


# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)

# Add handler
if not security_logger.handlers:
    security_logger.addHandler(console_handler)


class SecurityLogger:
    """
    Security event logger.
    
    Logs important security events:
    - Authentication success/failure
    - Authorization denials
    - Suspicious activity
    - Account lockouts
    - Token operations
    """
    
    @staticmethod
    def log_auth_success(
        user_id: str,
        email: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log successful authentication.
        
        Args:
            user_id: User ID
            email: User email
            ip_address: Client IP address
            user_agent: Client user agent string
        """
        security_logger.info(
            "AUTH_SUCCESS",
            extra={
                "event_type": "auth_success",
                "user_id": user_id,
                "email": email,
                "ip_address": ip_address,
                "user_agent": user_agent or "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_auth_failure(
        email: str,
        ip_address: str,
        reason: str,
        attempts_remaining: Optional[int] = None
    ) -> None:
        """
        Log failed authentication attempt.
        
        Args:
            email: Attempted email
            ip_address: Client IP address
            reason: Failure reason
            attempts_remaining: Number of attempts before lockout
        """
        security_logger.warning(
            "AUTH_FAILURE",
            extra={
                "event_type": "auth_failure",
                "email": email,
                "ip_address": ip_address,
                "reason": reason,
                "attempts_remaining": attempts_remaining,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_account_lockout(
        email: str,
        ip_address: str,
        lockout_duration_seconds: int,
        failed_attempts: int
    ) -> None:
        """
        Log account lockout.
        
        Args:
            email: Locked out email
            ip_address: Client IP address
            lockout_duration_seconds: Lockout duration
            failed_attempts: Number of failed attempts
        """
        security_logger.error(
            "ACCOUNT_LOCKOUT",
            extra={
                "event_type": "account_lockout",
                "email": email,
                "ip_address": ip_address,
                "lockout_duration_seconds": lockout_duration_seconds,
                "failed_attempts": failed_attempts,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_permission_denied(
        user_id: str,
        resource: str,
        action: str,
        reason: str
    ) -> None:
        """
        Log permission denial.
        
        Args:
            user_id: User ID
            resource: Resource being accessed
            action: Action attempted
            reason: Denial reason
        """
        security_logger.warning(
            "PERMISSION_DENIED",
            extra={
                "event_type": "permission_denied",
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_suspicious_activity(
        user_id: Optional[str],
        activity_type: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log suspicious activity.
        
        Args:
            user_id: User ID (if known)
            activity_type: Type of suspicious activity
            details: Activity details
            ip_address: Client IP address
        """
        security_logger.error(
            "SUSPICIOUS_ACTIVITY",
            extra={
                "event_type": "suspicious_activity",
                "user_id": user_id or "unknown",
                "activity_type": activity_type,
                "details": json.dumps(details),
                "ip_address": ip_address or "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_token_created(user_id: str, token_type: str) -> None:
        """
        Log token creation.
        
        Args:
            user_id: User ID
            token_type: Token type (access/refresh)
        """
        security_logger.info(
            "TOKEN_CREATED",
            extra={
                "event_type": "token_created",
                "user_id": user_id,
                "token_type": token_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_token_refreshed(user_id: str) -> None:
        """
        Log token refresh.
        
        Args:
            user_id: User ID
        """
        security_logger.info(
            "TOKEN_REFRESHED",
            extra={
                "event_type": "token_refreshed",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_token_invalid(reason: str, ip_address: Optional[str] = None) -> None:
        """
        Log invalid token usage.
        
        Args:
            reason: Reason token is invalid
            ip_address: Client IP address
        """
        security_logger.warning(
            "TOKEN_INVALID",
            extra={
                "event_type": "token_invalid",
                "reason": reason,
                "ip_address": ip_address or "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_rate_limit_exceeded(
        identifier: str,
        endpoint: str,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log rate limit exceeded.
        
        Args:
            identifier: Rate limit identifier (user_id, ip, etc.)
            endpoint: Endpoint that was rate limited
            ip_address: Client IP address
        """
        security_logger.warning(
            "RATE_LIMIT_EXCEEDED",
            extra={
                "event_type": "rate_limit_exceeded",
                "identifier": identifier,
                "endpoint": endpoint,
                "ip_address": ip_address or "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_password_changed(user_id: str, ip_address: str) -> None:
        """
        Log password change.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
        """
        security_logger.info(
            "PASSWORD_CHANGED",
            extra={
                "event_type": "password_changed",
                "user_id": user_id,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    @staticmethod
    def log_data_access(
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> None:
        """
        Log data access (for sensitive resources).
        
        Args:
            user_id: User ID
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action performed (read/write/delete)
        """
        security_logger.info(
            "DATA_ACCESS",
            extra={
                "event_type": "data_access",
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Global instance
security_log = SecurityLogger()
