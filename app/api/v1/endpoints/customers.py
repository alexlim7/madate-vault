"""
Customer API endpoints for multi-tenancy.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter()


@router.post("/", response_model=CustomerResponse, status_code=http_status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db)
) -> CustomerResponse:
    """
    Create a new customer (tenant).
    """
    try:
        customer_service = CustomerService(db)
        
        # Create customer
        customer = await customer_service.create_customer(customer_data)
        
        return CustomerResponse.model_validate(customer)
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=CustomerResponse)
async def get_customer(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
) -> CustomerResponse:
    """
    Get customer by tenant ID.
    """
    try:
        customer_service = CustomerService(db)
        
        # Get customer
        customer = await customer_service.get_customer_by_tenant_id(tenant_id)
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Customer with tenant ID {tenant_id} not found"
            )
        
        return CustomerResponse.model_validate(customer)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.patch("/{tenant_id}", response_model=CustomerResponse)
async def update_customer(
    tenant_id: str,
    update_data: CustomerUpdate,
    db: AsyncSession = Depends(get_db)
) -> CustomerResponse:
    """
    Update a customer.
    """
    try:
        customer_service = CustomerService(db)
        
        # Update customer
        customer = await customer_service.update_customer(tenant_id, update_data)
        if not customer:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Customer with tenant ID {tenant_id} not found"
            )
        
        return CustomerResponse.model_validate(customer)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{tenant_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def deactivate_customer(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a customer.
    """
    try:
        customer_service = CustomerService(db)
        
        # Deactivate customer
        success = await customer_service.deactivate_customer(tenant_id)
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Customer with tenant ID {tenant_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


