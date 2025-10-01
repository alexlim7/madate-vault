"""
Monitoring middleware for request/response tracking.
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    get_logger
)

logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and record metrics."""
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Normalize endpoint (remove IDs for better grouping)
        endpoint = self._normalize_endpoint(path)
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Record successful request
            duration = time.time() - start_time
            
            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # Log request
            logger.info(
                "http_request",
                method=method,
                path=path,
                status_code=status_code,
                duration_seconds=round(duration, 3),
                user_agent=request.headers.get("user-agent", "unknown"),
                client_ip=request.client.host if request.client else "unknown"
            )
            
            return response
            
        except Exception as e:
            # Record error
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500
            ).inc()
            
            logger.error(
                "http_request_error",
                method=method,
                path=path,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(duration, 3)
            )
            
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path by removing IDs.
        
        Args:
            path: Request path
            
        Returns:
            Normalized path
        """
        import re
        
        # Replace UUIDs with {id}
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+/', '/{id}/', path)
        
        return path


def setup_monitoring_middleware(app: ASGIApp):
    """Setup monitoring middleware on the application."""
    app.add_middleware(MonitoringMiddleware)
    logger.info("Monitoring middleware configured")

