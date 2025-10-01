"""
Health check endpoints for Kubernetes/GCP readiness.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter()


@router.get("/healthz")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {"status": "healthy", "service": "mandate-vault-api"}


@router.get("/readyz")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint that verifies database connectivity.
    """
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "ready",
            "service": "mandate-vault-api",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


