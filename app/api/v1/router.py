"""
Main API router for v1 endpoints.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    mandates, 
    authorizations,  # NEW: Multi-protocol endpoint
    audit, 
    health, 
    customers, 
    admin, 
    webhooks, 
    alerts, 
    auth, 
    users, 
    metrics,
    acp_webhooks  # ACP webhook handlers
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Authorization endpoints (multi-protocol: AP2 + ACP)
api_router.include_router(authorizations.router, prefix="/authorizations", tags=["authorizations"])

# ACP webhook endpoints (incoming events from ACP systems)
api_router.include_router(acp_webhooks.router, prefix="/acp", tags=["acp-webhooks"])

# Legacy mandate endpoints (AP2 only, deprecated)
api_router.include_router(mandates.router, prefix="/mandates", tags=["mandates (deprecated)"])

api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, tags=["monitoring"])
