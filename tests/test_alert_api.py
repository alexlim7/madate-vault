#!/usr/bin/env python3
"""
Test suite for Alert API endpoints.
Tests CRUD operations for alert management.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.alert import Alert


class TestAlertAPI:
    """Test cases for alert API endpoints."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        # Mock the execute method to handle different query types
        async def mock_execute(query):
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars = MagicMock(return_value=mock_scalars)
            return mock_result
        
        session.execute = mock_execute
        return session
    
    @pytest.fixture
    def client(self, mock_db_session):
        """Create a test client with mocked database."""
        app.dependency_overrides[get_db] = lambda: mock_db_session
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def sample_alerts(self):
        """Create sample alerts for testing."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mandate_id = str(uuid.uuid4())
        
        return [
            Alert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                alert_type="MANDATE_EXPIRING",
                title="Mandate Expiring Soon",
                message="Mandate will expire in 3 days",
                severity="warning",
                is_read=False,
                is_resolved=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Alert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                alert_type="MANDATE_VERIFICATION_FAILED",
                title="Verification Failed",
                message="Mandate verification failed due to invalid signature",
                severity="error",
                is_read=True,
                is_resolved=False,
                created_at=datetime.utcnow() - timedelta(hours=1),
                updated_at=datetime.utcnow() - timedelta(hours=1)
            ),
            Alert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                alert_type="WEBHOOK_DELIVERY_FAILED",
                title="Webhook Delivery Failed",
                message="Failed to deliver webhook after 3 attempts",
                severity="error",
                is_read=False,
                is_resolved=True,
                resolved_at=datetime.utcnow() - timedelta(minutes=30),
                created_at=datetime.utcnow() - timedelta(hours=2),
                updated_at=datetime.utcnow() - timedelta(hours=2)
            )
        ]
    
    def test_get_alerts_success(self, client, mock_db_session, sample_alerts):
        """Test getting alerts successfully."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service method
        with patch('app.api.v1.endpoints.alerts.AlertService.get_alerts') as mock_get_alerts:
            mock_get_alerts.return_value = {
                "alerts": sample_alerts,
                "total": 3,
                "limit": 100,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["alerts"]) == 3
            assert response_data["total"] == 3
            assert response_data["limit"] == 100
            assert response_data["offset"] == 0
    
    def test_get_alerts_with_filters(self, client, mock_db_session, sample_alerts):
        """Test getting alerts with various filters."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service method
        with patch('app.api.v1.endpoints.alerts.AlertService.get_alerts') as mock_get_alerts:
            mock_get_alerts.return_value = {
                "alerts": sample_alerts,
                "total": 3,
                "limit": 100,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}&is_read=false")
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["alerts"]) == 3
    
    def test_get_alerts_with_pagination(self, client, mock_db_session, sample_alerts):
        """Test getting alerts with pagination."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service method
        with patch('app.api.v1.endpoints.alerts.AlertService.get_alerts') as mock_get_alerts:
            mock_get_alerts.return_value = {
                "alerts": sample_alerts[:2],
                "total": 3,
                "limit": 2,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}&limit=2&offset=0")
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["alerts"]) == 2
            assert response_data["limit"] == 2
            assert response_data["offset"] == 0
    
    def test_get_alerts_missing_tenant_id(self, client):
        """Test getting alerts without tenant_id."""
        response = client.get("/api/v1/alerts/")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_alerts_invalid_pagination(self, client):
        """Test getting alerts with invalid pagination parameters."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Negative limit - API should return 500 (service validation error)
        response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}&limit=-1")
        assert response.status_code == 500
        
        # Negative offset - API should return 500 (service validation error)
        response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}&offset=-1")
        assert response.status_code == 500
    
    def test_get_alert_by_id_success(self, client, mock_db_session, sample_alerts):
        """Test getting a specific alert by ID."""
        alert = sample_alerts[0]
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return the alert
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get(f"/api/v1/alerts/{alert.id}?tenant_id={tenant_id}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == alert.id
        assert response_data["title"] == alert.title
        assert response_data["severity"] == alert.severity
    
    def test_get_alert_by_id_not_found(self, client, mock_db_session):
        """Test getting an alert that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get(f"/api/v1/alerts/{alert_id}?tenant_id={tenant_id}")
        
        assert response.status_code == 404
    
    def test_create_alert_success(self, client, mock_db_session):
        """Test creating a new alert."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        mandate_id = str(uuid.uuid4())
        
        alert_data = {
            "mandate_id": mandate_id,
            "alert_type": "MANDATE_EXPIRING",
            "title": "Test Alert",
            "message": "This is a test alert",
            "severity": "warning"
        }
        
        # Mock the alert service create_alert method
        with patch('app.services.alert_service.AlertService.create_alert', new_callable=AsyncMock) as mock_create_alert:
            mock_alert = Alert(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                mandate_id=mandate_id,
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                message="This is a test alert",
                severity="warning",
                is_read=False,
                is_resolved=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_create_alert.return_value = mock_alert
            
            response = client.post(f"/api/v1/alerts/?tenant_id={tenant_id}", json=alert_data)
            
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["title"] == "Test Alert"
            assert response_data["severity"] == "warning"
            assert response_data["is_read"] is False
            assert response_data["is_resolved"] is False
    
    def test_create_alert_invalid_data(self, client):
        """Test creating alert with invalid data."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Missing required fields
        response = client.post(f"/api/v1/alerts/?tenant_id={tenant_id}", json={})
        assert response.status_code == 422
        
        # Invalid severity
        alert_data = {
            "mandate_id": str(uuid.uuid4()),
            "alert_type": "MANDATE_EXPIRING",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "invalid_severity"
        }
        response = client.post(f"/api/v1/alerts/?tenant_id={tenant_id}", json=alert_data)
        assert response.status_code == 422
    
    def test_update_alert_success(self, client, mock_db_session, sample_alerts):
        """Test updating an alert."""
        alert = sample_alerts[0]
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        update_data = {
            "is_read": True,
            "is_resolved": True
        }
        
        # Mock the database query to return the alert
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = alert
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        response = client.patch(f"/api/v1/alerts/{alert.id}?tenant_id={tenant_id}", json=update_data)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["is_read"] is True
        assert response_data["is_resolved"] is True
    
    def test_update_alert_not_found(self, client, mock_db_session):
        """Test updating an alert that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        update_data = {"is_read": True}
        
        response = client.patch(f"/api/v1/alerts/{alert_id}?tenant_id={tenant_id}", json=update_data)
        
        assert response.status_code == 404
    
    def test_mark_alert_as_read(self, client, mock_db_session, sample_alerts):
        """Test marking an alert as read."""
        alert = sample_alerts[0]
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service mark_alert_as_read method
        with patch('app.services.alert_service.AlertService.mark_alert_as_read', new_callable=AsyncMock) as mock_mark_read:
            mock_mark_read.return_value = True
            
            # Mock the database query to return the alert after update
            mock_result = MagicMock()
            updated_alert = Alert(
                id=alert.id,
                tenant_id=alert.tenant_id,
                mandate_id=alert.mandate_id,
                alert_type=alert.alert_type,
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                is_read=True,
                is_resolved=alert.is_resolved,
                created_at=alert.created_at,
                updated_at=datetime.utcnow()
            )
            mock_result.scalar_one.return_value = updated_alert
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            
            response = client.post(f"/api/v1/alerts/{alert.id}/mark-read?tenant_id={tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["is_read"] is True
    
    def test_resolve_alert(self, client, mock_db_session, sample_alerts):
        """Test resolving an alert."""
        alert = sample_alerts[0]
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service resolve_alert method
        with patch('app.services.alert_service.AlertService.resolve_alert', new_callable=AsyncMock) as mock_resolve_alert:
            mock_resolve_alert.return_value = True
            
            # Mock the database query to return the alert after update
            mock_result = MagicMock()
            updated_alert = Alert(
                id=alert.id,
                tenant_id=alert.tenant_id,
                mandate_id=alert.mandate_id,
                alert_type=alert.alert_type,
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                is_read=alert.is_read,
                is_resolved=True,
                resolved_at=datetime.utcnow(),
                created_at=alert.created_at,
                updated_at=datetime.utcnow()
            )
            mock_result.scalar_one.return_value = updated_alert
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            
            response = client.post(f"/api/v1/alerts/{alert.id}/resolve?tenant_id={tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["is_resolved"] is True
            assert "resolved_at" in response_data
    
    def test_check_expiring_mandates(self, client, mock_db_session):
        """Test checking for expiring mandates."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Mock the alert service check_expiring_mandates method
        with patch('app.services.alert_service.AlertService.check_expiring_mandates', new_callable=AsyncMock) as mock_check_expiring:
            mock_check_expiring.return_value = 3
            
            response = client.post(f"/api/v1/alerts/check-expiring?tenant_id={tenant_id}&days_threshold=7")
            
            assert response.status_code == 200
            response_data = response.json()
            assert "message" in response_data
            assert "Created 3 alerts" in response_data["message"]
    
    def test_check_expiring_mandates_invalid_threshold(self, client):
        """Test checking expiring mandates with invalid threshold."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # Negative threshold
        response = client.post(f"/api/v1/alerts/check-expiring?tenant_id={tenant_id}&days_threshold=-1")
        assert response.status_code == 422
        
        # Too large threshold
        response = client.post(f"/api/v1/alerts/check-expiring?tenant_id={tenant_id}&days_threshold=1000")
        assert response.status_code == 422
    
    def test_alert_service_error_handling(self, client, mock_db_session):
        """Test error handling in alert service."""
        tenant_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('app.services.alert_service.AlertService.get_alerts', new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.side_effect = Exception("Database connection failed")
            
            response = client.get(f"/api/v1/alerts/?tenant_id={tenant_id}")
            
            assert response.status_code == 500
            response_data = response.json()
            assert "Failed to get alerts" in response_data["detail"]
            assert "Database connection failed" in response_data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
