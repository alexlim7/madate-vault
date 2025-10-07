"""
Mandate API endpoints.

⚠️ DEPRECATED: These endpoints are maintained for backward compatibility only.

USE /api/v1/authorizations ENDPOINTS FOR NEW INTEGRATIONS.

The /mandates endpoints only support AP2 (JWT-VC) protocol.
The /authorizations endpoints support both AP2 and ACP protocols.

Migration Path:
- POST /mandates → POST /authorizations with protocol='AP2'
- GET /mandates/{id} → GET /authorizations/{id}
- POST /mandates/search → POST /authorizations/search with protocol='AP2'

These endpoints will be removed in v2.0 (Q2 2026).
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_tenant_access, User, UserRole
from app.core.rate_limiting import create_endpoint_rate_limit
from app.schemas.mandate import MandateCreate, MandateResponse, MandateUpdate, MandateSearch, MandateSearchResponse
from app.services.mandate_service import MandateService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("/", response_model=MandateResponse, status_code=http_status.HTTP_201_CREATED, deprecated=True)
@create_endpoint_rate_limit("mandates", "create")
async def create_mandate(
    mandate_data: MandateCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MandateResponse:
    """
    Ingest a JWT-VC mandate (AP2 protocol only).
    
    ⚠️ **DEPRECATED**: Use `POST /api/v1/authorizations` instead.
    
    **Migration:**
    ```python
    # Old (deprecated)
    POST /api/v1/mandates
    {
        "vc_jwt": "eyJhbGc...",
        "tenant_id": "tenant-123"
    }
    
    # New (recommended)
    POST /api/v1/authorizations
    {
        "protocol": "AP2",
        "payload": {"vc_jwt": "eyJhbGc..."},
        "tenant_id": "tenant-123"
    }
    ```
    
    **Limitations:**
    - Only supports AP2 (JWT-VC) protocol
    - Cannot handle ACP delegated tokens
    - Will be removed in v2.0 (Q2 2026)
    
    **Use /authorizations for:**
    - Multi-protocol support (AP2 + ACP)
    - Advanced search capabilities
    - Evidence pack export
    - Unified audit trail
    """
    try:
        # Verify tenant access
        if current_user.tenant_id != mandate_data.tenant_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        mandate_service = MandateService(db)
        
        # Extract request metadata for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Create mandate
        mandate = await mandate_service.create_mandate(
            vc_jwt=mandate_data.vc_jwt,
            tenant_id=mandate_data.tenant_id,
            retention_days=mandate_data.retention_days,
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return MandateResponse.model_validate(mandate)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/search", response_model=MandateSearchResponse)
@create_endpoint_rate_limit("mandates", "search")
async def search_mandates(
    request: Request,
    tenant_id: str = Query(..., description="Tenant ID for multi-tenancy"),
    issuer_did: Optional[str] = None,
    subject_did: Optional[str] = None,
    status: Optional[str] = None,
    scope: Optional[str] = None,
    expires_before: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MandateSearchResponse:
    """
    Filter mandates by issuer_did, subject_did, status, scope, expires_before.
    """
    try:
        from datetime import datetime
        from app.schemas.mandate import MandateStatus
        
        mandate_service = MandateService(db)
        
        # Parse expires_before if provided
        expires_before_dt = None
        if expires_before:
            try:
                expires_before_dt = datetime.fromisoformat(expires_before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid expires_before format. Use ISO format (e.g., 2024-12-31T23:59:59Z)"
                )
        
        # Create search parameters
        search_params = MandateSearch(
            issuer_did=issuer_did,
            subject_did=subject_did,
            status=MandateStatus(status) if status else None,
            scope=scope,
            expires_before=expires_before_dt,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset
        )
        
        # Search mandates
        result = await mandate_service.search_mandates(search_params, tenant_id)
        
        # Convert mandates to response format
        mandate_responses = [MandateResponse.model_validate(m) for m in result["mandates"]]
        
        return MandateSearchResponse(
            mandates=mandate_responses,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: str,
    tenant_id: str = Query(..., description="Tenant ID for multi-tenancy"),
    include_deleted: bool = False,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> MandateResponse:
    """
    Fetch mandate with verification result + metadata.
    """
    try:
        mandate_service = MandateService(db)
        audit_service = AuditService(db)
        
        # Get mandate
        mandate = await mandate_service.get_mandate_by_id(mandate_id, tenant_id, include_deleted)
        if not mandate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Mandate with ID {mandate_id} not found"
            )
        
        # Log audit event
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        await audit_service.log_event(
            mandate_id=mandate.id,
            event_type="READ",
            details={
                "user_id": None,
                "ip_address": client_ip,
                "user_agent": user_agent
            }
        )
        
        return MandateResponse.model_validate(mandate)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.patch("/{mandate_id}", response_model=MandateResponse)
async def update_mandate(
    mandate_id: str,
    tenant_id: str = Query(..., description="Tenant ID for multi-tenancy"),
    update_data: MandateUpdate = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> MandateResponse:
    """
    Update a mandate.
    """
    try:
        mandate_service = MandateService(db)
        
        # Extract request metadata for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        # Update mandate
        mandate = await mandate_service.update_mandate(
            mandate_id=mandate_id,
            tenant_id=tenant_id,
            update_data=update_data,
            user_id=None,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not mandate:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Mandate with ID {mandate_id} not found"
            )
        
        return MandateResponse.model_validate(mandate)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{mandate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def soft_delete_mandate(
    mandate_id: str,
    tenant_id: str = Query(..., description="Tenant ID for multi-tenancy"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a mandate.
    """
    try:
        mandate_service = MandateService(db)
        
        # Extract request metadata for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        # Soft delete mandate
        success = await mandate_service.soft_delete_mandate(
            mandate_id=mandate_id,
            tenant_id=tenant_id,
            user_id=None,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Mandate with ID {mandate_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{mandate_id}/restore", response_model=MandateResponse)
async def restore_mandate(
    mandate_id: str,
    tenant_id: str = Query(..., description="Tenant ID for multi-tenancy"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> MandateResponse:
    """
    Restore a soft-deleted mandate.
    """
    try:
        mandate_service = MandateService(db)
        
        # Extract request metadata for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        # Restore mandate
        success = await mandate_service.restore_mandate(
            mandate_id=mandate_id,
            tenant_id=tenant_id,
            user_id=None,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Mandate with ID {mandate_id} not found or not deleted"
            )
        
        # Get the restored mandate
        mandate = await mandate_service.get_mandate_by_id(mandate_id, tenant_id)
        
        return MandateResponse.model_validate(mandate)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
