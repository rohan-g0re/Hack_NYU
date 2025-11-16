"""
Global error handling middleware.

WHAT: Translate exceptions to appropriate HTTP responses
WHY: Consistent error responses with proper status codes
HOW: FastAPI exception handlers for custom exceptions
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from ..llm.types import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderDisabledError,
    ProviderResponseError,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def provider_disabled_handler(request: Request, exc: ProviderDisabledError):
    """
    Handle ProviderDisabledError.
    
    WHAT: Provider is disabled in config
    WHY: User needs to enable provider or switch to another
    HOW: Return 400 with clear error code
    """
    logger.warning(f"Provider disabled: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "LLM_PROVIDER_DISABLED",
            "message": str(exc),
            "detail": "Check LLM provider configuration"
        }
    )


async def provider_timeout_handler(request: Request, exc: ProviderTimeoutError):
    """
    Handle ProviderTimeoutError.
    
    WHAT: LLM request timed out
    WHY: Provider may be slow or unresponsive
    HOW: Return 503 service unavailable
    """
    logger.error(f"Provider timeout: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "LLM_TIMEOUT",
            "message": str(exc),
            "detail": "LLM provider request timed out"
        }
    )


async def provider_unavailable_handler(request: Request, exc: ProviderUnavailableError):
    """
    Handle ProviderUnavailableError.
    
    WHAT: Provider is not reachable
    WHY: Service may be down or misconfigured
    HOW: Return 503 service unavailable
    """
    logger.error(f"Provider unavailable: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "LLM_UNAVAILABLE",
            "message": str(exc),
            "detail": "LLM provider is not reachable. Check that LM Studio is running."
        }
    )


async def provider_response_error_handler(request: Request, exc: ProviderResponseError):
    """
    Handle ProviderResponseError.
    
    WHAT: Provider returned invalid or error response
    WHY: API contract violation or server error
    HOW: Return 502 bad gateway
    """
    logger.error(f"Provider response error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "LLM_BAD_GATEWAY",
            "message": str(exc),
            "detail": "LLM provider returned an invalid response"
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with FastAPI app.
    
    WHAT: Attach handlers to app
    WHY: Centralized error handling
    HOW: Use app.add_exception_handler
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(ProviderDisabledError, provider_disabled_handler)
    app.add_exception_handler(ProviderTimeoutError, provider_timeout_handler)
    app.add_exception_handler(ProviderUnavailableError, provider_unavailable_handler)
    app.add_exception_handler(ProviderResponseError, provider_response_error_handler)
    
    logger.info("Exception handlers registered")

