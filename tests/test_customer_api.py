#!/usr/bin/env python3
"""
Test suite for Customer API endpoints.
Tests CRUD operations for customer/tenant management.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.models.customer import Customer


class TestCustomerAPI:
    """Test cases for customer API endpoints."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.add = MagicMock()  # add is not async
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        # Mock the execute method to handle different query types
        def mock_execute(query):
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
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
    
    def test_create_customer(self, client, mock_db_session):
        """Test creating a new customer."""
        customer_data = {
            "name": "Test Customer",
            "email": "test@example.com"
        }
        
        with patch('app.services.customer_service.CustomerService.create_customer', new_callable=AsyncMock) as mock_create:
            mock_customer = Customer(
                tenant_id="550e8400-e29b-41d4-a716-446655440000",
                name="Test Customer",
                email="test@example.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_create.return_value = mock_customer
            
            response = client.post("/api/v1/customers/", json=customer_data)
            
            assert response.status_code == 201
            response_data = response.json()
            assert response_data["name"] == "Test Customer"
            assert response_data["email"] == "test@example.com"
            assert response_data["is_active"] is True
            assert "tenant_id" in response_data
    
    def test_create_customer_with_invalid_data(self, client):
        """Test creating customer with invalid data."""
        # Missing required fields
        response = client.post("/api/v1/customers/", json={})
        assert response.status_code == 422
        
        # Invalid email format
        response = client.post("/api/v1/customers/", json={
            "name": "Test",
            "email": "invalid-email"
        })
        assert response.status_code == 422
    
    def test_get_customer(self, client, mock_db_session):
        """Test getting a customer by tenant ID."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.get_customer_by_tenant_id', new_callable=AsyncMock) as mock_get:
            mock_customer = Customer(
                tenant_id=tenant_id,
                name="Test Customer",
                email="test@example.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_get.return_value = mock_customer
            
            response = client.get(f"/api/v1/customers/{tenant_id}")
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["tenant_id"] == tenant_id
            assert response_data["name"] == "Test Customer"
            assert response_data["email"] == "test@example.com"
    
    def test_get_nonexistent_customer(self, client, mock_db_session):
        """Test getting a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.get_customer_by_tenant_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = client.get(f"/api/v1/customers/{tenant_id}")
            
            assert response.status_code == 404
    
    def test_update_customer(self, client, mock_db_session):
        """Test updating a customer."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.update_customer', new_callable=AsyncMock) as mock_update:
            mock_customer = Customer(
                tenant_id=tenant_id,
                name="Updated Customer",
                email="updated@example.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            mock_update.return_value = mock_customer
            
            update_data = {
                "name": "Updated Customer",
                "email": "updated@example.com"
            }
            
            response = client.patch(f"/api/v1/customers/{tenant_id}", json=update_data)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["name"] == "Updated Customer"
            assert response_data["email"] == "updated@example.com"
    
    def test_update_nonexistent_customer(self, client, mock_db_session):
        """Test updating a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.update_customer', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            
            update_data = {"name": "Updated Customer"}
            
            response = client.patch(f"/api/v1/customers/{tenant_id}", json=update_data)
            
            assert response.status_code == 404
    
    def test_deactivate_customer(self, client, mock_db_session):
        """Test deactivating a customer."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.deactivate_customer', new_callable=AsyncMock) as mock_deactivate:
            mock_deactivate.return_value = True
            
            response = client.delete(f"/api/v1/customers/{tenant_id}")
            
            assert response.status_code == 204
    
    def test_deactivate_nonexistent_customer(self, client, mock_db_session):
        """Test deactivating a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        with patch('app.services.customer_service.CustomerService.deactivate_customer', new_callable=AsyncMock) as mock_deactivate:
            mock_deactivate.return_value = False
            
            response = client.delete(f"/api/v1/customers/{tenant_id}")
            
            assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
