#!/usr/bin/env python3
"""
Test suite for Alert Service.
Tests alert creation, retrieval, and management functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.alert_service import AlertService
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertUpdate


class TestAlertService:
    """Test cases for alert service."""
    
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
    def alert_service(self, mock_db_session):
        """Create alert service instance."""
        return AlertService(mock_db_session)
    
    @pytest.fixture
    def sample_alert_data(self):
        """Sample alert data for testing."""
        return AlertCreate(
            mandate_id=str(uuid.uuid4()),
            alert_type="MANDATE_EXPIRING",
            title="Mandate Expiring Soon",
            message="Mandate will expire in 3 days",
            severity="warning"
        )
    
    @pytest.fixture
    def sample_alert(self):
        """Sample alert model for testing."""
        return Alert(
            id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            mandate_id=str(uuid.uuid4()),
            alert_type="MANDATE_EXPIRING",
            title="Mandate Expiring Soon",
            message="Mandate will expire in 3 days",
            severity="warning",
            is_read=False,
            is_resolved=False,
            created_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_alerts(self):
        """Multiple sample alerts for testing."""
        tenant_id = str(uuid.uuid4())
        mandate_id = str(uuid.uuid4())
        base_time = datetime.utcnow()
        
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
                created_at=base_time
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
                created_at=base_time - timedelta(hours=1)
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
                resolved_at=base_time - timedelta(minutes=30),
                created_at=base_time - timedelta(hours=2)
            )
        ]
    
    @pytest.mark.asyncio
    async def test_create_alert_success(self, alert_service, mock_db_session, sample_alert_data, sample_alert):
        """Test creating an alert successfully."""
        tenant_id = sample_alert.tenant_id
        
        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        # Mock the refresh to set the id and timestamps
        def mock_refresh(alert):
            alert.id = sample_alert.id
            alert.tenant_id = tenant_id
            alert.created_at = sample_alert.created_at
        
        mock_db_session.refresh.side_effect = mock_refresh
        
        result = await alert_service.create_alert(tenant_id, sample_alert_data)
        
        assert result.mandate_id == sample_alert_data.mandate_id
        assert result.alert_type == sample_alert_data.alert_type
        assert result.title == sample_alert_data.title
        assert result.message == sample_alert_data.message
        assert result.severity == sample_alert_data.severity
        assert result.is_read is False
        assert result.is_resolved is False
        assert result.tenant_id == tenant_id
        
        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_success(self, alert_service, mock_db_session, sample_alert):
        """Test getting an alert by ID successfully."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_alert)
        mock_db_session.execute.return_value = mock_result
        
        result = await alert_service.get_alert_by_id(sample_alert.id, sample_alert.tenant_id)
        
        assert result is not None
        assert result.id == sample_alert.id
        assert result.tenant_id == sample_alert.tenant_id
        assert result.title == sample_alert.title
        assert result.severity == sample_alert.severity
    
    @pytest.mark.asyncio
    async def test_get_alert_by_id_not_found(self, alert_service, mock_db_session):
        """Test getting an alert that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await alert_service.get_alert_by_id(alert_id, tenant_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_alerts_success(self, alert_service, mock_db_session, sample_alerts):
        """Test getting alerts successfully."""
        tenant_id = sample_alerts[0].tenant_id
        
        # Mock database query - need to handle both count and data queries
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_alerts
        
        # Mock both execute calls (count query and data query)
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await alert_service.get_alerts(tenant_id=tenant_id)
        
        assert len(result["alerts"]) == 3
        assert result["total"] == 3
        assert result["limit"] == 100
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self, alert_service, mock_db_session, sample_alerts):
        """Test getting alerts with various filters."""
        tenant_id = sample_alerts[0].tenant_id
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_alerts
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test with severity filter
        result = await alert_service.get_alerts(tenant_id=tenant_id, severity="warning")
        assert len(result["alerts"]) == 3
        
        # Test with alert_type filter
        result = await alert_service.get_alerts(tenant_id=tenant_id, alert_type="MANDATE_EXPIRING")
        assert len(result["alerts"]) == 3
        
        # Test with is_read filter
        result = await alert_service.get_alerts(tenant_id=tenant_id, is_read=False)
        assert len(result["alerts"]) == 3
        
        # Test with is_resolved filter
        result = await alert_service.get_alerts(tenant_id=tenant_id, is_resolved=False)
        assert len(result["alerts"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_alerts_with_pagination(self, alert_service, mock_db_session, sample_alerts):
        """Test getting alerts with pagination."""
        tenant_id = sample_alerts[0].tenant_id
        
        # Mock database query to return first 2 alerts
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_alerts[:2]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await alert_service.get_alerts(tenant_id=tenant_id, limit=2, offset=0)
        
        assert len(result["alerts"]) == 2
        assert result["limit"] == 2
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_get_alerts_empty(self, alert_service, mock_db_session):
        """Test getting alerts when none exist."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await alert_service.get_alerts(tenant_id=tenant_id)
        
        assert len(result["alerts"]) == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_update_alert_success(self, alert_service, mock_db_session, sample_alert):
        """Test updating an alert successfully."""
        # Mock getting existing alert
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_alert)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        update_data = AlertUpdate(
            is_read=True,
            is_resolved=True
        )
        
        result = await alert_service.update_alert(sample_alert.id, sample_alert.tenant_id, update_data)
        
        assert result.is_read is True
        assert result.is_resolved is True
        assert result.resolved_at is not None
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_alert_not_found(self, alert_service, mock_db_session):
        """Test updating an alert that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        update_data = AlertUpdate(is_read=True)
        
        result = await alert_service.update_alert(alert_id, tenant_id, update_data)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_mark_alert_as_read_success(self, alert_service, mock_db_session, sample_alert):
        """Test marking an alert as read successfully."""
        # Mock getting existing alert
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_alert)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        result = await alert_service.mark_alert_as_read(sample_alert.id, sample_alert.tenant_id)
        
        assert result.is_read is True
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_alert_as_read_not_found(self, alert_service, mock_db_session):
        """Test marking an alert as read that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await alert_service.mark_alert_as_read(alert_id, tenant_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_resolve_alert_success(self, alert_service, mock_db_session, sample_alert):
        """Test resolving an alert successfully."""
        # Mock getting existing alert
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_alert)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        result = await alert_service.resolve_alert(sample_alert.id, sample_alert.tenant_id)
        
        assert result.is_resolved is True
        assert result.resolved_at is not None
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_alert_not_found(self, alert_service, mock_db_session):
        """Test resolving an alert that doesn't exist."""
        alert_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await alert_service.resolve_alert(alert_id, tenant_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_check_expiring_mandates_success(self, alert_service, mock_db_session, sample_alert):
        """Test checking for expiring mandates successfully."""
        tenant_id = str(uuid.uuid4())
        mandate_id = str(uuid.uuid4())
        
        # Mock expiring mandate
        expiring_mandate = MagicMock()
        expiring_mandate.id = mandate_id
        expiring_mandate.expires_at = datetime.utcnow() + timedelta(days=3)
        expiring_mandate.issuer_did = "did:example:issuer"
        expiring_mandate.subject_did = "did:example:subject"
        
        # Mock database query to return expiring mandates
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expiring_mandate]
        
        # Mock existing alert query to return None (no existing alerts)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none = MagicMock(return_value=None)
        
        # Configure mock_db_session to return different results for different queries
        call_count = 0
        def mock_execute_side_effect(query):
            nonlocal call_count
            call_count += 1
            # First call: get expiring mandates
            if call_count == 1:
                return mock_result
            # Second call: check for existing alerts
            elif call_count == 2:
                return mock_existing_result
            else:
                return mock_result
        
        mock_db_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        
        # Mock alert creation
        with patch.object(alert_service, 'create_mandate_expiring_alert', new_callable=AsyncMock) as mock_create_alert:
            mock_create_alert.return_value = sample_alert
            
            alerts_created = await alert_service.check_expiring_mandates(days_threshold=7)
            
            assert alerts_created == 1
            mock_create_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_expiring_mandates_no_expiring(self, alert_service, mock_db_session):
        """Test checking for expiring mandates when none are expiring."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return no expiring mandates
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        alerts_created = await alert_service.check_expiring_mandates(days_threshold=7)
        
        assert alerts_created == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_old_resolved_alerts_success(self, alert_service, mock_db_session):
        """Test cleaning up old resolved alerts successfully."""
        # Mock database query to return old alerts for deletion
        old_alerts = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = old_alerts
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock database operations
        mock_db_session.commit = AsyncMock()
        mock_db_session.delete = AsyncMock()
        
        result = await alert_service.cleanup_old_resolved_alerts(days_threshold=30)
        
        assert result == 5
        
        # Verify database operations were called
        assert mock_db_session.delete.call_count == 5
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_service_validation_error(self, alert_service, mock_db_session):
        """Test alert service validation error handling."""
        tenant_id = str(uuid.uuid4())
        
        # Test with invalid severity - this will fail at the schema level
        with pytest.raises(Exception):  # Pydantic validation error
            invalid_alert_data = AlertCreate(
                mandate_id=str(uuid.uuid4()),
                alert_type="MANDATE_EXPIRING",
                title="Test Alert",
                message="Test message",
                severity="invalid_severity"
            )
    
    @pytest.mark.asyncio
    async def test_alert_service_pagination_validation(self, alert_service, mock_db_session):
        """Test alert service pagination validation."""
        tenant_id = str(uuid.uuid4())
        
        # Test with negative limit
        with pytest.raises(ValueError, match="Limit must be positive"):
            await alert_service.get_alerts(tenant_id=tenant_id, limit=-1)
        
        # Test with negative offset
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            await alert_service.get_alerts(tenant_id=tenant_id, offset=-1)
        
        # Test with too large limit
        with pytest.raises(ValueError, match="Limit cannot exceed 1000"):
            await alert_service.get_alerts(tenant_id=tenant_id, limit=1001)
    
    @pytest.mark.asyncio
    async def test_alert_service_database_error(self, alert_service, mock_db_session, sample_alert_data):
        """Test alert service error handling."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database to raise an exception
        def mock_add_side_effect(obj):
            raise Exception("Database connection failed")
        mock_db_session.add.side_effect = mock_add_side_effect
        
        with pytest.raises(Exception, match="Database connection failed"):
            await alert_service.create_alert(tenant_id, sample_alert_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
