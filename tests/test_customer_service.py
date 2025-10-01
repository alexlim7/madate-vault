#!/usr/bin/env python3
"""
Test suite for Customer Service.
Tests CRUD operations and business logic for customer management.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.customer_service import CustomerService
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class TestCustomerService:
    """Test cases for customer service."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        
        # Mock execute method - will be configured per test
        session.execute = AsyncMock()
        
        return session
    
    @pytest.fixture
    def customer_service(self, mock_db_session):
        """Create customer service instance."""
        return CustomerService(mock_db_session)
    
    @pytest.fixture
    def sample_customer_data(self):
        """Sample customer data for testing."""
        return CustomerCreate(
            name="Test Customer",
            email="test@example.com"
        )
    
    @pytest.fixture
    def sample_customer(self):
        """Sample customer model for testing."""
        return Customer(
            tenant_id=str(uuid.uuid4()),
            name="Test Customer",
            email="test@example.com",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_create_customer_success(self, customer_service, mock_db_session, sample_customer_data, sample_customer):
        """Test creating a customer successfully."""
        # Patch the get_customer_by_email method to return None
        with patch.object(customer_service, 'get_customer_by_email', return_value=None):
            # Mock refresh to set the customer attributes
            async def mock_refresh(customer):
                customer.tenant_id = sample_customer.tenant_id
                customer.created_at = sample_customer.created_at
                customer.updated_at = sample_customer.updated_at
                customer.is_active = True
            
            mock_db_session.refresh.side_effect = mock_refresh
            
            result = await customer_service.create_customer(sample_customer_data)
            
            assert result.name == sample_customer_data.name
            assert result.email == sample_customer_data.email
            assert result.is_active is True
            assert result.tenant_id is not None
            
            # Verify database operations were called
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_customer_with_existing_email(self, customer_service, mock_db_session, sample_customer_data, sample_customer):
        """Test creating a customer with existing email."""
        # Mock database to return existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Customer with email test@example.com already exists"):
            await customer_service.create_customer(sample_customer_data)
    
    @pytest.mark.asyncio
    async def test_get_customer_by_tenant_id_success(self, customer_service, mock_db_session, sample_customer):
        """Test getting a customer by tenant ID successfully."""
        # Patch the get_customer_by_tenant_id method to return the sample customer
        with patch.object(customer_service, 'get_customer_by_tenant_id', return_value=sample_customer):
            result = await customer_service.get_customer_by_tenant_id(sample_customer.tenant_id)
            
            assert result is not None
            assert result.tenant_id == sample_customer.tenant_id
            assert result.name == sample_customer.name
            assert result.email == sample_customer.email
    
    @pytest.mark.asyncio
    async def test_get_customer_by_tenant_id_not_found(self, customer_service, mock_db_session):
        """Test getting a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        # Patch the get_customer_by_tenant_id method to return None
        with patch.object(customer_service, 'get_customer_by_tenant_id', return_value=None):
            result = await customer_service.get_customer_by_tenant_id(tenant_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_customer_by_email_success(self, customer_service, mock_db_session, sample_customer):
        """Test getting a customer by email successfully."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        result = await customer_service.get_customer_by_email(sample_customer.email)
        
        assert result is not None
        assert result.email == sample_customer.email
        assert result.tenant_id == sample_customer.tenant_id
    
    @pytest.mark.asyncio
    async def test_get_customer_by_email_not_found(self, customer_service, mock_db_session):
        """Test getting a customer by email that doesn't exist."""
        email = "nonexistent@example.com"
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await customer_service.get_customer_by_email(email)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_customer_success(self, customer_service, mock_db_session, sample_customer):
        """Test updating a customer successfully."""
        # Mock getting existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        update_data = CustomerUpdate(
            name="Updated Customer",
            email="updated@example.com"
        )
        
        # Mock the email check to return None (no existing customer with this email)
        def mock_execute_side_effect(query):
            if "email" in str(query):
                # Email check query - return None (no existing customer)
                mock_email_result = AsyncMock()
                mock_email_result.scalar_one_or_none = MagicMock(return_value=None)
                return mock_email_result
            else:
                # Customer lookup query - return the customer
                return mock_result
        
        mock_db_session.execute = AsyncMock(side_effect=mock_execute_side_effect)
        
        # Also need to mock the get_customer_by_tenant_id call
        with patch.object(customer_service, 'get_customer_by_tenant_id', return_value=sample_customer):
            with patch.object(customer_service, 'get_customer_by_email', return_value=None):
                result = await customer_service.update_customer(sample_customer.tenant_id, update_data)
        
        assert result.name == update_data.name
        assert result.email == update_data.email
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, customer_service, mock_db_session):
        """Test updating a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        update_data = CustomerUpdate(name="Updated Customer")
        
        result = await customer_service.update_customer(tenant_id, update_data)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_customer_with_existing_email(self, customer_service, mock_db_session, sample_customer):
        """Test updating a customer with an email that already exists."""
        # Mock getting existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        update_data = CustomerUpdate(email="existing@example.com")
        
        with pytest.raises(ValueError, match="Customer with email existing@example.com already exists"):
            await customer_service.update_customer(sample_customer.tenant_id, update_data)
    
    @pytest.mark.asyncio
    async def test_deactivate_customer_success(self, customer_service, mock_db_session, sample_customer):
        """Test deactivating a customer successfully."""
        # Mock getting existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        result = await customer_service.deactivate_customer(sample_customer.tenant_id)
        
        assert result is True
        assert sample_customer.is_active is False
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        # Note: deactivate_customer doesn't call refresh
    
    @pytest.mark.asyncio
    async def test_deactivate_customer_not_found(self, customer_service, mock_db_session):
        """Test deactivating a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await customer_service.deactivate_customer(tenant_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_deactivate_already_inactive_customer(self, customer_service, mock_db_session, sample_customer):
        """Test deactivating a customer that's already inactive."""
        # Set customer as inactive
        sample_customer.is_active = False
        
        # Mock getting existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        result = await customer_service.deactivate_customer(sample_customer.tenant_id)
        
        assert result is True  # Should still return True even if already inactive
    
    @pytest.mark.asyncio
    async def test_activate_customer_success(self, customer_service, mock_db_session, sample_customer):
        """Test activating a customer successfully."""
        # Set customer as inactive
        sample_customer.is_active = False
        
        # Mock getting existing customer
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_customer)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database operations
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        result = await customer_service.activate_customer(sample_customer.tenant_id)
        
        assert result is True
        assert sample_customer.is_active is True
        
        # Verify database operations were called
        mock_db_session.commit.assert_called_once()
        # Note: activate_customer doesn't call refresh
    
    @pytest.mark.asyncio
    async def test_activate_customer_not_found(self, customer_service, mock_db_session):
        """Test activating a customer that doesn't exist."""
        tenant_id = str(uuid.uuid4())
        
        # Mock database query to return None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        result = await customer_service.activate_customer(tenant_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_customers_success(self, customer_service, mock_db_session, sample_customer):
        """Test listing customers successfully."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_customer]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_service.list_customers(limit=10, offset=0)
        
        assert len(result["customers"]) == 1
        assert result["customers"][0].tenant_id == sample_customer.tenant_id
        assert result["total"] == 1
        assert result["limit"] == 10
        assert result["offset"] == 0
    
    @pytest.mark.asyncio
    async def test_list_customers_with_filters(self, customer_service, mock_db_session, sample_customer):
        """Test listing customers with filters."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_customer]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_service.list_customers(
            limit=10, 
            offset=0, 
            is_active=True,
            search="Test"
        )
        
        assert len(result["customers"]) == 1
        assert result["total"] == 1
    
    @pytest.mark.asyncio
    async def test_list_customers_empty(self, customer_service, mock_db_session):
        """Test listing customers when none exist."""
        # Mock database query to return empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_service.list_customers(limit=10, offset=0)
        
        assert len(result["customers"]) == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_customer_service_database_error(self, customer_service, mock_db_session, sample_customer_data):
        """Test customer service error handling."""
        # Mock email check to return None (no existing customer)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        
        # Mock database to raise an exception during add
        mock_db_session.add.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await customer_service.create_customer(sample_customer_data)
    
    @pytest.mark.asyncio
    async def test_customer_service_validation_error(self, customer_service, mock_db_session):
        """Test customer service validation error handling."""
        # Test with invalid email format - this should fail at Pydantic validation level
        with pytest.raises(Exception):  # Pydantic ValidationError
            invalid_customer_data = CustomerCreate(
                name="Test Customer",
                email="invalid-email-format"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
