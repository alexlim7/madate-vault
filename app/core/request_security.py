"""
Request security middleware for Mandate Vault.
Implements request size limits and other request-level security.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for request-level security."""
    
    # Maximum request size: 10MB
    MAX_REQUEST_SIZE = 10 * 1024 * 1024
    
    # Maximum URL length
    MAX_URL_LENGTH = 2048
    
    async def dispatch(self, request: Request, call_next):
        # Check request size
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "Request Entity Too Large",
                        "detail": f"Request size {content_length} bytes exceeds maximum {self.MAX_REQUEST_SIZE} bytes"
                    }
                )
        
        # Check URL length
        if len(str(request.url)) > self.MAX_URL_LENGTH:
            return JSONResponse(
                status_code=414,
                content={
                    "error": "URI Too Long",
                    "detail": f"URL length exceeds maximum {self.MAX_URL_LENGTH} characters"
                }
            )
        
        response = await call_next(request)
        return response


class SecureCookieHelper:
    """Helper class for setting secure cookies."""
    
    @staticmethod
    def set_secure_cookie(
        response: Response,
        key: str,
        value: str,
        max_age: int = 3600,
        path: str = "/",
        domain: str = None,
        httponly: bool = True,
        secure: bool = True,
        samesite: str = "strict"
    ):
        """
        Set a cookie with secure defaults.
        
        Args:
            response: FastAPI Response object
            key: Cookie name
            value: Cookie value
            max_age: Cookie lifetime in seconds (default: 1 hour)
            path: Cookie path (default: "/")
            domain: Cookie domain (default: None)
            httponly: Prevent JavaScript access (default: True)
            secure: Require HTTPS (default: True)
            samesite: SameSite policy (default: "strict")
        """
        response.set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            path=path,
            domain=domain,
            httponly=httponly,
            secure=secure,
            samesite=samesite
        )
