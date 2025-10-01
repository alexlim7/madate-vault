"""
Comprehensive tests for webhook delivery system.
Tests HMAC signing, delivery, retries, and background workers.
"""
import pytest
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from sqlalchemy import select

from app.models.webhook import Webhook, WebhookDelivery
from app.models.mandate import Mandate
from app.models.customer import Customer
from app.services.webhook_service import WebhookService, WebhookEvent
from app.workers.webhook_worker import WebhookWorker
import uuid


@pytest.fixture
async def test_customer(db_session):
    """Create a test customer."""
    customer = Customer(
        tenant_id=str(uuid.uuid4()),
        name="Test Company",
        email="test@webhook.com",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def test_webhook(db_session, test_customer):
    """Create a test webhook."""
    webhook = Webhook(
        id=str(uuid.uuid4()),
        tenant_id=test_customer.tenant_id,
        name="Test Webhook",
        url="https://example.com/webhooks/mandate-events",
        events=[WebhookEvent.MANDATE_CREATED, WebhookEvent.MANDATE_EXPIRED],
        secret="test-webhook-secret-key",
        is_active=True,
        max_retries=3,
        retry_delay_seconds=60,
        timeout_seconds=30,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(webhook)
    await db_session.commit()
    await db_session.refresh(webhook)
    return webhook


@pytest.fixture
async def test_mandate(db_session, test_customer):
    """Create a test mandate."""
    mandate = Mandate(
        id=str(uuid.uuid4()),
        vc_jwt="eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZSJ9.signature",
        issuer_did="did:example:issuer",
        subject_did="did:example:subject",
        scope="payment.recurring",
        amount_limit="1000.00 USD",
        status="active",
        tenant_id=test_customer.tenant_id,
        verification_status="VALID",
        verification_reason="All checks passed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(mandate)
    await db_session.commit()
    await db_session.refresh(mandate)
    return mandate


class TestHMACSignature:
    """Test HMAC signature generation and verification."""
    
    @pytest.mark.asyncio
    async def test_create_signature(self, db_session):
        """Test HMAC signature creation."""
        webhook_service = WebhookService(db_session)
        
        secret = "my-webhook-secret"
        payload = '{"event_type":"MandateCreated","mandate_id":"123"}'
        
        signature = webhook_service._create_signature(secret, payload)
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest length
        
        # Verify signature manually
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        assert signature == expected_sig
    
    @pytest.mark.asyncio
    async def test_signature_changes_with_payload(self, db_session):
        """Test that signature changes when payload changes."""
        webhook_service = WebhookService(db_session)
        
        secret = "secret"
        payload1 = '{"data":"value1"}'
        payload2 = '{"data":"value2"}'
        
        sig1 = webhook_service._create_signature(secret, payload1)
        sig2 = webhook_service._create_signature(secret, payload2)
        
        assert sig1 != sig2
    
    @pytest.mark.asyncio
    async def test_signature_changes_with_secret(self, db_session):
        """Test that signature changes when secret changes."""
        webhook_service = WebhookService(db_session)
        
        payload = '{"data":"value"}'
        secret1 = "secret1"
        secret2 = "secret2"
        
        sig1 = webhook_service._create_signature(secret1, payload)
        sig2 = webhook_service._create_signature(secret2, payload)
        
        assert sig1 != sig2


class TestWebhookPayload:
    """Test webhook payload creation."""
    
    @pytest.mark.asyncio
    async def test_create_webhook_payload(self, db_session, test_mandate):
        """Test webhook payload creation."""
        webhook_service = WebhookService(db_session)
        
        payload = webhook_service._create_webhook_payload(
            event_type=WebhookEvent.MANDATE_CREATED,
            mandate=test_mandate,
            additional_data={"custom_field": "value"}
        )
        
        assert payload["event_type"] == WebhookEvent.MANDATE_CREATED
        assert "mandate" in payload
        assert payload["mandate"]["id"] == test_mandate.id
        assert "timestamp" in payload
        assert payload["custom_field"] == "value"
    
    @pytest.mark.asyncio
    async def test_payload_includes_mandate_details(self, db_session, test_mandate):
        """Test that payload includes full mandate details."""
        webhook_service = WebhookService(db_session)
        
        payload = webhook_service._create_webhook_payload(
            event_type=WebhookEvent.MANDATE_CREATED,
            mandate=test_mandate
        )
        
        mandate_data = payload["mandate"]
        assert mandate_data["issuer_did"] == "did:example:issuer"
        assert mandate_data["subject_did"] == "did:example:subject"
        assert mandate_data["scope"] == "payment.recurring"
        assert mandate_data["amount_limit"] == "1000.00 USD"
        assert mandate_data["verification_status"] == "VALID"


@pytest.mark.asyncio
class TestWebhookDelivery:
    """Test webhook delivery mechanism."""
    
    async def test_successful_delivery(self, db_session, test_webhook, test_mandate):
        """Test successful webhook delivery."""
        webhook_service = WebhookService(db_session)
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"received": true}'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response) as mock_post:
            payload = {"event_type": "MandateCreated", "mandate_id": test_mandate.id}
            
            await webhook_service._deliver_webhook(test_webhook, payload, test_mandate.id)
            
            # Verify HTTP call was made
            assert mock_post.called
            call_args = mock_post.call_args
            
            # Check URL
            assert call_args[0][0] == test_webhook.url
            
            # Check headers include signature
            headers = call_args[1]['headers']
            assert 'X-Webhook-Signature' in headers
            assert headers['X-Webhook-Signature'].startswith('sha256=')
    
    async def test_delivery_with_hmac_signature(self, db_session, test_webhook, test_mandate):
        """Test that delivery includes correct HMAC signature."""
        webhook_service = WebhookService(db_session)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response) as mock_post:
            payload = {"event_type": "test", "data": "value"}
            
            await webhook_service._deliver_webhook(test_webhook, payload, test_mandate.id)
            
            # Extract signature from call
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            signature = headers['X-Webhook-Signature'].replace('sha256=', '')
            
            # Verify signature is correct
            expected_sig = hmac.new(
                test_webhook.secret.encode('utf-8'),
                json.dumps(payload).encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            assert signature == expected_sig
    
    async def test_delivery_timeout_handling(self, db_session, test_webhook, test_mandate):
        """Test handling of webhook delivery timeout."""
        webhook_service = WebhookService(db_session)
        
        # Mock timeout exception
        with patch.object(webhook_service.client, 'post', side_effect=httpx.TimeoutException("Request timeout")):
            payload = {"event_type": "test"}
            
            await webhook_service._deliver_webhook(test_webhook, payload, test_mandate.id)
            
            # Check that delivery was created and marked as failed
            query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == test_webhook.id)
            result = await db_session.execute(query)
            delivery = result.scalar_one_or_none()
            
            assert delivery is not None
            assert delivery.is_delivered is False
            assert delivery.failed_at is not None
            assert "Timeout" in delivery.response_body
            assert delivery.next_retry_at is not None  # Retry scheduled
    
    async def test_delivery_http_error_handling(self, db_session, test_webhook, test_mandate):
        """Test handling of HTTP error responses."""
        webhook_service = WebhookService(db_session)
        
        # Mock 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response):
            payload = {"event_type": "test"}
            
            await webhook_service._deliver_webhook(test_webhook, payload, test_mandate.id)
            
            # Check delivery record
            query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == test_webhook.id)
            result = await db_session.execute(query)
            delivery = result.scalar_one_or_none()
            
            assert delivery.is_delivered is False
            assert delivery.status_code == 500
            assert delivery.next_retry_at is not None  # Retry scheduled


