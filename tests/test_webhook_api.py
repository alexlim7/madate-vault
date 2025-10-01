#!/usr/bin/env python3
"""
Test suite for Webhook API endpoints.
Tests CRUD operations for webhook management.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.webhook import Webhook, WebhookDelivery


class TestWebhookAPI:
    """Test cases for webhook API endpoints."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.add = MagicMock()  # add is not async
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        # Mock execute method to return a mock result
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock()
        mock_result.scalars.return_value.all = MagicMock(return_value=[])
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)
        
        return session
    
    @pytest.fixture
    def client(self, mock_db_session):
        """Create a test client with mocked database."""
        app.dependency_overrides[get_db] = lambda: mock_db_session
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    def test_create_webhook(self, client, mock_db_session):
        """Test creating a new webhook."""
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "events": ["MandateCreated", "MandateVerificationFailed"],
            "secret": "test-secret-key",
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "timeout_seconds": 30
        }
        
        response = client.post("/api/v1/webhooks/?tenant_id=550e8400-e29b-41d4-a716-446655440000", json=webhook_data)
        
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == "Test Webhook"
        assert response_data["url"] == "https://example.com/webhook"
        assert response_data["events"] == ["MandateCreated", "MandateVerificationFailed"]
        assert response_data["is_active"] is True
        assert response_data["max_retries"] == 3
        assert response_data["retry_delay_seconds"] == 60
        assert response_data["timeout_seconds"] == 30
        assert "id" in response_data
        assert "created_at" in response_data
        
        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    def test_create_webhook_with_invalid_url(self, client):
        """Test creating webhook with invalid URL."""
        webhook_data = {
            "name": "Test Webhook",
            "url": "not-a-valid-url",
            "events": ["MandateCreated"]
        }
        
        response = client.post("/api/v1/webhooks/?tenant_id=550e8400-e29b-41d4-a716-446655440000", json=webhook_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_create_webhook_missing_required_fields(self, client):
        """Test creating webhook with missing required fields."""
        webhook_data = {
            "name": "Test Webhook"
            # Missing url and events
        }
        
        response = client.post("/api/v1/webhooks/?tenant_id=550e8400-e29b-41d4-a716-446655440000", json=webhook_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_list_webhooks(self, client, mock_db_session):
        """Test listing webhooks for a tenant."""
        # Create mock webhooks
        from datetime import datetime
        now = datetime.utcnow()
        
        webhook1 = Webhook(
            id=str(uuid.uuid4()),
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Webhook 1",
            url="https://example1.com/webhook",
            events=["MandateCreated"],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=now,
            updated_at=now
        )

        webhook2 = Webhook(
            id=str(uuid.uuid4()),
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Webhook 2",
            url="https://example2.com/webhook",
            events=["MandateVerificationFailed"],
            is_active=False,
            max_retries=5,
            retry_delay_seconds=120,
            timeout_seconds=60,
            created_at=now,
            updated_at=now
        )
        
        # Mock the database query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [webhook1, webhook2]
        mock_result.scalars.return_value = mock_scalars
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get("/api/v1/webhooks/?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["name"] == "Webhook 1"
        assert response_data[1]["name"] == "Webhook 2"
    
    def test_list_webhooks_empty(self, client, mock_db_session):
        """Test listing webhooks when none exist."""
        # Mock the database query to return empty list
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get("/api/v1/webhooks/?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 0
    
    def test_get_webhook_by_id(self, client, mock_db_session):
        """Test getting a webhook by ID."""
        webhook_id = str(uuid.uuid4())
        mock_webhook = Webhook(
            id=webhook_id,
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateCreated"],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == webhook_id
        assert response_data["name"] == "Test Webhook"
        assert response_data["url"] == "https://example.com/webhook"
    
    def test_get_nonexistent_webhook(self, client, mock_db_session):
        """Test getting a webhook that doesn't exist."""
        webhook_id = str(uuid.uuid4())
        
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 404
    
    def test_update_webhook(self, client, mock_db_session):
        """Test updating a webhook."""
        webhook_id = str(uuid.uuid4())
        mock_webhook = Webhook(
            id=webhook_id,
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateCreated"],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        update_data = {
            "name": "Updated Webhook",
            "url": "https://updated.example.com/webhook",
            "events": ["MandateCreated", "MandateExpired"]
        }
        
        response = client.patch(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000", json=update_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "Updated Webhook"
        assert response_data["url"] == "https://updated.example.com/webhook"
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    def test_update_nonexistent_webhook(self, client, mock_db_session):
        """Test updating a webhook that doesn't exist."""
        webhook_id = str(uuid.uuid4())
        
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        update_data = {"name": "Updated Webhook"}
        
        response = client.patch(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000", json=update_data)
        
        assert response.status_code == 404
    
    def test_delete_webhook(self, client, mock_db_session):
        """Test deleting a webhook."""
        webhook_id = str(uuid.uuid4())
        mock_webhook = Webhook(
            id=webhook_id,
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["MandateCreated"],
            is_active=True,
            max_retries=3,
            retry_delay_seconds=60,
            timeout_seconds=30,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_webhook
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.delete(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 204
        # 204 No Content doesn't return JSON
        
        # Verify database operations were called
        mock_db_session.delete.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_delete_nonexistent_webhook(self, client, mock_db_session):
        """Test deleting a webhook that doesn't exist."""
        webhook_id = str(uuid.uuid4())
        
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        # Override the execute method to return our custom mock_result
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.delete(f"/api/v1/webhooks/{webhook_id}?tenant_id=550e8400-e29b-41d4-a716-446655440000")
        
        assert response.status_code == 404
    
    def test_get_webhook_deliveries(self, client, mock_db_session):
        """Test getting webhook delivery logs."""
        webhook_id = str(uuid.uuid4())
        
        # Create mock webhook deliveries
        delivery1 = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook_id,
            event_type="MandateCreated",
            payload={"test": "data"},
            status_code=200,
            attempts=1,
            is_delivered=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        delivery2 = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook_id,
            event_type="MandateVerificationFailed",
            payload={"test": "data"},
            status_code=500,
            attempts=2,
            is_delivered=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the webhook service method
        with patch('app.api.v1.endpoints.webhooks.WebhookService.get_webhook_deliveries') as mock_get_deliveries:
            mock_get_deliveries.return_value = {
                "deliveries": [delivery1, delivery2],
                "total": 2,
                "limit": 100,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/webhooks/{webhook_id}/deliveries?tenant_id=550e8400-e29b-41d4-a716-446655440000")
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["deliveries"]) == 2
            assert response_data["total"] == 2
            assert response_data["deliveries"][0]["event_type"] == "MandateCreated"
            assert response_data["deliveries"][1]["event_type"] == "MandateVerificationFailed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
