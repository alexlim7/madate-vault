"""
Webhook service for managing webhook deliveries with retry logic.
"""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.webhook import Webhook, WebhookDelivery
from app.models.mandate import Mandate

logger = logging.getLogger(__name__)


class WebhookEvent:
    """Webhook event types."""
    MANDATE_CREATED = "MandateCreated"
    MANDATE_VERIFICATION_FAILED = "MandateVerificationFailed"
    MANDATE_EXPIRED = "MandateExpired"
    MANDATE_REVOKED = "MandateRevoked"


class WebhookService:
    """Service for managing webhook deliveries."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_webhook_event(
        self,
        event_type: str,
        mandate: Mandate,
        tenant_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send webhook event to all registered webhooks for the tenant.
        
        Args:
            event_type: Type of webhook event
            mandate: Mandate object
            tenant_id: Tenant ID
            additional_data: Additional data to include in payload
        """
        try:
            # Get active webhooks for the tenant that subscribe to this event
            webhooks = await self._get_active_webhooks(tenant_id, event_type)
            
            if not webhooks:
                logger.info(f"No active webhooks found for event {event_type} and tenant {tenant_id}")
                return
            
            # Create webhook payload
            payload = self._create_webhook_payload(event_type, mandate, additional_data)
            
            # Send to each webhook
            for webhook in webhooks:
                await self._deliver_webhook(webhook, payload, mandate.id)
                
        except Exception as e:
            logger.error(f"Error sending webhook event {event_type}: {str(e)}")
    
    async def _get_active_webhooks(self, tenant_id: str, event_type: str) -> List[Webhook]:
        """Get active webhooks that subscribe to the given event type."""
        query = select(Webhook).where(
            and_(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        webhooks = result.scalars().all()
        
        # Filter webhooks that subscribe to this event type
        subscribed_webhooks = []
        for webhook in webhooks:
            if event_type in webhook.events:
                subscribed_webhooks.append(webhook)
        
        return subscribed_webhooks
    
    def _create_webhook_payload(
        self,
        event_type: str,
        mandate: Mandate,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create webhook payload."""
        payload = {
            "event_type": event_type,
            "mandate": mandate.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": None,  # Will be set during delivery
        }
        
        if additional_data:
            payload.update(additional_data)
        
        return payload
    
    async def _deliver_webhook(
        self,
        webhook: Webhook,
        payload: Dict[str, Any],
        mandate_id: Optional[str] = None
    ) -> None:
        """
        Deliver webhook with retry logic.
        
        Args:
            webhook: Webhook configuration
            payload: Webhook payload
            mandate_id: Optional mandate ID
        """
        # Create webhook delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            mandate_id=mandate_id,
            event_type=payload["event_type"],
            payload=payload
        )
        
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        
        # Attempt delivery
        await self._attempt_delivery(delivery, webhook)
    
    async def _attempt_delivery(self, delivery: WebhookDelivery, webhook: Webhook) -> None:
        """Attempt to deliver webhook with retry logic."""
        try:
            # Update attempt count
            delivery.attempts += 1
            
            # Create signature if webhook has secret
            headers = {"Content-Type": "application/json"}
            if webhook.secret:
                signature = self._create_signature(webhook.secret, json.dumps(delivery.payload))
                headers["X-Webhook-Signature"] = f"sha256={signature}"
            
            # Send webhook
            response = await self.client.post(
                webhook.url,
                json=delivery.payload,
                headers=headers,
                timeout=webhook.timeout_seconds
            )
            
            # Update delivery status
            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000]  # Limit response body size
            
            if 200 <= response.status_code < 300:
                # Success
                delivery.is_delivered = True
                delivery.delivered_at = datetime.utcnow()
                delivery.next_retry_at = None
                logger.info(f"Webhook delivered successfully: {webhook.url} (attempt {delivery.attempts})")
            else:
                # Failed - schedule retry if within retry limit
                await self._handle_delivery_failure(delivery, webhook, f"HTTP {response.status_code}")
            
        except httpx.TimeoutException:
            await self._handle_delivery_failure(delivery, webhook, "Timeout")
        except httpx.RequestError as e:
            await self._handle_delivery_failure(delivery, webhook, f"Request error: {str(e)}")
        except Exception as e:
            await self._handle_delivery_failure(delivery, webhook, f"Unexpected error: {str(e)}")
        
        await self.db.commit()
    
    async def _handle_delivery_failure(
        self,
        delivery: WebhookDelivery,
        webhook: Webhook,
        error_message: str
    ) -> None:
        """Handle webhook delivery failure and schedule retry if appropriate."""
        delivery.failed_at = datetime.utcnow()
        delivery.response_body = error_message
        
        if delivery.attempts < webhook.max_retries:
            # Schedule retry with exponential backoff
            retry_delay = webhook.retry_delay_seconds * (2 ** (delivery.attempts - 1))
            delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
            logger.warning(f"Webhook delivery failed, scheduling retry: {webhook.url} (attempt {delivery.attempts}, retry in {retry_delay}s)")
        else:
            # Max retries exceeded
            delivery.next_retry_at = None
            logger.error(f"Webhook delivery failed permanently after {delivery.attempts} attempts: {webhook.url}")
    
    def _create_signature(self, secret: str, payload: str) -> str:
        """Create HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def retry_failed_deliveries(self) -> int:
        """
        Retry webhook deliveries that are scheduled for retry.
        
        Returns:
            Number of deliveries retried
        """
        try:
            # Get deliveries ready for retry
            query = select(WebhookDelivery).where(
                and_(
                    WebhookDelivery.is_delivered == False,
                    WebhookDelivery.next_retry_at <= datetime.utcnow(),
                    WebhookDelivery.next_retry_at.is_not(None)
                )
            )
            
            result = await self.db.execute(query)
            deliveries = result.scalars().all()
            
            retry_count = 0
            for delivery in deliveries:
                # Get webhook configuration
                webhook_query = select(Webhook).where(Webhook.id == delivery.webhook_id)
                webhook_result = await self.db.execute(webhook_query)
                webhook = webhook_result.scalar_one_or_none()
                
                if webhook and webhook.is_active:
                    await self._attempt_delivery(delivery, webhook)
                    retry_count += 1
                else:
                    # Webhook no longer exists or is inactive
                    delivery.next_retry_at = None
                    logger.warning(f"Webhook {delivery.webhook_id} no longer active, canceling retry")
            
            await self.db.commit()
            return retry_count
            
        except Exception as e:
            logger.error(f"Error retrying webhook deliveries: {str(e)}")
            return 0
    
    async def get_webhook_deliveries(
        self,
        webhook_id: Optional[str] = None,
        mandate_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get webhook delivery history.
        
        Args:
            webhook_id: Filter by webhook ID
            mandate_id: Filter by mandate ID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Dictionary with deliveries and pagination info
        """
        query = select(WebhookDelivery)
        conditions = []
        
        if webhook_id:
            conditions.append(WebhookDelivery.webhook_id == webhook_id)
        
        if mandate_id:
            conditions.append(WebhookDelivery.mandate_id == mandate_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(WebhookDelivery.id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total_scalars = total_result.scalars()
        total = len(total_scalars.all())
        
        # Apply pagination
        query = query.order_by(WebhookDelivery.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        deliveries_scalars = result.scalars()
        deliveries = deliveries_scalars.all()
        
        return {
            "deliveries": deliveries,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


