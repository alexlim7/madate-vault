#!/usr/bin/env python3
"""
Test suite for Webhook Service.
Tests webhook delivery, retry functionality, and delivery history.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.webhook_service import WebhookService, WebhookEvent
from app.models.webhook import Webhook, WebhookDelivery
from app.models.mandate import Mandate


class TestWebhookService:
    """Test cases for webhook service."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        # Mock execute method
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)
        
        return session
    
    @pytest.fixture
    def webhook_service(self, mock_db_session):
        """Create webhook service instance."""
        return WebhookService(mock_db_session)
    
    @pytest.fixture
    def sample_webhook(self):
        """Sample webhook for testing."""
        return Webhook(
            id=str(uuid.uuid4()),
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateCreated", "MandateVerificationFailed"],
            secret="test-secret-key",
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_mandate(self):
        """Sample mandate for testing."""
        return Mandate(
            id=str(uuid.uuid4()),
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            vc_jwt="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            scope="payment",
            amount_limit=1000.0,
            expires_at=datetime.utcnow() + timedelta(days=30),
            status="active",
            retention_days=90,
            verification_status="valid",
            verification_details={"verified": True},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_webhook_delivery(self):
        """Sample webhook delivery for testing."""
        return WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=str(uuid.uuid4()),
            mandate_id=str(uuid.uuid4()),
            event_type="MandateCreated",
            payload={"event_type": "MandateCreated", "mandate": {}},
            attempts=1,
            is_delivered=False,
            status_code=None,
            response_body=None,
            failed_at=None,
            delivered_at=None,
            next_retry_at=None,
            created_at=datetime.utcnow()
        )

    async def test_send_webhook_event_success(self, webhook_service, sample_webhook, sample_mandate):
        """Test sending webhook event successfully."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return webhooks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_webhook]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Mock the delivery method
        with patch.object(webhook_service, '_deliver_webhook', new_callable=AsyncMock) as mock_deliver:
            await webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=sample_mandate,
                tenant_id=tenant_id
            )
            
            # Verify delivery was called
            mock_deliver.assert_called_once()
            call_args = mock_deliver.call_args
            assert call_args[0][0] == sample_webhook
            assert call_args[0][1]["event_type"] == WebhookEvent.MANDATE_CREATED
            assert call_args[0][2] == sample_mandate.id

    async def test_send_webhook_event_no_webhooks(self, webhook_service, sample_mandate):
        """Test sending webhook event when no webhooks exist."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return no webhooks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Mock the delivery method
        with patch.object(webhook_service, '_deliver_webhook', new_callable=AsyncMock) as mock_deliver:
            await webhook_service.send_webhook_event(
                event_type=WebhookEvent.MANDATE_CREATED,
                mandate=sample_mandate,
                tenant_id=tenant_id
            )
            
            # Verify delivery was not called
            mock_deliver.assert_not_called()

    async def test_get_active_webhooks(self, webhook_service, sample_webhook):
        """Test getting active webhooks for an event type."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return webhooks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_webhook]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        webhooks = await webhook_service._get_active_webhooks(tenant_id, WebhookEvent.MANDATE_CREATED)
        
        assert len(webhooks) == 1
        assert webhooks[0] == sample_webhook

    async def test_get_active_webhooks_filter_by_event(self, webhook_service):
        """Test getting active webhooks filtered by event type."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Create webhook that doesn't subscribe to the event
        webhook = Webhook(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateExpired"],  # Different event
            secret="test-secret-key",
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the database query to return webhooks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [webhook]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        webhooks = await webhook_service._get_active_webhooks(tenant_id, WebhookEvent.MANDATE_CREATED)
        
        # Should return empty list since webhook doesn't subscribe to MANDATE_CREATED
        assert len(webhooks) == 0

    def test_create_webhook_payload(self, webhook_service, sample_mandate):
        """Test creating webhook payload."""
        additional_data = {"custom_field": "custom_value"}
        
        payload = webhook_service._create_webhook_payload(
            event_type=WebhookEvent.MANDATE_CREATED,
            mandate=sample_mandate,
            additional_data=additional_data
        )
        
        assert payload["event_type"] == WebhookEvent.MANDATE_CREATED
        assert payload["mandate"] == sample_mandate.to_dict()
        assert payload["custom_field"] == "custom_value"
        assert "timestamp" in payload
        assert payload["webhook_id"] is None

    async def test_deliver_webhook_success(self, webhook_service, sample_webhook, sample_mandate):
        """Test successful webhook delivery."""
        payload = {"event_type": "MandateCreated", "mandate": {}}
        
        # Mock database operations
        webhook_service.db.add = AsyncMock()
        webhook_service.db.commit = AsyncMock()
        webhook_service.db.refresh = AsyncMock()
        
        # Mock the attempt delivery method
        with patch.object(webhook_service, '_attempt_delivery', new_callable=AsyncMock) as mock_attempt:
            await webhook_service._deliver_webhook(sample_webhook, payload, sample_mandate.id)
            
            # Verify database operations
            webhook_service.db.add.assert_called_once()
            webhook_service.db.commit.assert_called_once()
            webhook_service.db.refresh.assert_called_once()
            
            # Verify attempt delivery was called
            mock_attempt.assert_called_once()

    async def test_attempt_delivery_success(self, webhook_service, sample_webhook, sample_webhook_delivery):
        """Test successful webhook delivery attempt."""
        # Mock httpx client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await webhook_service._attempt_delivery(sample_webhook_delivery, sample_webhook)
            
            # Verify HTTP request was made
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == sample_webhook.url  # First positional argument is URL
            assert call_args[1]["json"] == sample_webhook_delivery.payload
            
            # Verify delivery was marked as successful
            assert sample_webhook_delivery.is_delivered is True
            assert sample_webhook_delivery.delivered_at is not None
            assert sample_webhook_delivery.next_retry_at is None

    async def test_attempt_delivery_failure(self, webhook_service, sample_webhook, sample_webhook_delivery):
        """Test failed webhook delivery attempt."""
        # Mock httpx client to raise an exception
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection error")
            
            # Mock the handle failure method
            with patch.object(webhook_service, '_handle_delivery_failure', new_callable=AsyncMock) as mock_handle:
                await webhook_service._attempt_delivery(sample_webhook_delivery, sample_webhook)
                
                # Verify failure handling was called
                mock_handle.assert_called_once()

    async def test_handle_delivery_failure_with_retry(self, webhook_service, sample_webhook, sample_webhook_delivery):
        """Test handling delivery failure with retry."""
        sample_webhook_delivery.attempts = 1  # Less than max_retries
        
        await webhook_service._handle_delivery_failure(
            sample_webhook_delivery, 
            sample_webhook, 
            "Connection error"
        )
        
        # Verify retry is scheduled
        assert sample_webhook_delivery.failed_at is not None
        assert sample_webhook_delivery.next_retry_at is not None
        assert sample_webhook_delivery.response_body == "Connection error"

    async def test_handle_delivery_failure_max_retries_exceeded(self, webhook_service, sample_webhook, sample_webhook_delivery):
        """Test handling delivery failure when max retries exceeded."""
        sample_webhook_delivery.attempts = 3  # Equal to max_retries
        
        await webhook_service._handle_delivery_failure(
            sample_webhook_delivery, 
            sample_webhook, 
            "Connection error"
        )
        
        # Verify no retry is scheduled
        assert sample_webhook_delivery.failed_at is not None
        assert sample_webhook_delivery.next_retry_at is None
        assert sample_webhook_delivery.response_body == "Connection error"

    def test_create_signature(self, webhook_service):
        """Test creating HMAC signature."""
        secret = "test-secret"
        payload = '{"event_type": "MandateCreated"}'
        
        signature = webhook_service._create_signature(secret, payload)
        
        # Verify signature is created (should be a hex string)
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex length

    async def test_retry_failed_deliveries_success(self, webhook_service, sample_webhook_delivery):
        """Test retrying failed deliveries successfully."""
        # Mock deliveries ready for retry
        sample_webhook_delivery.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_webhook_delivery]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Mock webhook lookup
        mock_webhook_result = AsyncMock()
        mock_webhook_result.scalar_one_or_none = MagicMock(return_value=Webhook(
            id=sample_webhook_delivery.webhook_id,
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateCreated"],
            secret="test-secret-key",
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ))
        
        # Mock multiple execute calls
        webhook_service.db.execute.side_effect = [mock_result, mock_webhook_result]
        
        # Mock attempt delivery
        with patch.object(webhook_service, '_attempt_delivery', new_callable=AsyncMock) as mock_attempt:
            retry_count = await webhook_service.retry_failed_deliveries()
            
            assert retry_count == 1
            mock_attempt.assert_called_once()

    async def test_retry_failed_deliveries_no_deliveries(self, webhook_service):
        """Test retrying failed deliveries when no deliveries are ready."""
        # Mock no deliveries ready for retry
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        retry_count = await webhook_service.retry_failed_deliveries()
        
        assert retry_count == 0

    async def test_get_webhook_deliveries(self, webhook_service, sample_webhook_delivery):
        """Test getting webhook delivery history."""
        webhook_id = str(uuid.uuid4())
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_webhook_delivery]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_service.get_webhook_deliveries(
            webhook_id=webhook_id,
            limit=10,
            offset=0
        )
        
        assert result["total"] == 1
        assert result["limit"] == 10
        assert result["offset"] == 0
        assert len(result["deliveries"]) == 1
        assert result["deliveries"][0] == sample_webhook_delivery

    async def test_get_webhook_deliveries_with_filters(self, webhook_service, sample_webhook_delivery):
        """Test getting webhook delivery history with filters."""
        webhook_id = str(uuid.uuid4())
        mandate_id = str(uuid.uuid4())
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_webhook_delivery]
        webhook_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await webhook_service.get_webhook_deliveries(
            webhook_id=webhook_id,
            mandate_id=mandate_id,
            limit=5,
            offset=10
        )
        
        assert result["total"] == 1
        assert result["limit"] == 5
        assert result["offset"] == 10
        assert len(result["deliveries"]) == 1

    async def test_close_client(self, webhook_service):
        """Test closing the HTTP client."""
        with patch.object(webhook_service.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await webhook_service.close()
            mock_close.assert_called_once()