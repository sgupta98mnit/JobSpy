"""
API v1 router configuration.

Combines all API endpoints under the v1 namespace.
"""

from fastapi import APIRouter

from .endpoints import health


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Placeholder for future endpoints
# api_router.include_router(search.router, prefix="/search", tags=["search"])
# api_router.include_router(export.router, prefix="/export", tags=["export"])