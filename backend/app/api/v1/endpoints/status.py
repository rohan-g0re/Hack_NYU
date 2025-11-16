"""
Status and health check endpoints.

WHAT: Health monitoring for LLM providers and database
WHY: Quick diagnostics for frontend and ops
HOW: FastAPI endpoints calling provider ping and DB ping
"""

from fastapi import APIRouter

from ....llm.provider_factory import get_provider
from ....core.database import ping_database
from ....core.config import settings
from ....utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/llm/status")
async def llm_status():
    """
    Check LLM provider status.
    
    WHAT: Get health status of configured LLM provider and database
    WHY: Frontend can check before starting negotiations
    HOW: Call provider.ping() and database.ping_database()
    
    Returns:
        JSON with provider status and database status
    """
    try:
        provider = get_provider()
        llm_status = await provider.ping()
        
        # Convert dataclass to dict
        llm_dict = {
            "available": llm_status.available,
            "base_url": llm_status.base_url,
            "models": llm_status.models,
            "error": llm_status.error
        }
    except Exception as e:
        logger.error(f"Failed to get LLM status: {e}")
        llm_dict = {
            "available": False,
            "base_url": "unknown",
            "models": None,
            "error": str(e)
        }
    
    # Get database status
    db_status = ping_database()
    
    return {
        "llm": llm_dict,
        "database": db_status
    }


@router.get("/health")
async def health_check():
    """
    Overall application health check.
    
    WHAT: Comprehensive health status including version
    WHY: Ops and monitoring tools need simple health endpoint
    HOW: Aggregate LLM and DB status with app metadata
    
    Returns:
        JSON with overall health status
    """
    try:
        provider = get_provider()
        llm_status = await provider.ping()
        llm_available = llm_status.available
    except Exception as e:
        logger.error(f"Health check LLM failed: {e}")
        llm_available = False
    
    db_status = ping_database()
    db_available = db_status["available"]
    
    # Overall health is healthy if both components are up
    healthy = llm_available and db_available
    
    return {
        "status": "healthy" if healthy else "degraded",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
        "components": {
            "llm": {
                "available": llm_available,
                "provider": settings.LLM_PROVIDER
            },
            "database": {
                "available": db_available
            }
        }
    }

