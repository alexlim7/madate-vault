"""
ACP Webhook endpoints.

Handles incoming webhook events from ACP authorization systems.

Supported Events:
- token.used: Log usage without changing authorization status
- token.revoked: Revoke the authorization and log the event

Security:
- HMAC-SHA256 signature verification via X-ACP-Signature header
- Idempotency via event_id deduplication

Example Payloads:

Token Used:
```json
{
    "event_id": "evt_abc123",
    "event_type": "token.used",
    "timestamp": "2025-10-01T12:00:00Z",
    "data": {
        "token_id": "acp-token-123",
        "amount": "50.00",
        "currency": "USD",
        "merchant_id": "merchant-acme",
        "transaction_id": "txn_xyz789",
        "metadata": {
            "item": "product-001",
            "category": "retail"
        }
    }
}
```

Token Revoked:
```json
{
    "event_id": "evt_def456",
    "event_type": "token.revoked",
    "timestamp": "2025-10-01T12:00:00Z",
    "data": {
        "token_id": "acp-token-123",
        "reason": "User requested revocation",
        "revoked_by": "user-123"
    }
}
```
"""
from typing import Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
import hmac
import hashlib
import json

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limiting import create_endpoint_rate_limit
from app.core.monitoring import (
    acp_webhook_events_received_total,
    acp_webhook_signature_failures_total
)
from app.models.acp_event import ACPEvent
from app.models.authorization import Authorization, AuthorizationStatus
from app.services.audit_service import AuditService

router = APIRouter()


class ACPWebhookPayload(BaseModel):
    """ACP webhook event payload."""
    event_id: str = Field(..., description="Unique event identifier for idempotency")
    event_type: str = Field(..., description="Event type (token.used, token.revoked)")
    timestamp: datetime = Field(..., description="Event timestamp")
    data: Dict[str, Any] = Field(..., description="Event-specific data")


def verify_acp_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature for ACP webhook.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from X-ACP-Signature header
        secret: ACP webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)


async def handle_token_used(
    event_data: Dict[str, Any],
    authorization: Authorization,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Handle token.used event.
    
    Logs the usage in audit log without changing the authorization status.
    
    Args:
        event_data: Event data containing amount, merchant_id, etc.
        authorization: The authorization being used
        db: Database session
        
    Returns:
        Response data
    """
    # Extract usage details
    amount = event_data.get('amount')
    currency = event_data.get('currency')
    transaction_id = event_data.get('transaction_id')
    metadata = event_data.get('metadata', {})
    
    # Create audit log entry
    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type="USED",
        details={
            "protocol": "ACP",
            "actor_id": "acp-system",
            "resource_type": "authorization",
            "resource_id": str(authorization.id),
            "action": "token_used",
            "token_id": event_data.get('token_id'),
            "amount": str(amount) if amount else None,
            "currency": currency,
            "transaction_id": transaction_id,
            "merchant_id": event_data.get('merchant_id'),
            "metadata": metadata,
            "tenant_id": authorization.tenant_id,
            "status": "SUCCESS",
            "reason": f"ACP token used for transaction {transaction_id}"
        }
    )
    
    return {
        "status": "processed",
        "event_type": "token.used",
        "authorization_id": str(authorization.id),
        "authorization_status": authorization.status,
        "message": "Token usage logged successfully"
    }


async def handle_token_revoked(
    event_data: Dict[str, Any],
    authorization: Authorization,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Handle token.revoked event.
    
    Sets authorization status to REVOKED and logs the event.
    
    Args:
        event_data: Event data containing revocation reason
        authorization: The authorization being revoked
        db: Database session
        
    Returns:
        Response data
    """
    # Extract revocation details
    reason = event_data.get('reason', 'Revoked by ACP system')
    revoked_by = event_data.get('revoked_by')
    
    # Update authorization status
    old_status = authorization.status
    authorization.status = AuthorizationStatus.REVOKED
    authorization.revoked_at = datetime.now(timezone.utc)
    authorization.revoke_reason = reason
    
    # Create audit log entry
    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type="REVOKED",
        details={
            "protocol": "ACP",
            "actor_id": revoked_by or "acp-system",
            "resource_type": "authorization",
            "resource_id": str(authorization.id),
            "action": "token_revoked",
            "token_id": event_data.get('token_id'),
            "old_status": old_status,
            "new_status": AuthorizationStatus.REVOKED.value,
            "reason": reason,
            "revoked_by": revoked_by,
            "tenant_id": authorization.tenant_id,
            "status": "SUCCESS"
        }
    )
    
    await db.commit()
    await db.refresh(authorization)
    
    return {
        "status": "processed",
        "event_type": "token.revoked",
        "authorization_id": str(authorization.id),
        "authorization_status": authorization.status,
        "message": f"Token revoked: {reason}"
    }


