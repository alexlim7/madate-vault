"""
Customer service for multi-tenancy support.
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import uuid

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Service class for customer operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Create a new customer.
        
        Args:
            customer_data: Customer creation data
            
        Returns:
            Created customer object
        """
        # Check if email already exists
        if customer_data.email:
            existing_customer = await self.get_customer_by_email(customer_data.email)
            if existing_customer:
                raise ValueError(f"Customer with email {customer_data.email} already exists")
        
        customer = Customer(
            name=customer_data.name,
            email=customer_data.email
        )
        
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        
        return customer
    
    async def get_customer_by_tenant_id(self, tenant_id: str) -> Optional[Customer]:
        """Get customer by tenant ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email."""
        result = await self.db.execute(
            select(Customer).where(Customer.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_customer(self, tenant_id: str, update_data: CustomerUpdate) -> Optional[Customer]:
        """Update a customer."""
        customer = await self.get_customer_by_tenant_id(tenant_id)
        if not customer:
            return None
        
        # Check if email already exists (if updating email)
        if update_data.email and update_data.email != customer.email:
            existing_customer = await self.get_customer_by_email(update_data.email)
            if existing_customer:
                raise ValueError(f"Customer with email {update_data.email} already exists")
        
        # Update fields
        if update_data.name is not None:
            customer.name = update_data.name
        if update_data.email is not None:
            customer.email = update_data.email
        if update_data.is_active is not None:
            customer.is_active = update_data.is_active
        
        await self.db.commit()
        await self.db.refresh(customer)
        
        return customer
    
    async def deactivate_customer(self, tenant_id: str) -> bool:
        """Deactivate a customer."""
        customer = await self.get_customer_by_tenant_id(tenant_id)
        if not customer:
            return False
        
        customer.is_active = False
        await self.db.commit()
        
        return True
    
    async def activate_customer(self, tenant_id: str) -> bool:
        """Activate a customer."""
        customer = await self.get_customer_by_tenant_id(tenant_id)
        if not customer:
            return False
        
        customer.is_active = True
        await self.db.commit()
        
        return True
    
    async def list_customers(self, limit: int = 100, offset: int = 0, 
                           is_active: Optional[bool] = None, 
                           search: Optional[str] = None) -> Dict[str, Any]:
        """
        List customers with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            is_active: Filter by active status
            search: Search in name and email
            
        Returns:
            Dictionary with customers and pagination info
        """
        query = select(Customer)
        conditions = []
        
        if is_active is not None:
            conditions.append(Customer.is_active == is_active)
        
        if search:
            conditions.append(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.email.ilike(f"%{search}%")
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(Customer.tenant_id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        query = query.order_by(Customer.created_at.desc())
        
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return {
            "customers": customers,
            "total": total,
            "limit": limit,
            "offset": offset
        }


