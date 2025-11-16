"""
Global error handling middleware.

WHAT: Translate exceptions to appropriate HTTP responses
WHY: Consistent error responses with proper status codes
HOW: FastAPI exception handlers for custom exceptions
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime

from ..llm.types import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderDisabledError,
    ProviderResponseError,
)
from ..utils.exceptions import (
    APIException,
    ValidationError,
    SessionNotFoundError,
    RoomNotFoundError,
    NegotiationAlreadyActiveError,
    MaxSellersExceededError,
    InsufficientInventoryError,
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


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI RequestValidationError.
    
    WHAT: Request validation failed
    WHY: Invalid request payload
    HOW: Return 400 with field errors
    """
    logger.warning(f"Validation error: {exc.errors()}")
    
    # Clean up error details to be JSON serializable
    errors = exc.errors()
    cleaned_errors = []
    for error in errors:
        cleaned_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input")
        }
        # Convert ctx errors to strings
        if "ctx" in error:
            ctx = error["ctx"]
            cleaned_ctx = {}
            for k, v in ctx.items():
                if isinstance(v, Exception):
                    cleaned_ctx[k] = str(v)
                else:
                    cleaned_ctx[k] = v
            cleaned_error["ctx"] = cleaned_ctx
        cleaned_errors.append(cleaned_error)
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": cleaned_errors,
            "timestamp": datetime.now().isoformat()
        }
    )


async def api_exception_handler(request: Request, exc: APIException):
    """
    Handle generic APIException.
    
    WHAT: Custom API exception
    WHY: Domain-specific error
    HOW: Return appropriate status code based on exception type
    """
    status_code = status.HTTP_400_BAD_REQUEST
    
    if isinstance(exc, (SessionNotFoundError, RoomNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, NegotiationAlreadyActiveError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, (MaxSellersExceededError, InsufficientInventoryError)):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    
    logger.warning(f"API exception: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now().isoformat()
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
    # LLM Provider exceptions
    app.add_exception_handler(ProviderDisabledError, provider_disabled_handler)
    app.add_exception_handler(ProviderTimeoutError, provider_timeout_handler)
    app.add_exception_handler(ProviderUnavailableError, provider_unavailable_handler)
    app.add_exception_handler(ProviderResponseError, provider_response_error_handler)
    
    # API exceptions
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(APIException, api_exception_handler)
    
    logger.info("Exception handlers registered")

