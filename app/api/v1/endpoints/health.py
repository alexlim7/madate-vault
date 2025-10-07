"""
Health check endpoints for Kubernetes/GCP readiness.

Provides comprehensive health and readiness checks including:
- Database connectivity
- Configuration validation
- External dependencies (KMS, secrets, webhooks)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/healthz")
async def health_check():
    """
    Basic liveness check endpoint.
    
    Returns HTTP 200 if the service is running.
    Used by Kubernetes liveness probes.
    
    This is a lightweight check that only verifies the service is responsive.
    """
    return {
        "status": "healthy",
        "service": "mandate-vault-api",
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/readyz")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive readiness check endpoint.
    
    Verifies all critical dependencies are available:
    - Database connectivity
    - Required configuration
    - Webhook signer configuration (if webhooks enabled)
    - ACP configuration (if ACP enabled)
    
    Returns HTTP 200 if service is ready to accept traffic.
    Returns HTTP 503 if service is not ready.
    
    Used by Kubernetes readiness probes.
    """
    checks = {}
    all_passed = True
    
    # 1. Database check
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = {"status": "connected", "healthy": True}
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        checks["database"] = {"status": "failed", "healthy": False, "error": str(e)}
        all_passed = False
    
    # 2. Configuration checks
    config_checks = {}
    
    # Check SECRET_KEY is configured
    if settings.secret_key and len(settings.secret_key) >= 32:
        config_checks["secret_key"] = {"status": "configured", "healthy": True}
    else:
        config_checks["secret_key"] = {"status": "missing_or_too_short", "healthy": False}
        all_passed = False
    
    # Check DATABASE_URL is configured
    if settings.database_url:
        config_checks["database_url"] = {"status": "configured", "healthy": True}
    else:
        config_checks["database_url"] = {"status": "using_default", "healthy": True}
    
    checks["configuration"] = config_checks
    
    # 3. ACP configuration checks (if enabled)
    if settings.acp_enable:
        acp_checks = {}
        
        # Check webhook secret if webhooks are expected
        if settings.acp_webhook_secret:
            if len(settings.acp_webhook_secret) >= 32:
                acp_checks["webhook_secret"] = {"status": "configured", "healthy": True}
            else:
                acp_checks["webhook_secret"] = {"status": "too_short", "healthy": False}
                all_passed = False
        else:
            acp_checks["webhook_secret"] = {"status": "not_configured", "healthy": True, "note": "Webhooks will not be signature-verified"}
        
        # Check PSP allowlist
        allowlist = settings.get_acp_psp_allowlist()
        if allowlist:
            acp_checks["psp_allowlist"] = {
                "status": "configured",
                "healthy": True,
                "allowed_psps": len(allowlist)
            }
        else:
            acp_checks["psp_allowlist"] = {
                "status": "not_configured",
                "healthy": True,
                "note": "All PSPs allowed"
            }
        
        checks["acp_protocol"] = {
            "enabled": True,
            "checks": acp_checks
        }
    else:
        checks["acp_protocol"] = {"enabled": False, "healthy": True}
    
    # 4. KMS/Secret Manager check (if configured)
    kms_checks = {}
    if settings.kms_key_id:
        # KMS is configured
        kms_checks["kms_configured"] = True
        kms_checks["key_id"] = settings.kms_key_id[:20] + "..."  # Truncate for security
        # Note: We don't actually test KMS connectivity here to avoid latency
        # That should be done in a separate deep health check endpoint
    else:
        kms_checks["kms_configured"] = False
    
    checks["kms"] = kms_checks
    
    # 5. Webhook configuration check
    webhook_checks = {}
    if settings.webhook_timeout and settings.webhook_max_retries:
        webhook_checks["timeout"] = settings.webhook_timeout
        webhook_checks["max_retries"] = settings.webhook_max_retries
        webhook_checks["healthy"] = True
    else:
        webhook_checks["healthy"] = False
        all_passed = False
    
    checks["webhooks"] = webhook_checks
    
    # Overall status
    if all_passed:
        return {
            "status": "ready",
            "service": "mandate-vault-api",
            "version": settings.app_version,
            "environment": settings.environment,
            "checks": checks
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "service": "mandate-vault-api",
                "checks": checks
            }
        )


@router.get("/healthz/deep")
async def deep_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Deep health check with comprehensive dependency validation.
    
    This endpoint performs more extensive checks and should NOT be used
    for Kubernetes probes (too slow). Use /healthz and /readyz instead.
    
    Checks:
    - Database query performance
    - Table accessibility
    - Configuration completeness
    """
    import time
    checks = {}
    
    # Database performance check
    try:
        start = time.time()
        result = await db.execute(text("SELECT COUNT(*) FROM authorizations"))
        auth_count = result.scalar()
        duration = time.time() - start
        
        checks["database"] = {
            "status": "healthy",
            "authorization_count": auth_count,
            "query_duration_ms": round(duration * 1000, 2),
            "healthy": duration < 1.0  # Query should be under 1 second
        }
    except Exception as e:
        checks["database"] = {
            "status": "failed",
            "error": str(e),
            "healthy": False
        }
    
    # Check authorization table structure
    try:
        result = await db.execute(
            text("SELECT protocol, COUNT(*) as count FROM authorizations GROUP BY protocol")
        )
        protocol_counts = {row[0]: row[1] for row in result.fetchall()}
        
        checks["authorization_protocols"] = {
            "ap2_count": protocol_counts.get('AP2', 0),
            "acp_count": protocol_counts.get('ACP', 0),
            "healthy": True
        }
    except Exception as e:
        checks["authorization_protocols"] = {
            "status": "failed",
            "error": str(e),
            "healthy": False
        }
    
    return {
        "status": "healthy",
        "service": "mandate-vault-api",
        "checks": checks,
        "timestamp": time.time()
    }


