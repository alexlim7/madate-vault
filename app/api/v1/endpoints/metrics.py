"""
Metrics endpoint for Prometheus scraping.
"""
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.monitoring import update_health_metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns all application metrics in Prometheus format.
    """
    # Update dynamic metrics before returning
    update_health_metrics()
    
    # Generate Prometheus metrics
    metrics_data = generate_latest()
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )

