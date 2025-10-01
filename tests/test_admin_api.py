#!/usr/bin/env python3
"""
Test suite for Admin API endpoints.
Tests administrative operations like cleanup and system status.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db


class TestAdminAPI:
    """Test cases for admin API endpoints."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session
    
    @pytest.fixture
    def client(self, mock_db_session):
        """Create a test client with mocked database."""
        app.dependency_overrides[get_db] = lambda: mock_db_session
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    
    def test_cleanup_expired_retention_success(self, client, mock_db_session):
        """Test successful cleanup of expired retention mandates."""
        with patch('app.services.mandate_service.MandateService.cleanup_expired_retention') as mock_cleanup:
            mock_cleanup.return_value = 5  # Mock 5 mandates cleaned up
            
            response = client.post("/api/v1/admin/cleanup-retention")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["cleaned_count"] == 5
            assert "Successfully cleaned up 5 mandates" in response_data["message"]
            
            # Verify the service method was called
            mock_cleanup.assert_called_once()
    
    def test_cleanup_expired_retention_no_cleanup(self, client, mock_db_session):
        """Test cleanup when no mandates need cleaning."""
        with patch('app.services.mandate_service.MandateService.cleanup_expired_retention') as mock_cleanup:
            mock_cleanup.return_value = 0  # No mandates cleaned up
            
            response = client.post("/api/v1/admin/cleanup-retention")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["cleaned_count"] == 0
            assert "Successfully cleaned up 0 mandates" in response_data["message"]
    
    def test_cleanup_expired_retention_error(self, client, mock_db_session):
        """Test cleanup when an error occurs."""
        with patch('app.services.mandate_service.MandateService.cleanup_expired_retention') as mock_cleanup:
            mock_cleanup.side_effect = Exception("Database connection failed")
            
            response = client.post("/api/v1/admin/cleanup-retention")
            
            assert response.status_code == 500
            response_data = response.json()
            assert "Internal server error" in response_data["detail"]
            assert "Database connection failed" in response_data["detail"]
    
    def test_get_truststore_status_success(self, client):
        """Test getting truststore status."""
        with patch('app.services.verification_service.verification_service.get_truststore_status') as mock_status:
            mock_status.return_value = {
                "total_issuers": 3,
                "cached_issuers": 2,
                "last_refresh": "2024-01-01T12:00:00Z",
                "refresh_errors": 0,
                "status": "healthy"
            }
            
            response = client.get("/api/v1/admin/truststore-status")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["total_issuers"] == 3
            assert response_data["cached_issuers"] == 2
            assert response_data["status"] == "healthy"
    
    def test_get_truststore_status_with_errors(self, client):
        """Test getting truststore status when there are refresh errors."""
        with patch('app.services.verification_service.verification_service.get_truststore_status') as mock_status:
            mock_status.return_value = {
                "total_issuers": 5,
                "cached_issuers": 3,
                "last_refresh": "2024-01-01T12:00:00Z",
                "refresh_errors": 2,
                "status": "degraded",
                "error_details": [
                    "Failed to fetch JWKS for did:example:issuer1",
                    "Timeout fetching JWKS for did:example:issuer2"
                ]
            }
            
            response = client.get("/api/v1/admin/truststore-status")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["total_issuers"] == 5
            assert response_data["cached_issuers"] == 3
            assert response_data["refresh_errors"] == 2
            assert response_data["status"] == "degraded"
            assert "error_details" in response_data
    
    def test_get_truststore_status_error(self, client):
        """Test getting truststore status when an error occurs."""
        with patch('app.services.verification_service.verification_service.get_truststore_status') as mock_status:
            mock_status.side_effect = Exception("Truststore service unavailable")
            
            response = client.get("/api/v1/admin/truststore-status")
            
            assert response.status_code == 500
            response_data = response.json()
            assert "Internal server error" in response_data["detail"]
            assert "Truststore service unavailable" in response_data["detail"]
    
    def test_admin_endpoints_require_authentication(self, client):
        """Test that admin endpoints are properly secured (future enhancement)."""
        # Note: Currently admin endpoints don't have authentication
        # This test documents the expectation for future implementation
        
        # Test cleanup endpoint
        response = client.post("/api/v1/admin/cleanup-retention")
        assert response.status_code in [200, 500]  # Should work without auth currently
        
        # Test truststore status endpoint
        response = client.get("/api/v1/admin/truststore-status")
        assert response.status_code in [200, 500]  # Should work without auth currently
        
        # TODO: When authentication is implemented, these should return 401/403
        # assert response.status_code == 401  # Unauthorized
    
    def test_cleanup_retention_with_large_count(self, client, mock_db_session):
        """Test cleanup with a large number of mandates."""
        with patch('app.services.mandate_service.MandateService.cleanup_expired_retention') as mock_cleanup:
            mock_cleanup.return_value = 1000  # Large cleanup count
            
            response = client.post("/api/v1/admin/cleanup-retention")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["cleaned_count"] == 1000
            assert "Successfully cleaned up 1000 mandates" in response_data["message"]
    
    def test_truststore_status_empty(self, client):
        """Test truststore status when no issuers are cached."""
        with patch('app.services.verification_service.verification_service.get_truststore_status') as mock_status:
            mock_status.return_value = {
                "total_issuers": 0,
                "cached_issuers": 0,
                "last_refresh": None,
                "refresh_errors": 0,
                "status": "empty"
            }
            
            response = client.get("/api/v1/admin/truststore-status")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["total_issuers"] == 0
            assert response_data["cached_issuers"] == 0
            assert response_data["status"] == "empty"
            assert response_data["last_refresh"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
