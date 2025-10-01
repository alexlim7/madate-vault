"""
FastAPI application for mandate vault backend.
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.rate_limiting import limiter
from app.core.security_middleware import setup_security_middleware, setup_request_logging
from app.core.request_security import RequestSecurityMiddleware
from app.core.monitoring_middleware import setup_monitoring_middleware
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start background services
    import asyncio
    from app.core.cleanup_service import session_cleanup_service
    from app.workers.webhook_worker import webhook_worker
    
    cleanup_task = asyncio.create_task(session_cleanup_service.run_periodic_cleanup())
    
    # Start webhook worker
    await webhook_worker.start()
    
    yield
    
    # Shutdown
    session_cleanup_service.stop()
    webhook_worker.stop()
    
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Mandate Vault API",
    description="A secure FastAPI backend for managing JWT-VC mandates",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

# Setup security middleware
setup_security_middleware(app)
setup_request_logging(app)

# Setup monitoring middleware
setup_monitoring_middleware(app)

# Add request security middleware (request size limits, etc.)
app.add_middleware(RequestSecurityMiddleware)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Include health endpoints directly on the root
from app.api.v1.endpoints import health
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Mandate Vault API", "version": "1.0.0"}
