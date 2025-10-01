"""
Rate limiting middleware and configuration.
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Optional

from app.core.config import settings

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimitConfig:
    """Rate limiting configuration."""
    
    def __init__(self):
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis client for rate limiting."""
        try:
            # In production, use Redis for distributed rate limiting
            # For demo purposes, we'll use in-memory storage
            self.redis_client = None
        except Exception:
            # Fallback to in-memory storage
            self.redis_client = None
    
    def get_storage_uri(self) -> str:
        """Get Redis storage URI."""
        if self.redis_client:
            return "redis://localhost:6379"
        return "memory://"


# Initialize rate limiter
rate_limit_config = RateLimitConfig()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=rate_limit_config.get_storage_uri(),
    default_limits=["100/minute"]  # Default rate limit
)


def create_rate_limit_exceeded_handler():
    """Create custom rate limit exceeded handler."""
    
    def handler(request: Request, exc: RateLimitExceeded):
        """Handle rate limit exceeded."""
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Rate limit exceeded: {exc.detail}",
                "retry_after": getattr(exc, 'retry_after', 60)
            }
        )
        response.headers["Retry-After"] = str(getattr(exc, 'retry_after', 60))
        return response
    
    return handler


# Rate limiting decorators for different endpoints
def auth_rate_limit():
    """Rate limit for authentication endpoints."""
    return limiter.limit("5/minute", key_func=get_remote_address)


def api_rate_limit():
    """Rate limit for general API endpoints."""
    return limiter.limit("100/minute", key_func=get_remote_address)


def strict_rate_limit():
    """Strict rate limit for sensitive operations."""
    return limiter.limit("10/minute", key_func=get_remote_address)


def admin_rate_limit():
    """Rate limit for admin endpoints."""
    return limiter.limit("200/minute", key_func=get_remote_address)


# Per-endpoint rate limits
RATE_LIMITS = {
    "auth": {
        "login": "5/minute",
        "refresh": "10/minute",
        "verify": "30/minute"
    },
    "mandates": {
        "create": "20/minute",
        "search": "100/minute",
        "get": "200/minute",
        "update": "10/minute",
        "verify": "30/minute"
    },
    "webhooks": {
        "create": "10/minute",
        "list": "50/minute",
        "deliveries": "100/minute",
        "retry": "5/minute"
    },
    "alerts": {
        "create": "20/minute",
        "list": "100/minute",
        "update": "50/minute"
    },
    "admin": {
        "cleanup": "1/hour",
        "status": "100/minute"
    }
}


def get_rate_limit_for_endpoint(endpoint_name: str, operation: str) -> str:
    """Get rate limit for specific endpoint and operation."""
    return RATE_LIMITS.get(endpoint_name, {}).get(operation, "100/minute")


def create_endpoint_rate_limit(endpoint_name: str, operation: str):
    """Create rate limit decorator for specific endpoint."""
    rate_limit = get_rate_limit_for_endpoint(endpoint_name, operation)
    return limiter.limit(rate_limit, key_func=get_remote_address)
