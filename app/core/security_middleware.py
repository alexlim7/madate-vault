"""
Security headers and CORS configuration.
"""
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from typing import List, Optional

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Additional security headers (Quick Win #3)
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-DNS-Prefetch-Control"] = "off"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        # Content Security Policy - Allow Swagger UI CDN in development and staging
        if settings.environment in ("development", "staging"):
            # Relaxed CSP for development/staging to allow Swagger UI from CDN
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.redoc.ly; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # Strict CSP for production
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        response.headers["Content-Security-Policy"] = csp
        
        # Strict Transport Security (HTTPS only) - Enhanced with preload
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class CORSSecurityMiddleware:
    """Secure CORS configuration."""
    
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get allowed CORS origins."""
        if settings.environment == "production":
            # In production, only allow specific domains
            return [
                "https://mandatevault.com",
                "https://app.mandatevault.com",
                "https://admin.mandatevault.com"
            ]
        elif settings.environment == "staging":
            # In staging, allow staging domains
            return [
                "https://staging.mandatevault.com",
                "https://staging-app.mandatevault.com"
            ]
        else:
            # In development, allow localhost
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ]
    
    @staticmethod
    def get_cors_methods() -> List[str]:
        """Get allowed CORS methods."""
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    
    @staticmethod
    def get_cors_headers() -> List[str]:
        """Get allowed CORS headers."""
        return [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Tenant-ID"
        ]


def setup_security_middleware(app: FastAPI):
    """Setup security middleware for the application."""
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add trusted host middleware
    if settings.environment == "production":
        allowed_hosts = [
            "mandatevault.com",
            "app.mandatevault.com",
            "admin.mandatevault.com",
            "mandate-vault.onrender.com",  # Render.com deployment
            "*.onrender.com"  # Allow all Render subdomains
        ]
    elif settings.environment == "staging":
        allowed_hosts = [
            "staging.mandatevault.com",
            "staging-app.mandatevault.com",
            "mandate-vault.onrender.com"
        ]
    else:
        allowed_hosts = ["*"]  # Development
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts
    )
    
    # Add CORS middleware
    cors_config = CORSSecurityMiddleware()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get_cors_origins(),
        allow_credentials=True,
        allow_methods=cors_config.get_cors_methods(),
        allow_headers=cors_config.get_cors_headers(),
        expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"]
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for security-focused request logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Log request details for security monitoring
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log suspicious patterns
        if self._is_suspicious_request(request):
            # In production, this would log to a security monitoring system
            print(f"SECURITY WARNING: Suspicious request from {client_ip}: {request.url}")
        
        response = await call_next(request)
        
        # Add security-related response headers
        response.headers["X-Request-ID"] = str(id(request))
        
        return response
    
    def _is_suspicious_request(self, request: Request) -> bool:
        """Detect suspicious request patterns."""
        user_agent = request.headers.get("user-agent", "").lower()
        path = str(request.url.path).lower()
        
        # Check for common attack patterns
        suspicious_patterns = [
            "sqlmap", "nikto", "nmap", "masscan",
            "bot", "crawler", "scanner", "exploit"
        ]
        
        # Check user agent
        if any(pattern in user_agent for pattern in suspicious_patterns):
            return True
        
        # Check for common attack paths
        attack_paths = [
            "/admin", "/wp-admin", "/phpmyadmin",
            "/.env", "/config", "/backup"
        ]
        
        if any(path.startswith(attack_path) for attack_path in attack_paths):
            return True
        
        return False


def setup_request_logging(app: FastAPI):
    """Setup request logging middleware."""
    app.add_middleware(RequestLoggingMiddleware)
