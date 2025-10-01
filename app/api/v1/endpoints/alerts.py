"""
Alert API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.alert import (
    AlertResponse, AlertCreate, AlertUpdate, AlertSearch, AlertSearchResponse
)
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("/", response_model=AlertSearchResponse)
async def get_alerts(
    tenant_id: str = Query(..., description="Tenant ID"),
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_resolved: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> AlertSearchResponse:
    """
    Get alerts with optional filtering.
    """
    try:
        alert_service = AlertService(db)
        result = await alert_service.get_alerts(
            tenant_id=tenant_id,
            alert_type=alert_type,
            severity=severity,
            is_read=is_read,
            is_resolved=is_resolved,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        alerts = [AlertResponse.model_validate(alert) for alert in result["alerts"]]
        
        return AlertSearchResponse(
            alerts=alerts,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Get alert by ID.
    """
    try:
        from sqlalchemy import select
        from app.models.alert import Alert
        import uuid
        
        query = select(Alert).where(
            Alert.id == uuid.UUID(alert_id),
            Alert.tenant_id == uuid.UUID(tenant_id)
        )
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        return AlertResponse.model_validate(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )


@router.post("/", response_model=AlertResponse, status_code=http_status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Create a new alert.
    """
    try:
        alert_service = AlertService(db)
        alert = await alert_service.create_alert(
            tenant_id=tenant_id,
            alert_data=alert_data
        )
        
        return AlertResponse.model_validate(alert)
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_data: AlertUpdate,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Update an alert.
    """
    try:
        from sqlalchemy import select
        from app.models.alert import Alert
        import uuid
        
        query = select(Alert).where(
            Alert.id == uuid.UUID(alert_id),
            Alert.tenant_id == uuid.UUID(tenant_id)
        )
        result = await db.execute(query)
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Update fields
        if alert_data.is_read is not None:
            alert.is_read = alert_data.is_read
        if alert_data.is_resolved is not None:
            alert.is_resolved = alert_data.is_resolved
            if alert_data.is_resolved:
                from datetime import datetime
                alert.resolved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(alert)
        
        return AlertResponse.model_validate(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )


@router.post("/{alert_id}/mark-read", response_model=AlertResponse)
async def mark_alert_as_read(
    alert_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Mark an alert as read.
    """
    try:
        alert_service = AlertService(db)
        success = await alert_service.mark_alert_as_read(alert_id, tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Get updated alert
        from sqlalchemy import select
        from app.models.alert import Alert
        import uuid
        
        query = select(Alert).where(
            Alert.id == uuid.UUID(alert_id),
            Alert.tenant_id == uuid.UUID(tenant_id)
        )
        result = await db.execute(query)
        alert = result.scalar_one()
        
        return AlertResponse.model_validate(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark alert as read: {str(e)}"
        )


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    tenant_id: str = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db)
) -> AlertResponse:
    """
    Resolve an alert.
    """
    try:
        alert_service = AlertService(db)
        success = await alert_service.resolve_alert(alert_id, tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Get updated alert
        from sqlalchemy import select
        from app.models.alert import Alert
        import uuid
        
        query = select(Alert).where(
            Alert.id == uuid.UUID(alert_id),
            Alert.tenant_id == uuid.UUID(tenant_id)
        )
        result = await db.execute(query)
        alert = result.scalar_one()
        
        return AlertResponse.model_validate(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )


@router.post("/check-expiring", status_code=http_status.HTTP_200_OK)
async def check_expiring_mandates(
    tenant_id: str = Query(..., description="Tenant ID"),
    days_threshold: int = Query(7, ge=1, le=30, description="Days to check ahead"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for mandates expiring within the specified days and create alerts.
    """
    try:
        alert_service = AlertService(db)
        alerts_created = await alert_service.check_expiring_mandates(days_threshold)
        
        return {"message": f"Created {alerts_created} alerts for expiring mandates"}
        
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check expiring mandates: {str(e)}"
        )


