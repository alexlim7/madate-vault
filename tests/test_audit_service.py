#!/usr/bin/env python3
"""
Test suite for Audit Service.
Tests audit log creation, retrieval, and search functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_service import AuditService
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogSearch


class TestAuditService:
    """Test cases for audit service."""
    
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
    def audit_service(self, mock_db_session):
        """Create audit service instance."""
        return AuditService(mock_db_session)
    
    @pytest.fixture
    def sample_audit_log_data(self):
        """Sample audit log data for testing."""
        return {
            "mandate_id": str(uuid.uuid4()),
            "event_type": "CREATE",
            "details": {"issuer_did": "did:example:issuer", "subject_did": "did:example:subject"}
        }
    
    @pytest.fixture
    def sample_audit_log(self):
        """Sample audit log model for testing."""
        return AuditLog(
            id=str(uuid.uuid4()),
            mandate_id=str(uuid.uuid4()),
            event_type="CREATE",
            timestamp=datetime.utcnow(),
            details={"issuer_did": "did:example:issuer", "subject_did": "did:example:subject"}
        )
    
    @pytest.fixture
    def sample_audit_logs(self):
        """Multiple sample audit logs for testing."""
        mandate_id = str(uuid.uuid4())
        base_time = datetime.utcnow()
        
        return [
            AuditLog(
                id=str(uuid.uuid4()),
                mandate_id=mandate_id,
                event_type="CREATE",
                timestamp=base_time,
                details={"issuer_did": "did:example:issuer"}
            ),
            AuditLog(
                id=str(uuid.uuid4()),
                mandate_id=mandate_id,
                event_type="VERIFY",
                timestamp=base_time - timedelta(minutes=1),
                details={"verification_status": "VALID"}
            ),
            AuditLog(
                id=str(uuid.uuid4()),
                mandate_id=mandate_id,
                event_type="UPDATE",
                timestamp=base_time - timedelta(minutes=2),
                details={"updated_fields": ["scope", "amount_limit"]}
            ),
            AuditLog(
                id=str(uuid.uuid4()),
                mandate_id=mandate_id,
                event_type="SOFT_DELETE",
                timestamp=base_time - timedelta(minutes=3),
                details={"retention_days": 90}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_create_audit_log_success(self, audit_service, mock_db_session, sample_audit_log_data, sample_audit_log):
        """Test creating an audit log successfully."""
        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        # Mock the refresh to set the id and timestamp
        def mock_refresh(audit_log):
            audit_log.id = sample_audit_log.id
            audit_log.timestamp = sample_audit_log.timestamp
        
        mock_db_session.refresh.side_effect = mock_refresh
        
        result = await audit_service.create_audit_log(sample_audit_log_data)
        
        assert str(result.mandate_id) == sample_audit_log_data["mandate_id"]
        assert result.event_type == sample_audit_log_data["event_type"]
        assert result.details == sample_audit_log_data["details"]
        assert result.id is not None
        assert result.timestamp is not None
        
        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_mandate_success(self, audit_service, mock_db_session, sample_audit_logs):
        """Test getting audit logs by mandate ID successfully."""
        mandate_id = sample_audit_logs[0].mandate_id
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.get_audit_logs_by_mandate(mandate_id, limit=100, offset=0)
        
        assert len(result["logs"]) == 4
        assert result["total"] == 4
        assert result["limit"] == 100
        assert result["offset"] == 0
        
        # Verify logs are ordered by timestamp (newest first)
        timestamps = [log.timestamp for log in result["logs"]]
        assert timestamps == sorted(timestamps, reverse=True)
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_mandate_with_pagination(self, audit_service, mock_db_session, sample_audit_logs):
        """Test getting audit logs by mandate ID with pagination."""
        mandate_id = sample_audit_logs[0].mandate_id
        
        # Mock database query to return first 2 logs
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs[:2]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.get_audit_logs_by_mandate(mandate_id, limit=2, offset=0)
        
        assert len(result["logs"]) == 2
        assert result["limit"] == 2
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_by_mandate_empty(self, audit_service, mock_db_session):
        """Test getting audit logs for a mandate with no audit history."""
        mandate_id = str(uuid.uuid4())
        
        # Mock database query to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.get_audit_logs_by_mandate(mandate_id)
        
        assert len(result["logs"]) == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_search_audit_logs_success(self, audit_service, mock_db_session, sample_audit_logs):
        """Test searching audit logs successfully."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.search_audit_logs(
            mandate_id=sample_audit_logs[0].mandate_id,
            event_type="CREATE",
            limit=100,
            offset=0
        )
        
        assert len(result["audit_logs"]) == 4
        assert result["total"] == 4
        assert result["limit"] == 100
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_search_audit_logs_with_filters(self, audit_service, mock_db_session, sample_audit_logs):
        """Test searching audit logs with various filters."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test with event_type filter
        result = await audit_service.search_audit_logs(event_type="CREATE")
        assert len(result["audit_logs"]) == 4
        
        # Test with mandate_id filter
        result = await audit_service.search_audit_logs(mandate_id=sample_audit_logs[0].mandate_id)
        assert len(result["audit_logs"]) == 4
    
    @pytest.mark.asyncio
    async def test_search_audit_logs_with_date_range(self, audit_service, mock_db_session, sample_audit_logs):
        """Test searching audit logs with date range filters."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        start_date = datetime.utcnow() - timedelta(hours=1)
        end_date = datetime.utcnow()
        
        result = await audit_service.search_audit_logs(
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(result["audit_logs"]) == 4
    
    @pytest.mark.asyncio
    async def test_search_audit_logs_with_pagination(self, audit_service, mock_db_session, sample_audit_logs):
        """Test searching audit logs with pagination."""
        # Mock database query to return first 2 logs
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_audit_logs[:2]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.search_audit_logs(limit=2, offset=0)
        
        assert len(result["audit_logs"]) == 2
        assert result["limit"] == 2
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_search_audit_logs_empty(self, audit_service, mock_db_session):
        """Test searching audit logs when no results found."""
        # Mock database query to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await audit_service.search_audit_logs()
        
        assert len(result["audit_logs"]) == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_audit_log_by_id_success(self, audit_service, mock_db_session, sample_audit_log):
        """Test getting an audit log by ID successfully."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_audit_log)
        mock_db_session.execute.return_value = mock_result
        
        result = await audit_service.get_audit_log_by_id(sample_audit_log.id)
        
        assert result is not None
        assert result.id == sample_audit_log.id
        assert result.event_type == sample_audit_log.event_type
        assert result.mandate_id == sample_audit_log.mandate_id
    
    @pytest.mark.asyncio
    async def test_get_audit_log_by_id_not_found(self, audit_service, mock_db_session):
        """Test getting an audit log that doesn't exist."""
        audit_log_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await audit_service.get_audit_log_by_id(audit_log_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_log_mandate_event_success(self, audit_service, mock_db_session, sample_audit_log):
        """Test logging a mandate event successfully."""
        mandate_id = sample_audit_log.mandate_id
        event_type = sample_audit_log.event_type
        details = sample_audit_log.details
        
        # Mock the log_event method
        with patch.object(audit_service, 'log_event', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = sample_audit_log
            
            result = await audit_service.log_mandate_event(mandate_id, event_type, details)
            
            assert result is not None
            assert str(result.mandate_id) == str(mandate_id)
            assert result.event_type == event_type
            assert result.details == details
            
            # Verify log_event was called
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_mandate_event_with_optional_details(self, audit_service, mock_db_session, sample_audit_log):
        """Test logging a mandate event with optional details."""
        mandate_id = sample_audit_log.mandate_id
        event_type = sample_audit_log.event_type
        
        # Mock the log_event method
        with patch.object(audit_service, 'log_event', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = sample_audit_log
            
            result = await audit_service.log_mandate_event(mandate_id, event_type)
            
            assert result is not None
            assert str(result.mandate_id) == str(mandate_id)
            assert result.event_type == event_type
            
            # Verify log_event was called
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_audit_service_database_error(self, audit_service, mock_db_session, sample_audit_log_data):
        """Test audit service error handling."""
        # Mock database to raise an exception
        mock_db_session.add.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await audit_service.create_audit_log(sample_audit_log_data)
    
    @pytest.mark.asyncio
    async def test_audit_service_validation_error(self, audit_service, mock_db_session):
        """Test audit service validation error handling."""
        # Test with invalid event_type
        invalid_audit_log_data = {
            "mandate_id": str(uuid.uuid4()),
            "event_type": "INVALID_EVENT_TYPE",
            "details": {}
        }
        
        with pytest.raises(ValueError):
            await audit_service.create_audit_log(invalid_audit_log_data)
    
    @pytest.mark.asyncio
    async def test_audit_service_pagination_validation(self, audit_service, mock_db_session):
        """Test audit service pagination validation."""
        # Test with negative limit
        with pytest.raises(ValueError, match="Limit must be positive"):
            await audit_service.get_audit_logs_by_mandate("test-id", limit=-1)
        
        # Test with negative offset
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            await audit_service.get_audit_logs_by_mandate("test-id", offset=-1)
        
        # Test with too large limit
        with pytest.raises(ValueError, match="Limit cannot exceed 1000"):
            await audit_service.get_audit_logs_by_mandate("test-id", limit=1001)
    
    @pytest.mark.asyncio
    async def test_audit_service_date_validation(self, audit_service, mock_db_session):
        """Test audit service date validation."""
        # Test with invalid date range (start_date > end_date)
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() - timedelta(hours=1)
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            await audit_service.search_audit_logs(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
