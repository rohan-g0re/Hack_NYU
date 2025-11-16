"""
API v1 router aggregation.

WHAT: Combine all v1 endpoint routers
WHY: Single place to register all API routes
HOW: Include routers from endpoints with prefixes
"""

from fastapi import APIRouter

from .endpoints import status

# Create main v1 router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    status.router,
    prefix="/api/v1",
    tags=["status"]
)

# Additional routers will be added here as they're implemented
# api_router.include_router(negotiation.router, prefix="/api/v1", tags=["negotiation"])
# api_router.include_router(simulation.router, prefix="/api/v1", tags=["simulation"])