class TestWebhookRetryLogic:
    """Test webhook retry logic and exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_retry_scheduling_exponential_backoff(self, db_session, test_webhook):
        """Test exponential backoff for retries."""
        webhook_service = WebhookService(db_session)
        
        delivery = WebhookDelivery(
            webhook_id=test_webhook.id,
            event_type="test",
            payload={},
            attempts=0
        )
        
        # Simulate failures and check retry delays
        for attempt in range(1, 4):
            delivery.attempts = attempt
            await webhook_service._handle_delivery_failure(delivery, test_webhook, "Test failure")
            
            expected_delay = test_webhook.retry_delay_seconds * (2 ** (attempt - 1))
            
            if attempt < test_webhook.max_retries:
                assert delivery.next_retry_at is not None
                # Verify approximate delay (within 2 seconds)
                actual_delay = (delivery.next_retry_at - datetime.utcnow()).total_seconds()
                assert abs(actual_delay - expected_delay) < 2
            else:
                # Max retries reached
                assert delivery.next_retry_at is None
    
    @pytest.mark.asyncio
    async def test_retry_failed_deliveries(self, db_session, test_webhook, test_mandate):
        """Test retrying failed webhook deliveries."""
        webhook_service = WebhookService(db_session)
        
        # Create failed delivery ready for retry
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=test_webhook.id,
            mandate_id=test_mandate.id,
            event_type=WebhookEvent.MANDATE_CREATED,
            payload={"event_type": "test"},
            attempts=1,
            is_delivered=False,
            next_retry_at=datetime.utcnow() - timedelta(seconds=10),  # Ready for retry
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(delivery)
        await db_session.commit()
        
        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response):
            retry_count = await webhook_service.retry_failed_deliveries()
            
            assert retry_count >= 1
            
            # Verify delivery was updated
            await db_session.refresh(delivery)
            assert delivery.is_delivered is True
            assert delivery.delivered_at is not None


class TestWebhookWorker:
    """Test background webhook worker."""
    
    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self):
        """Test webhook worker lifecycle."""
        worker = WebhookWorker(retry_interval=1)
        
        # Start worker
        await worker.start()
        assert worker._running is True
        
        # Stop worker
        worker.stop()
        assert worker._running is False
    
    @pytest.mark.asyncio
    async def test_worker_processes_retries(self, db_session, test_webhook, test_mandate):
        """Test that worker processes retry queue."""
        # Create failed delivery ready for retry
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=test_webhook.id,
            mandate_id=test_mandate.id,
            event_type=WebhookEvent.MANDATE_CREATED,
            payload={"event_type": "test"},
            attempts=1,
            is_delivered=False,
            next_retry_at=datetime.utcnow() - timedelta(seconds=10),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(delivery)
        await db_session.commit()
        
        worker = WebhookWorker(retry_interval=1)
        
        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            # Process one iteration
            await worker._process_retries()
            
            # Verify delivery was processed
            await db_session.refresh(delivery)
            assert delivery.attempts >= 2  # Incremented


class TestWebhookEvents:
    """Test webhook event triggering."""
    
    @pytest.mark.asyncio
    async def test_send_webhook_event(self, db_session, test_webhook, test_mandate, test_customer):
        """Test sending webhook event."""
        webhook_service = WebhookService(db_session)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response):
            await webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=test_mandate,
                tenant_id=test_customer.tenant_id,
                additional_data={"verification": "passed"}
            )
            
            # Verify delivery was created
            query = select(WebhookDelivery).where(WebhookDelivery.mandate_id == test_mandate.id)
            result = await db_session.execute(query)
            delivery = result.scalar_one_or_none()
            
            assert delivery is not None
            assert delivery.event_type == WebhookEvent.MANDATE_CREATED
            assert delivery.webhook_id == test_webhook.id
            assert "verification" in delivery.payload
    
    @pytest.mark.asyncio
    async def test_multiple_webhooks_receive_event(self, db_session, test_customer, test_mandate):
        """Test that multiple webhooks receive the same event."""
        # Create multiple webhooks
        webhook1 = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=test_customer.tenant_id,
            name="Webhook 1",
            url="https://example.com/webhook1",
            events=[WebhookEvent.MANDATE_CREATED],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        webhook2 = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=test_customer.tenant_id,
            name="Webhook 2",
            url="https://example.com/webhook2",
            events=[WebhookEvent.MANDATE_CREATED],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db_session.add_all([webhook1, webhook2])
        await db_session.commit()
        
        webhook_service = WebhookService(db_session)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response) as mock_post:
            await webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=test_mandate,
                tenant_id=test_customer.tenant_id
            )
            
            # Both webhooks should receive the event
            assert mock_post.call_count >= 2


class TestWebhookFiltering:
    """Test webhook event filtering and subscription."""
    
    @pytest.mark.asyncio
    async def test_only_subscribed_webhooks_receive_event(self, db_session, test_customer, test_mandate):
        """Test that only webhooks subscribed to event type receive it."""
        # Webhook subscribed to MANDATE_CREATED
        webhook_subscribed = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=test_customer.tenant_id,
            name="Subscribed",
            url="https://example.com/subscribed",
            events=[WebhookEvent.MANDATE_CREATED],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Webhook NOT subscribed to MANDATE_CREATED
        webhook_not_subscribed = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=test_customer.tenant_id,
            name="Not Subscribed",
            url="https://example.com/not-subscribed",
            events=[WebhookEvent.MANDATE_EXPIRED],  # Different event
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db_session.add_all([webhook_subscribed, webhook_not_subscribed])
        await db_session.commit()
        
        webhook_service = WebhookService(db_session)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        
        with patch.object(webhook_service.client, 'post', return_value=mock_response) as mock_post:
            await webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=test_mandate,
                tenant_id=test_customer.tenant_id
            )
            
            # Only subscribed webhook should receive
            assert mock_post.call_count == 1


# Fixture for database session
@pytest.fixture
async def db_session():
    """Create a test database session."""
    import os
    os.environ['SECRET_KEY'] = 'test-secret-key-minimum-32-characters-long'
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
    
    from app.core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        yield session


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