@router.post("/webhook", status_code=http_status.HTTP_200_OK)
@create_endpoint_rate_limit("acp_webhooks", "webhook")
async def receive_acp_webhook(
    request: Request,
    x_acp_signature: str = Header(None, alias="X-ACP-Signature"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Receive and process ACP webhook events.
    
    Supports:
    - **token.used**: Log usage without status change
    - **token.revoked**: Set status to REVOKED
    
    Security:
    - HMAC-SHA256 signature verification
    - Idempotency via event_id
    - PSP allowlist enforcement (if configured)
    
    Returns:
        Processing result with authorization status
        
    Raises:
        403: ACP disabled or PSP not allowed
        401: Invalid signature
        409: Duplicate event_id (idempotency)
        404: Authorization not found
        422: Unsupported event type
    """
    # Check if ACP is enabled
    if not settings.acp_enable:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="ACP protocol is disabled on this server"
        )
    
    # Get ACP webhook secret from settings
    acp_webhook_secret = settings.acp_webhook_secret
    
    # Read raw body for signature verification
    raw_body = await request.body()
    
    # Verify HMAC signature if secret is configured
    if acp_webhook_secret:
        if not x_acp_signature:
            acp_webhook_signature_failures_total.labels(reason="missing_signature").inc()
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-ACP-Signature header"
            )
        
        if not verify_acp_signature(raw_body, x_acp_signature, acp_webhook_secret):
            acp_webhook_signature_failures_total.labels(reason="invalid_signature").inc()
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Parse payload after signature verification
    try:
        payload_dict = json.loads(raw_body)
        webhook_payload = ACPWebhookPayload.model_validate(payload_dict)
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payload format: {str(e)}"
        )
    
    # Check for duplicate event (idempotency)
    existing_event = await db.execute(
        select(ACPEvent).where(ACPEvent.event_id == webhook_payload.event_id)
    )
    if existing_event.scalar_one_or_none():
        # Event already processed - return success (idempotent)
        return {
            "status": "already_processed",
            "event_id": webhook_payload.event_id,
            "message": "Event already processed (idempotency)"
        }
    
    # Extract token_id from event data
    token_id = webhook_payload.data.get('token_id')
    if not token_id:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing token_id in event data"
        )
    
    # Find authorization by token_id in raw_payload
    # Use database-agnostic approach - fetch all ACP authorizations and filter in Python
    result = await db.execute(
        select(Authorization).where(Authorization.protocol == 'ACP')
    )
    authorizations = result.scalars().all()
    
    # Filter by token_id in raw_payload (database-agnostic)
    authorization = None
    for auth in authorizations:
        if auth.raw_payload.get('token_id') == token_id:
            authorization = auth
            break
    
    if not authorization:
        # Create event record even if authorization not found
        acp_event = ACPEvent(
            event_id=webhook_payload.event_id,
            event_type=webhook_payload.event_type,
            token_id=token_id,
            authorization_id=None,
            payload=webhook_payload.model_dump(mode='json'),
            processing_status="FAILED",
            error_message=f"Authorization not found for token_id: {token_id}"
        )
        db.add(acp_event)
        await db.commit()
        
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Authorization not found for token_id: {token_id}"
        )
    
    # Check PSP allowlist if configured
    psp_id = authorization.issuer  # For ACP, issuer = psp_id
    if not settings.is_acp_psp_allowed(psp_id):
        allowlist = settings.get_acp_psp_allowlist()
        # Log rejected webhook
        acp_event = ACPEvent(
            event_id=webhook_payload.event_id,
            event_type=webhook_payload.event_type,
            token_id=token_id,
            authorization_id=str(authorization.id),
            payload=webhook_payload.model_dump(mode='json'),
            processing_status="FAILED",
            error_message=f"PSP '{psp_id}' not in allowlist"
        )
        db.add(acp_event)
        await db.commit()
        
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=f"PSP '{psp_id}' is not in the allowlist. Allowed PSPs: {', '.join(allowlist)}"
        )
    
    # Check event type before processing
    if webhook_payload.event_type not in ["token.used", "token.revoked"]:
        # Record failed event for unsupported type
        acp_event = ACPEvent(
            event_id=webhook_payload.event_id,
            event_type=webhook_payload.event_type,
            token_id=token_id,
            authorization_id=str(authorization.id),
            payload=webhook_payload.model_dump(mode='json'),
            processing_status="FAILED",
            error_message=f"Unsupported event type: {webhook_payload.event_type}"
        )
        db.add(acp_event)
        await db.commit()
        
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported event type: {webhook_payload.event_type}"
        )
    
    # Process event based on type
    try:
        if webhook_payload.event_type == "token.used":
            response_data = await handle_token_used(
                webhook_payload.data,
                authorization,
                db
            )
        else:  # token.revoked
            response_data = await handle_token_revoked(
                webhook_payload.data,
                authorization,
                db
            )
        
        # Record successful event processing
        acp_event = ACPEvent(
            event_id=webhook_payload.event_id,
            event_type=webhook_payload.event_type,
            token_id=token_id,
            authorization_id=str(authorization.id),
            payload=webhook_payload.model_dump(mode='json'),
            processing_status="SUCCESS"
        )
        db.add(acp_event)
        await db.commit()
        
        # Record metrics
        acp_webhook_events_received_total.labels(
            event_type=webhook_payload.event_type,
            status="success"
        ).inc()
        
        return {
            **response_data,
            "event_id": webhook_payload.event_id,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except IntegrityError as e:
        # Duplicate event_id (race condition)
        await db.rollback()
        return {
            "status": "already_processed",
            "event_id": webhook_payload.event_id,
            "message": "Event already processed (idempotency)"
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        
        # Record failed event processing
        try:
            acp_event = ACPEvent(
                event_id=webhook_payload.event_id,
                event_type=webhook_payload.event_type,
                token_id=token_id,
                authorization_id=str(authorization.id) if authorization else None,
                payload=webhook_payload.model_dump(mode='json'),
                processing_status="FAILED",
                error_message=str(e)
            )
            db.add(acp_event)
            await db.commit()
        except:
            pass  # Best effort logging
        
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/events/{event_id}", status_code=http_status.HTTP_200_OK)
async def get_acp_event(
    event_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get ACP event processing status.
    
    Useful for debugging and verifying event delivery.
    """
    result = await db.execute(
        select(ACPEvent).where(ACPEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Event not found: {event_id}"
        )
    
    return event.to_dict()

