"""
Authorization API endpoints (multi-protocol).

New endpoint that supports both AP2 and ACP protocols.
This is the modern replacement for the legacy /mandates endpoint.
"""
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status as http_status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_active_user, User, UserRole
from app.core.rate_limiting import create_endpoint_rate_limit
from app.core.config import settings
from app.core.monitoring import (
    authorizations_created_total,
    authorizations_verified_total,
    authorizations_revoked_total,
    evidence_packs_exported_total,
    evidence_pack_export_duration_seconds
)
import time
from app.schemas.authorization import (
    AuthorizationCreate,
    AuthorizationResponse,
    AuthorizationSearchRequest,
    AuthorizationSearchResponse
)
from app.models.authorization import Authorization, ProtocolType
from app.services.audit_service import AuditService
from app.services.verification_dispatcher import verify_authorization
from app.protocols.acp.schemas import ACPDelegatedToken
from app.protocols.acp.verify import verify_acp_token
from app.services.verification_service import verification_service

router = APIRouter()


@router.post("/", response_model=AuthorizationResponse, status_code=http_status.HTTP_201_CREATED)
@create_endpoint_rate_limit("authorizations", "create")
async def create_authorization(
    auth_data: AuthorizationCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationResponse:
    """
    Create a new authorization (multi-protocol).
    
    Supports both AP2 (JWT-VC) and ACP protocols.
    
    **AP2 Payload Format:**
    ```json
    {
        "protocol": "AP2",
        "payload": {
            "vc_jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        },
        "tenant_id": "tenant-123"
    }
    ```
    
    **ACP Payload Format:**
    ```json
    {
        "protocol": "ACP",
        "payload": {
            "token_id": "acp-123",
            "psp_id": "psp-456",
            "merchant_id": "merchant-789",
            "max_amount": "5000.00",
            "currency": "USD",
            "expires_at": "2026-01-01T00:00:00Z",
            "constraints": {"category": "retail"}
        },
        "tenant_id": "tenant-123"
    }
    ```
    """
    try:
        # Verify tenant access
        if current_user.tenant_id != auth_data.tenant_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Extract request metadata for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Route based on protocol
        if auth_data.protocol == ProtocolType.AP2:
            authorization = await _process_ap2_authorization(
                auth_data=auth_data,
                db=db,
                current_user=current_user,
                client_ip=client_ip,
                user_agent=user_agent
            )
        elif auth_data.protocol == ProtocolType.ACP:
            authorization = await _process_acp_authorization(
                auth_data=auth_data,
                db=db,
                current_user=current_user,
                client_ip=client_ip,
                user_agent=user_agent
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported protocol: {auth_data.protocol}"
            )
        
        # Record metrics
        authorizations_created_total.labels(
            protocol=authorization.protocol,
            status=authorization.status,
            tenant_id=authorization.tenant_id
        ).inc()
        
        return AuthorizationResponse.model_validate(authorization)
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from ACP checks)
        raise
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


