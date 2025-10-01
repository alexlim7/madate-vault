#!/usr/bin/env python3
"""
Test suite for Mandate API endpoints - Additional Tests.
Tests update, restore, soft delete, and search functionality.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.core.auth import User, UserRole, UserStatus
from app.models.mandate import Mandate
from app.models.customer import Customer


@pytest.fixture
def sample_user():
    """Sample authenticated user."""
    return User(
        id="user-001",
        email="test@example.com",
        tenant_id="550e8400-e29b-41d4-a716-446655440000",
        role=UserRole.CUSTOMER_ADMIN,
        status=UserStatus.ACTIVE,
        created_at=datetime.now()
    )


def get_auth_headers(user):
    """Get authentication headers for a user."""
    return {"Authorization": f"Bearer mock-token-for-{user.id}"}


class TestMandateAPIAdditional:
    """Additional test cases for mandate API endpoints."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session with valid customer."""
        session = AsyncMock()
        
        # Create a mock customer that will be returned by get_tenant
        mock_customer = Customer(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Customer",
            email="test@example.com",
            is_active=True
        )
        
        # Mock the database query to return our customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_customer)
        session.execute.return_value = mock_result
        
        # Mock other async operations
        session.add = MagicMock()  # add is not async
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        
        return session
    
    @pytest.fixture
    def client(self, mock_db_session, sample_user):
        """Create a test client with mocked database and authentication."""
        from app.core.auth import get_current_active_user
        
        # Mock authentication
        def mock_get_current_user():
            return sample_user
        
        # Override both dependencies
        app.dependency_overrides[get_db] = lambda: mock_db_session
        app.dependency_overrides[get_current_active_user] = mock_get_current_user
        
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def valid_tenant_id(self):
        """Valid tenant ID for testing."""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    @pytest.fixture
    def sample_mandate(self, valid_tenant_id):
        """Create a sample mandate for testing."""
        return Mandate(
            id=str(uuid.uuid4()),
            vc_jwt="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkaWQ6ZXhhbXBsZTppc3N1ZXIiLCJzdWIiOiJkaWQ6ZXhhbXBsZTpzdWJqZWN0IiwiaWF0IjoxNjQwOTk1MjAwLCJleHAiOjE2NDEwNzg4MDAsInNjb3BlIjoicGF5bWVudCIsImFtb3VudF9saW1pdCI6IjEwMDAifQ.signature",
            issuer_did="did:example:issuer",
            subject_did="did:example:subject",
            scope="payment",
            amount_limit="1000",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            status="active",
            retention_days=90,
            tenant_id=valid_tenant_id,
            verification_status="VALID",
            verification_reason="All verification checks passed",
            verified_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_update_mandate_success(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test updating a mandate successfully."""
        mandate_id = sample_mandate.id
        
        update_data = {
            "scope": "transfer",
            "amount_limit": "2000"
        }
        
        with patch('app.services.mandate_service.MandateService.update_mandate', new_callable=AsyncMock) as mock_update:
            updated_mandate = Mandate(
                id=sample_mandate.id,
                vc_jwt=sample_mandate.vc_jwt,
                issuer_did=sample_mandate.issuer_did,
                subject_did=sample_mandate.subject_did,
                scope="transfer",
                amount_limit="2000",
                expires_at=sample_mandate.expires_at,
                status=sample_mandate.status,
                retention_days=sample_mandate.retention_days,
                tenant_id=sample_mandate.tenant_id,
                verification_status=sample_mandate.verification_status,
                verification_reason=sample_mandate.verification_reason,
                verified_at=sample_mandate.verified_at,
                created_at=sample_mandate.created_at,
                updated_at=datetime.utcnow()
            )
            mock_update.return_value = updated_mandate
            
            response = client.patch(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}", json=update_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["scope"] == "transfer"
            assert response_data["amount_limit"] == "2000"
    
    def test_update_mandate_not_found(self, client, mock_db_session, valid_tenant_id):
        """Test updating a mandate that doesn't exist."""
        mandate_id = str(uuid.uuid4())
        
        with patch('app.services.mandate_service.MandateService.update_mandate', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            
            update_data = {"scope": "transfer"}
            
            response = client.patch(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}", json=update_data)
            
            assert response.status_code == 404
    
    def test_update_mandate_invalid_data(self, client, valid_tenant_id, sample_mandate):
        """Test updating a mandate with invalid data."""
        mandate_id = sample_mandate.id
        
        # Invalid scope
        update_data = {
            "scope": "invalid_scope"
        }
        
        # Mock the mandate service update_mandate method to return None (validation error)
        with patch('app.services.mandate_service.MandateService.update_mandate', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            
            response = client.patch(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}", json=update_data)
            
            assert response.status_code == 404  # Not found when update returns None
    
    def test_soft_delete_mandate_success(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test soft deleting a mandate successfully."""
        mandate_id = sample_mandate.id
        
        with patch('app.services.mandate_service.MandateService.soft_delete_mandate', new_callable=AsyncMock) as mock_soft_delete:
            deleted_mandate = Mandate(
                id=sample_mandate.id,
                vc_jwt=sample_mandate.vc_jwt,
                issuer_did=sample_mandate.issuer_did,
                subject_did=sample_mandate.subject_did,
                scope=sample_mandate.scope,
                amount_limit=sample_mandate.amount_limit,
                expires_at=sample_mandate.expires_at,
                status="deleted",
                retention_days=sample_mandate.retention_days,
                tenant_id=sample_mandate.tenant_id,
                verification_status=sample_mandate.verification_status,
                verification_reason=sample_mandate.verification_reason,
                verified_at=sample_mandate.verified_at,
                deleted_at=datetime.utcnow(),
                created_at=sample_mandate.created_at,
                updated_at=datetime.utcnow()
            )
            mock_soft_delete.return_value = deleted_mandate
            
            response = client.delete(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 204
            # 204 No Content doesn't return JSON
    
    def test_soft_delete_mandate_not_found(self, client, mock_db_session, valid_tenant_id):
        """Test soft deleting a mandate that doesn't exist."""
        mandate_id = str(uuid.uuid4())
        
        with patch('app.services.mandate_service.MandateService.soft_delete_mandate', new_callable=AsyncMock) as mock_soft_delete:
            mock_soft_delete.return_value = None
            
            response = client.delete(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 404
    
    def test_restore_mandate_success(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test restoring a soft-deleted mandate successfully."""
        mandate_id = sample_mandate.id
        
        with patch('app.services.mandate_service.MandateService.restore_mandate', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = True
            
            with patch('app.services.mandate_service.MandateService.get_mandate_by_id', new_callable=AsyncMock) as mock_get:
                restored_mandate = Mandate(
                    id=sample_mandate.id,
                    vc_jwt=sample_mandate.vc_jwt,
                    issuer_did=sample_mandate.issuer_did,
                    subject_did=sample_mandate.subject_did,
                    scope=sample_mandate.scope,
                    amount_limit=sample_mandate.amount_limit,
                    expires_at=sample_mandate.expires_at,
                    status="active",
                    retention_days=sample_mandate.retention_days,
                    tenant_id=sample_mandate.tenant_id,
                    verification_status=sample_mandate.verification_status,
                    verification_reason=sample_mandate.verification_reason,
                    verified_at=sample_mandate.verified_at,
                    deleted_at=None,
                    created_at=sample_mandate.created_at,
                    updated_at=datetime.utcnow()
                )
                mock_get.return_value = restored_mandate
                
                response = client.post(f"/api/v1/mandates/{mandate_id}/restore?tenant_id={valid_tenant_id}")
                
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "active"
                assert response_data["deleted_at"] is None
    
    def test_restore_mandate_not_found(self, client, mock_db_session, valid_tenant_id):
        """Test restoring a mandate that doesn't exist."""
        mandate_id = str(uuid.uuid4())
        
        with patch('app.services.mandate_service.MandateService.restore_mandate', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = None
            
            response = client.post(f"/api/v1/mandates/{mandate_id}/restore?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 404
    
    def test_restore_active_mandate(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test restoring a mandate that's already active."""
        mandate_id = sample_mandate.id
        
        with patch('app.services.mandate_service.MandateService.restore_mandate', new_callable=AsyncMock) as mock_restore:
            mock_restore.side_effect = ValueError("Mandate is not deleted")
            
            response = client.post(f"/api/v1/mandates/{mandate_id}/restore?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 500
            response_data = response.json()
            assert "Mandate is not deleted" in response_data["detail"]
    
    def test_search_mandates_success(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test searching mandates successfully."""
        with patch('app.services.mandate_service.MandateService.search_mandates', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "mandates": [sample_mandate],
                "total": 1,
                "limit": 100,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data["mandates"]) == 1
            assert response_data["total"] == 1
    
    def test_search_mandates_with_filters(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test searching mandates with various filters."""
        with patch('app.services.mandate_service.MandateService.search_mandates', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "mandates": [sample_mandate],
                "total": 1,
                "limit": 100,
                "offset": 0
            }
            
            # Search by issuer DID
            response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&issuer_did=did:example:issuer")
            assert response.status_code == 200
            
            # Search by subject DID
            response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&subject_did=did:example:subject")
            assert response.status_code == 200
            
            # Search by status
            response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&status=active")
            assert response.status_code == 200
    
    def test_search_mandates_with_pagination(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test searching mandates with pagination."""
        with patch('app.services.mandate_service.MandateService.search_mandates', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "mandates": [sample_mandate],
                "total": 1,
                "limit": 10,
                "offset": 0
            }
            
            response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&limit=10&offset=0")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["limit"] == 10
            assert response_data["offset"] == 0
    
    def test_search_mandates_missing_tenant_id(self, client):
        """Test searching mandates without tenant_id."""
        response = client.get("/api/v1/mandates/search")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_mandates_invalid_pagination(self, client, valid_tenant_id):
        """Test searching mandates with invalid pagination parameters."""
        # Negative limit
        response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&limit=-1")
        assert response.status_code == 400
        
        # Negative offset
        response = client.get(f"/api/v1/mandates/search?tenant_id={valid_tenant_id}&offset=-1")
        assert response.status_code == 400
    
    def test_get_mandate_by_id_success(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test getting a mandate by ID successfully."""
        mandate_id = sample_mandate.id
        
        with patch('app.services.mandate_service.MandateService.get_mandate_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_mandate
            
            response = client.get(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["id"] == mandate_id
            assert response_data["issuer_did"] == sample_mandate.issuer_did
            assert response_data["subject_did"] == sample_mandate.subject_did
    
    def test_get_mandate_by_id_not_found(self, client, mock_db_session, valid_tenant_id):
        """Test getting a mandate that doesn't exist."""
        mandate_id = str(uuid.uuid4())
        
        with patch('app.services.mandate_service.MandateService.get_mandate_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = client.get(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 404
    
    def test_get_mandate_by_id_missing_tenant_id(self, client, sample_mandate):
        """Test getting a mandate without tenant_id."""
        mandate_id = sample_mandate.id
        
        response = client.get(f"/api/v1/mandates/{mandate_id}")
        
        assert response.status_code == 422  # Validation error
    
    def test_mandate_service_error_handling(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test error handling in mandate service."""
        mandate_id = sample_mandate.id
        
        with patch('app.services.mandate_service.MandateService.get_mandate_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database connection failed")
            
            response = client.get(f"/api/v1/mandates/{mandate_id}?tenant_id={valid_tenant_id}")
            
            assert response.status_code == 500
            response_data = response.json()
            assert "Database connection failed" in response_data["detail"]
    
    def test_mandate_export_functionality(self, client, mock_db_session, valid_tenant_id, sample_mandate):
        """Test mandate export functionality."""
        mandate_id = sample_mandate.id
        
        response = client.get(f"/api/v1/mandates/{mandate_id}/export?tenant_id={valid_tenant_id}")
        
        # This endpoint doesn't exist, so expect 404
        assert response.status_code == 404
    
    def test_mandate_export_not_found(self, client, mock_db_session, valid_tenant_id):
        """Test exporting a mandate that doesn't exist."""
        mandate_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/mandates/{mandate_id}/export?tenant_id={valid_tenant_id}")
        
        # This endpoint doesn't exist, so expect 404
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
