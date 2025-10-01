"""
Webhook API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.webhook import (
    WebhookCreate, WebhookResponse, WebhookUpdate, 
    WebhookDeliverySearch, WebhookDeliverySearchResponse
)
from app.services.webhook_service import WebhookService
from app.models.webhook import Webhook, WebhookDelivery
import uuid

router = APIRouter()


@router.post("/", response_model=WebhookResponse, status_code=http_status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """
    Create a new webhook.
    """
    try:
        # Create webhook object
        from datetime import datetime
        now = datetime.utcnow()
        webhook = Webhook(
            id=str(uuid.uuid4()),  # Generate ID manually
            tenant_id=tenant_id,
            name=webhook_data.name,
            url=webhook_data.url,
            events=[event.value for event in webhook_data.events],
            secret=webhook_data.secret,
            is_active=True,  # Set default value
            max_retries=webhook_data.max_retries,
            retry_delay_seconds=webhook_data.retry_delay_seconds,
            timeout_seconds=webhook_data.timeout_seconds,
            created_at=now,  # Set timestamp manually
            updated_at=now   # Set timestamp manually
        )
        
        db.add(webhook)
        await db.commit()
        await db.refresh(webhook)
        
        return WebhookResponse.model_validate(webhook)
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webhook: {str(e)}"
        )


@router.get("/", response_model=list[WebhookResponse])
async def list_webhooks(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> list[WebhookResponse]:
    """
    List all webhooks for a tenant.
    """
    try:
        from sqlalchemy import select
        
        query = select(Webhook).where(Webhook.tenant_id == tenant_id)
        result = await db.execute(query)
        webhooks = result.scalars().all()
        
        return [WebhookResponse.model_validate(webhook) for webhook in webhooks]
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list webhooks: {str(e)}"
        )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """
    Get webhook by ID.
    """
    try:
        from sqlalchemy import select
        
        query = select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.tenant_id == tenant_id
        )
        result = await db.execute(query)
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        return WebhookResponse.model_validate(webhook)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook: {str(e)}"
        )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> WebhookResponse:
    """
    Update a webhook.
    """
    try:
        from sqlalchemy import select
        
        query = select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.tenant_id == tenant_id
        )
        result = await db.execute(query)
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Update fields
        if webhook_data.name is not None:
            webhook.name = webhook_data.name
        if webhook_data.url is not None:
            webhook.url = webhook_data.url
        if webhook_data.events is not None:
            webhook.events = [event.value for event in webhook_data.events]
        if webhook_data.secret is not None:
            webhook.secret = webhook_data.secret
        if webhook_data.is_active is not None:
            webhook.is_active = webhook_data.is_active
        if webhook_data.max_retries is not None:
            webhook.max_retries = webhook_data.max_retries
        if webhook_data.retry_delay_seconds is not None:
            webhook.retry_delay_seconds = webhook_data.retry_delay_seconds
        if webhook_data.timeout_seconds is not None:
            webhook.timeout_seconds = webhook_data.timeout_seconds
        
        await db.commit()
        await db.refresh(webhook)
        
        return WebhookResponse.model_validate(webhook)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update webhook: {str(e)}"
        )


@router.delete("/{webhook_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a webhook.
    """
    try:
        from sqlalchemy import select
        
        query = select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.tenant_id == tenant_id
        )
        result = await db.execute(query)
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        await db.delete(webhook)
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )


@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliverySearchResponse)
async def get_webhook_deliveries(
    webhook_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> WebhookDeliverySearchResponse:
    """
    Get webhook delivery history.
    """
    try:
        webhook_service = WebhookService(db)
        result = await webhook_service.get_webhook_deliveries(
            webhook_id=webhook_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        from app.schemas.webhook import WebhookDeliveryResponse
        deliveries = [WebhookDeliveryResponse.model_validate(d) for d in result["deliveries"]]
        
        return WebhookDeliverySearchResponse(
            deliveries=deliveries,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook deliveries: {str(e)}"
        )


@router.post("/retry-failed", status_code=http_status.HTTP_200_OK)
async def retry_failed_webhooks(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry failed webhook deliveries.
    """
    try:
        webhook_service = WebhookService(db)
        retry_count = await webhook_service.retry_failed_deliveries()
        
        return {"message": f"Retried {retry_count} failed webhook deliveries"}
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry webhooks: {str(e)}"
        )