async def _process_ap2_authorization(
    auth_data: AuthorizationCreate,
    db: AsyncSession,
    current_user: User,
    client_ip: Optional[str],
    user_agent: Optional[str]
) -> Authorization:
    """
    Process AP2 (JWT-VC) authorization.
    
    Args:
        auth_data: Authorization creation request
        db: Database session
        current_user: Current authenticated user
        client_ip: Client IP address
        user_agent: User agent string
    
    Returns:
        Created Authorization object
    """
    audit_service = AuditService(db)
    
    # Extract vc_jwt from payload
    vc_jwt = auth_data.payload.get('vc_jwt')
    if not vc_jwt:
        raise ValueError("AP2 payload must contain 'vc_jwt' field")
    
    # Verify using AP2 verifier
    verification_result = await verification_service.verify_mandate(vc_jwt)
    
    # Log verification attempt
    await audit_service.log_event(
        mandate_id=None,
        event_type="VERIFIED",
        details={
            "protocol": "AP2",
            "verification_status": verification_result.status.value,
            "verification_reason": verification_result.reason,
            "verification_details": verification_result.to_dict(),
            "user_id": current_user.id,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    # Check if verification passed
    if not verification_result.is_valid:
        raise ValueError(f"AP2 verification failed: {verification_result.reason}")
    
    # Extract data from verification result
    details = verification_result.details
    
    # Parse amount and currency from AP2 format (e.g., "5000.00 USD")
    amount_limit = None
    currency = None
    amount_str = details.get('amount_limit', '')
    
    if amount_str and isinstance(amount_str, str):
        parts = amount_str.split()
        if len(parts) >= 1:
            try:
                amount_limit = Decimal(parts[0].replace(',', ''))
            except:
                pass
        if len(parts) >= 2:
            currency = parts[1]
    
    # Parse expiration
    expires_at = None
    if details.get('expires_at'):
        try:
            expires_at = datetime.fromtimestamp(details['expires_at'], tz=timezone.utc)
        except:
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    else:
        # Default: 1 year
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    
    # Create Authorization object
    authorization = Authorization(
        protocol='AP2',
        issuer=details.get('issuer_did', 'unknown'),
        subject=details.get('subject_did', 'unknown'),
        scope={'scope': details.get('scope')} if details.get('scope') else {},
        amount_limit=amount_limit,
        currency=currency,
        expires_at=expires_at,
        status='VALID',
        raw_payload={
            'vc_jwt': vc_jwt,
            'issuer_did': details.get('issuer_did'),
            'subject_did': details.get('subject_did'),
            'scope': details.get('scope'),
            'amount_limit': amount_str,
            'original_format': 'jwt-vc'
        },
        tenant_id=auth_data.tenant_id,
        verification_status=verification_result.status.value,
        verification_reason=verification_result.reason,
        verification_details=verification_result.to_dict(),
        verified_at=datetime.now(timezone.utc),
        retention_days=auth_data.retention_days,
        created_by=current_user.id
    )
    
    # Save to database
    db.add(authorization)
    await db.commit()
    await db.refresh(authorization)
    
    # Log creation event
    await audit_service.log_event(
        mandate_id=str(authorization.id),
        event_type="CREATED",
        details={
            "protocol": "AP2",
            "issuer": authorization.issuer,
            "subject": authorization.subject,
            "scope": authorization.scope,
            "amount_limit": str(authorization.amount_limit) if authorization.amount_limit else None,
            "currency": authorization.currency,
            "verification_status": authorization.verification_status,
            "verification_reason": authorization.verification_reason,
            "user_id": current_user.id,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    return authorization


async def _process_acp_authorization(
    auth_data: AuthorizationCreate,
    db: AsyncSession,
    current_user: User,
    client_ip: Optional[str],
    user_agent: Optional[str]
) -> Authorization:
    """
    Process ACP authorization.
    
    Args:
        auth_data: Authorization creation request
        db: Database session
        current_user: Current authenticated user
        client_ip: Client IP address
        user_agent: User agent string
    
    Returns:
        Created Authorization object
        
    Raises:
        HTTPException: If ACP is disabled or PSP not in allowlist
    """
    # Check if ACP is enabled
    if not settings.acp_enable:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="ACP protocol is disabled on this server"
        )
    
    audit_service = AuditService(db)
    
    # Parse payload into ACPDelegatedToken
    try:
        # Convert Pydantic model to dict if needed
        payload_dict = auth_data.payload
        if hasattr(payload_dict, 'model_dump'):
            payload_dict = payload_dict.model_dump()
        elif hasattr(payload_dict, 'dict'):
            payload_dict = payload_dict.dict()
        
        acp_token = ACPDelegatedToken.from_dict(payload_dict)
    except Exception as e:
        raise ValueError(f"Invalid ACP token format: {str(e)}")
    
    # Check PSP allowlist if configured
    if not settings.is_acp_psp_allowed(acp_token.psp_id):
        allowlist = settings.get_acp_psp_allowlist()
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=f"PSP '{acp_token.psp_id}' is not in the allowlist. Allowed PSPs: {', '.join(allowlist)}"
        )
    
    # Verify ACP token
    verification_result = verify_acp_token(acp_token)
    
    # Log verification attempt
    await audit_service.log_event(
        mandate_id=None,
        event_type="VERIFIED",
        details={
            "protocol": "ACP",
            "verification_status": verification_result.status.value,
            "verification_reason": verification_result.reason,
            "verification_details": verification_result.to_dict(),
            "user_id": current_user.id,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    # Check if verification passed
    if not verification_result.is_valid:
        raise ValueError(f"ACP verification failed: {verification_result.reason}")
    
    # Create Authorization object from verified ACP token
    # Handle constraints - could be a Pydantic model or dict
    constraints_dict = {}
    if acp_token.constraints:
        if hasattr(acp_token.constraints, 'model_dump'):
            constraints_dict = acp_token.constraints.model_dump()
        elif hasattr(acp_token.constraints, 'dict'):
            constraints_dict = acp_token.constraints.dict()
        elif isinstance(acp_token.constraints, dict):
            constraints_dict = acp_token.constraints
    
    authorization = Authorization(
        protocol='ACP',
        issuer=acp_token.psp_id,
        subject=acp_token.merchant_id,
        scope={'constraints': constraints_dict} if constraints_dict else {},
        amount_limit=acp_token.max_amount,
        currency=acp_token.currency,
        expires_at=acp_token.expires_at,
        status='VALID',
        raw_payload=acp_token.model_dump(mode='json'),  # JSON-serializable
        tenant_id=auth_data.tenant_id,
        verification_status=verification_result.status.value,
        verification_reason=verification_result.reason,
        verification_details=json.loads(json.dumps(verification_result.to_dict(), default=str)),  # Ensure JSON-serializable
        verified_at=datetime.now(timezone.utc),
        retention_days=auth_data.retention_days,
        created_by=current_user.id
    )
    
    # Save to database
    db.add(authorization)
    await db.commit()
    await db.refresh(authorization)
    
    # Log creation event with protocol info
    await audit_service.log_event(
        mandate_id=str(authorization.id),
        event_type="CREATED",
        details={
            "protocol": "ACP",
            "psp_id": acp_token.psp_id,
            "merchant_id": acp_token.merchant_id,
            "max_amount": str(acp_token.max_amount),
            "currency": acp_token.currency,
            "constraints": acp_token.constraints,
            "token_id": acp_token.token_id,
            "verification_status": verification_result.status.value,
            "verification_reason": verification_result.reason,
            "user_id": current_user.id,
            "ip_address": client_ip,
            "user_agent": user_agent
        }
    )
    
    return authorization


@router.post("/{authorization_id}/verify")
@create_endpoint_rate_limit("authorizations", "verify")
async def verify_authorization_endpoint(
    authorization_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Re-verify an existing authorization.
    
    Re-runs verification on a stored authorization to check current validity.
    Useful for checking if an authorization has expired or been revoked.
    
    Supports both AP2 and ACP protocols.
    
    Returns:
        Uniform verification response with id, protocol, status, reason, etc.
    
    Example Response:
    ```json
    {
        "id": "auth-123",
        "protocol": "ACP",
        "status": "VALID",
        "reason": "ACP token verification successful",
        "expires_at": "2026-01-01T00:00:00Z",
        "amount_limit": 5000.00,
        "currency": "USD"
    }
    ```
    """
    from sqlalchemy import select
    
    # Load authorization from database
    result = await db.execute(
        select(Authorization).where(Authorization.id == authorization_id)
    )
    authorization = result.scalar_one_or_none()
    
    if not authorization:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Authorization {authorization_id} not found"
        )
    
    # Verify tenant access
    if current_user.tenant_id != authorization.tenant_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant's authorizations"
        )
    
    # Dispatch verification based on protocol
    try:
        if authorization.protocol == 'AP2':
            # Re-verify AP2 (JWT-VC)
            vc_jwt = authorization.raw_payload.get('vc_jwt')
            if not vc_jwt:
                raise ValueError("Stored AP2 authorization missing vc_jwt in raw_payload")
            
            verification_result = await verification_service.verify_mandate(vc_jwt)
            
        elif authorization.protocol == 'ACP':
            # Re-verify ACP token
            # Reconstruct ACPDelegatedToken from raw_payload
            acp_token = ACPDelegatedToken.from_dict(authorization.raw_payload)
            verification_result = verify_acp_token(acp_token)
            
        else:
            raise ValueError(f"Unknown protocol: {authorization.protocol}")
        
        # Update authorization status based on verification
        old_status = authorization.status
        new_status = verification_result.status.value
        
        # Map verification status to authorization status
        status_mapping = {
            'VALID': 'VALID',
            'ACTIVE': 'ACTIVE',
            'EXPIRED': 'EXPIRED',
            'REVOKED': 'REVOKED',
            'SIG_INVALID': 'REVOKED',
            'ISSUER_UNKNOWN': 'REVOKED',
            'INVALID_FORMAT': 'REVOKED',
            'SCOPE_INVALID': 'REVOKED',
            'MISSING_REQUIRED_FIELD': 'REVOKED'
        }
        
        authorization.status = status_mapping.get(new_status, 'REVOKED')
        authorization.verification_status = new_status
        authorization.verification_reason = verification_result.reason
        authorization.verification_details = verification_result.to_dict()
        authorization.verified_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(authorization)
        
        # Log verification event
        audit_service = AuditService(db)
        client_ip = request.client.host if request.client else None
        
        await audit_service.log_event(
            mandate_id=str(authorization.id),
            event_type="VERIFIED",
            details={
                "protocol": authorization.protocol,
                "verification_status": new_status,
                "verification_reason": verification_result.reason,
                "old_status": old_status,
                "new_status": authorization.status,
                "issuer": authorization.issuer,
                "subject": authorization.subject,
                "user_id": current_user.id,
                "ip_address": client_ip,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        # Record metrics
        authorizations_verified_total.labels(
            protocol=authorization.protocol,
            status=authorization.status
        ).inc()
        
        # Return uniform response
        return {
            "id": str(authorization.id),
            "protocol": authorization.protocol,
            "status": authorization.status,
            "reason": authorization.verification_reason,
            "expires_at": authorization.expires_at.isoformat() if authorization.expires_at else None,
            "amount_limit": float(authorization.amount_limit) if authorization.amount_limit else None,
            "currency": authorization.currency,
            "issuer": authorization.issuer,
            "subject": authorization.subject,
            "verified_at": authorization.verified_at.isoformat() if authorization.verified_at else None,
            "verification_details": authorization.verification_details
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}"
        )


@router.get("/{authorization_id}", response_model=AuthorizationResponse)
@create_endpoint_rate_limit("authorizations", "get")
async def get_authorization(
    authorization_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationResponse:
    """
    Get authorization by ID.
    
    Returns authorization regardless of protocol (AP2 or ACP).
    """
    from sqlalchemy import select
    
    result = await db.execute(
        select(Authorization).where(Authorization.id == authorization_id)
    )
    authorization = result.scalar_one_or_none()
    
    if not authorization:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Authorization {authorization_id} not found"
        )
    
    # Verify tenant access
    if current_user.tenant_id != authorization.tenant_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant's authorizations"
        )
    
    return AuthorizationResponse.model_validate(authorization)


@router.post("/search", response_model=AuthorizationSearchResponse)
@create_endpoint_rate_limit("authorizations", "search")
async def search_authorizations_post(
    search_request: AuthorizationSearchRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationSearchResponse:
    """
    Search authorizations (multi-protocol) - POST method.
    
    Supports advanced filtering:
    - Protocol type (AP2, ACP)
    - Standard fields (issuer, subject, status)
    - Date ranges (expires_before, expires_after, created_after)
    - Amount ranges (min_amount, max_amount, currency)
    - JSON path queries (scope->>'merchant', etc.)
    - Pagination & sorting
    
    Example:
    ```json
    {
        "tenant_id": "tenant-123",
        "protocol": "ACP",
        "status": "VALID",
        "expires_before": "2026-01-01T00:00:00Z",
        "scope_merchant": "merchant-acme",
        "min_amount": "1000.00",
        "currency": "USD",
        "limit": 50,
        "offset": 0,
        "sort_by": "created_at",
        "sort_order": "desc"
    }
    ```
    """
    return await _execute_search(search_request, current_user, db)


@router.get("/search", response_model=AuthorizationSearchResponse)
@create_endpoint_rate_limit("authorizations", "search_get")
async def search_authorizations_get(
    request: Request,
    tenant_id: str = Query(..., description="Tenant ID"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    issuer: Optional[str] = Query(None, description="Filter by issuer"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    status: Optional[str] = Query(None, description="Filter by status"),
    expires_before: Optional[str] = Query(None, description="ISO datetime"),
    expires_after: Optional[str] = Query(None, description="ISO datetime"),
    created_after: Optional[str] = Query(None, description="ISO datetime"),
    min_amount: Optional[str] = Query(None, description="Minimum amount"),
    max_amount: Optional[str] = Query(None, description="Maximum amount"),
    currency: Optional[str] = Query(None, description="Currency code"),
    scope_merchant: Optional[str] = Query(None, description="Scope merchant filter"),
    scope_category: Optional[str] = Query(None, description="Scope category filter"),
    scope_item: Optional[str] = Query(None, description="Scope item filter"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationSearchResponse:
    """
    Search authorizations (multi-protocol) - GET method.
    
    Same filtering capabilities as POST /search, but via query parameters.
    Useful for simple queries and bookmarkable searches.
    """
    # Parse query parameters into search request
    search_params = {
        'tenant_id': tenant_id,
        'limit': limit,
        'offset': offset,
        'sort_by': sort_by,
        'sort_order': sort_order
    }
    
    # Optional parameters
    if protocol:
        search_params['protocol'] = protocol
    if issuer:
        search_params['issuer'] = issuer
    if subject:
        search_params['subject'] = subject
    if status:
        search_params['status'] = status
    if expires_before:
        search_params['expires_before'] = datetime.fromisoformat(expires_before.replace('Z', '+00:00'))
    if expires_after:
        search_params['expires_after'] = datetime.fromisoformat(expires_after.replace('Z', '+00:00'))
    if created_after:
        search_params['created_after'] = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
    if min_amount:
        search_params['min_amount'] = Decimal(min_amount)
    if max_amount:
        search_params['max_amount'] = Decimal(max_amount)
    if currency:
        search_params['currency'] = currency
    if scope_merchant:
        search_params['scope_merchant'] = scope_merchant
    if scope_category:
        search_params['scope_category'] = scope_category
    if scope_item:
        search_params['scope_item'] = scope_item
    
    search_request = AuthorizationSearchRequest(**search_params)
    return await _execute_search(search_request, current_user, db)


async def _execute_search(
    search_request: AuthorizationSearchRequest,
    current_user: User,
    db: AsyncSession
) -> AuthorizationSearchResponse:
    """
    Execute authorization search with advanced filters.
    
    Internal function used by both POST and GET search endpoints.
    """
    from sqlalchemy import select, and_, func, or_, desc, asc, cast, String
    from sqlalchemy.dialects.postgresql import JSONB
    
    # Verify tenant access
    if current_user.tenant_id != search_request.tenant_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )
    
    # Build filter conditions
    conditions = [
        Authorization.tenant_id == search_request.tenant_id,
        Authorization.deleted_at.is_(None)
    ]
    
    # Standard filters
    if search_request.protocol:
        conditions.append(Authorization.protocol == search_request.protocol.value)
    
    if search_request.issuer:
        conditions.append(Authorization.issuer == search_request.issuer)
    
    if search_request.subject:
        conditions.append(Authorization.subject == search_request.subject)
    
    if search_request.status:
        conditions.append(Authorization.status == search_request.status.value)
    
    # Date filters
    if search_request.expires_before:
        conditions.append(Authorization.expires_at < search_request.expires_before)
    
    if search_request.expires_after:
        conditions.append(Authorization.expires_at > search_request.expires_after)
    
    if search_request.created_after:
        conditions.append(Authorization.created_at > search_request.created_after)
    
    # Amount filters
    if search_request.min_amount is not None:
        conditions.append(Authorization.amount_limit >= search_request.min_amount)
    
    if search_request.max_amount is not None:
        conditions.append(Authorization.amount_limit <= search_request.max_amount)
    
    if search_request.currency:
        conditions.append(Authorization.currency == search_request.currency)
    
    # JSON path filters
    # These use PostgreSQL JSON operators (->>, ->) 
    # For SQLite, these will be ignored or handled differently
    
    if search_request.scope_merchant:
        # For ACP: scope->'constraints'->>'merchant'
        # For AP2: not applicable (AP2 doesn't have merchant in scope)
        conditions.append(
            Authorization.scope['constraints']['merchant'].astext == search_request.scope_merchant
        )
    
    if search_request.scope_category:
        # scope->'constraints'->>'category' or scope->>'scope' for AP2
        conditions.append(
            or_(
                Authorization.scope['constraints']['category'].astext == search_request.scope_category,
                Authorization.scope['scope'].astext.contains(search_request.scope_category)
            )
        )
    
    if search_request.scope_item:
        # scope->'constraints'->>'item'
        conditions.append(
            Authorization.scope['constraints']['item'].astext == search_request.scope_item
        )
    
    # Get total count
    count_query = select(func.count(Authorization.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Build main query with sorting
    query = select(Authorization).where(and_(*conditions))
    
    # Apply sorting
    sort_column = getattr(Authorization, search_request.sort_by)
    if search_request.sort_order == 'desc':
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    query = query.limit(search_request.limit).offset(search_request.offset)
    
    # Execute query
    result = await db.execute(query)
    authorizations = result.scalars().all()
    
    return AuthorizationSearchResponse(
        authorizations=[AuthorizationResponse.model_validate(auth) for auth in authorizations],
        total=total,
        limit=search_request.limit,
        offset=search_request.offset
    )


@router.delete("/{authorization_id}", response_model=AuthorizationResponse)
@create_endpoint_rate_limit("authorizations", "revoke")
async def revoke_authorization(
    authorization_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> AuthorizationResponse:
    """
    Revoke an authorization.
    
    Works for both AP2 and ACP protocols.
    """
    from sqlalchemy import select
    
    # Get authorization
    result = await db.execute(
        select(Authorization).where(Authorization.id == authorization_id)
    )
    authorization = result.scalar_one_or_none()
    
    if not authorization:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Authorization {authorization_id} not found"
        )
    
    # Verify tenant access
    if current_user.tenant_id != authorization.tenant_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant's authorizations"
        )
    
    # Revoke
    authorization.status = 'REVOKED'
    authorization.revoked_at = datetime.now(timezone.utc)
    authorization.revoke_reason = f"Revoked by user {current_user.id}"
    
    await db.commit()
    await db.refresh(authorization)
    
    # Log revocation
    audit_service = AuditService(db)
    client_ip = request.client.host if request.client else None
    
    await audit_service.log_event(
        mandate_id=str(authorization.id),
        event_type="REVOKED",
        details={
            "protocol": authorization.protocol,
            "issuer": authorization.issuer,
            "subject": authorization.subject,
            "reason": authorization.revoke_reason,
            "user_id": current_user.id,
            "ip_address": client_ip,
            "user_agent": request.headers.get("user-agent")
        }
    )
    
    # Record metrics
    authorizations_revoked_total.labels(
        protocol=authorization.protocol,
        tenant_id=authorization.tenant_id
    ).inc()
    
    return AuthorizationResponse.model_validate(authorization)


@router.get("/{authorization_id}/evidence-pack")
@create_endpoint_rate_limit("authorizations", "evidence_pack")
async def get_evidence_pack(
    authorization_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Generate and download evidence pack for an authorization.
    
    Returns a ZIP file containing:
    
    **For AP2 (JWT-VC):**
    - `vc_jwt.txt` - The JWT-VC credential token
    - `credential.json` - Structured credential data
    - `verification.json` - Verification results and status
    - `audit.json` - Complete audit trail
    - `summary.txt` - Human-readable summary
    
    **For ACP (Delegated Token):**
    - `token.json` - The delegated token data with raw payload
    - `verification.json` - Verification results and status
    - `audit.json` - Complete audit trail including usage events
    - `summary.txt` - Human-readable summary (token_id, max_amount, currency, expires_at, status)
    
    **Use Cases:**
    - Compliance and audit requirements
    - Legal evidence for authorization
    - Customer dispute resolution
    - Regulatory reporting
    
    Returns:
        ZIP file as streaming download
    
    Raises:
        404: Authorization not found
        403: Access denied to tenant
    """
    from app.services.evidence_service import EvidencePackService
    from sqlalchemy import select
    
    # Fetch authorization to check tenant access
    result = await db.execute(
        select(Authorization).where(Authorization.id == authorization_id)
    )
    authorization = result.scalar_one_or_none()
    
    if not authorization:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Authorization {authorization_id} not found"
        )
    
    # Verify tenant access
    if current_user.tenant_id != authorization.tenant_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant's authorizations"
        )
    
    # Generate evidence pack
    evidence_service = EvidencePackService(db)
    
    # Track export duration
    start_time = time.time()
    
    try:
        zip_buffer, filename = await evidence_service.generate_evidence_pack(authorization_id)
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating evidence pack: {str(e)}"
        )
    
    # Record metrics
    duration = time.time() - start_time
    evidence_pack_export_duration_seconds.labels(
        protocol=authorization.protocol
    ).observe(duration)
    
    evidence_packs_exported_total.labels(
        protocol=authorization.protocol,
        tenant_id=authorization.tenant_id
    ).inc()
    
    # Log evidence pack generation
    audit_service = AuditService(db)
    client_ip = request.client.host if request.client else None
    
    await audit_service.log_event(
        mandate_id=str(authorization.id),
        event_type="EXPORTED",
        details={
            "protocol": authorization.protocol,
            "export_type": "evidence_pack",
            "user_id": current_user.id,
            "user_email": current_user.email,
            "ip_address": client_ip,
            "filename": filename,
            "authorization_id": str(authorization.id),
            "issuer": authorization.issuer,
            "subject": authorization.subject,
            "status": authorization.status
        }
    )
    
    # Return ZIP file as streaming response
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

