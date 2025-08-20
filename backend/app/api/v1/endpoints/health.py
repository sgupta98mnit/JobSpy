"""
Health check endpoint.

Provides basic health monitoring for the application.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from ....core.config import settings


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    service: str


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic application health information.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.VERSION,
        service=settings.PROJECT_NAME
    )