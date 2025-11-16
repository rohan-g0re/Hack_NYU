"""
Global error handling middleware.

WHAT: Translate exceptions to appropriate HTTP responses
WHY: Consistent error responses with proper status codes
HOW: FastAPI exception handlers for custom exceptions
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from datetime import datetime
from typing import Dict, Any

from ..llm.types import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderDisabledError,
    ProviderResponseError,
)
from ..utils.exceptions import (
    BusinessException,
    SessionNotFoundException,
    RoomNotFoundException,
    NegotiationAlreadyActiveException,
    MaxSellersExceededException,
    InsufficientInventoryException,
    ValidationException,
    NegotiationNotActiveException
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


def create_cors_response(status_code: int, content: Dict[Any, Any]) -> JSONResponse:
    """
    Create a JSONResponse with CORS headers.
    
    WHAT: JSONResponse with proper CORS headers
    WHY: Error responses bypass CORS middleware
    HOW: Manually add CORS headers to response
    """
    response = JSONResponse(status_code=status_code, content=content)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


async def provider_disabled_handler(request: Request, exc: ProviderDisabledError):
    """
    Handle ProviderDisabledError.
    
    WHAT: Provider is disabled in config
    WHY: User needs to enable provider or switch to another
    HOW: Return 400 with clear error code
    """
    logger.warning(f"Provider disabled: {exc}")
    return create_cors_response(
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
    return create_cors_response(
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
    return create_cors_response(
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
    return create_cors_response(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "LLM_BAD_GATEWAY",
            "message": str(exc),
            "detail": "LLM provider returned an invalid response"
        }
    )


async def session_not_found_handler(request: Request, exc: SessionNotFoundException):
    """Handle SessionNotFoundException."""
    logger.warning(f"Session not found: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def room_not_found_handler(request: Request, exc: RoomNotFoundException):
    """Handle RoomNotFoundException."""
    logger.warning(f"Room not found: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def negotiation_already_active_handler(request: Request, exc: NegotiationAlreadyActiveException):
    """Handle NegotiationAlreadyActiveException."""
    logger.warning(f"Negotiation already active: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def max_sellers_exceeded_handler(request: Request, exc: MaxSellersExceededException):
    """Handle MaxSellersExceededException."""
    logger.warning(f"Max sellers exceeded: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def insufficient_inventory_handler(request: Request, exc: InsufficientInventoryException):
    """Handle InsufficientInventoryException."""
    logger.warning(f"Insufficient inventory: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle ValidationException."""
    logger.warning(f"Validation error: {exc.message}")
    return create_cors_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def negotiation_not_active_handler(request: Request, exc: NegotiationNotActiveException):
    """Handle NegotiationNotActiveException."""
    logger.warning(f"Negotiation not active: {exc.details}")
    return create_cors_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    """
    Handle Pydantic ValidationError.
    
    WHAT: Convert Pydantic validation errors to standard format
    WHY: Provide field-level error details
    HOW: Extract error details and format as standard error response
    """
    logger.warning(f"Pydantic validation error: {exc}")
    
    # Extract field errors
    field_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_errors.append({
            "field": field_path,
            "issue": error["msg"]
        })
    
    return create_cors_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": field_errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def business_exception_handler(request: Request, exc: BusinessException):
    """
    Handle generic BusinessException.
    
    WHAT: Catch-all for business exceptions
    WHY: Ensure all business exceptions are handled consistently
    HOW: Return 400 with exception details
    """
    logger.warning(f"Business exception: {exc.message}")
    return create_cors_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle generic exceptions.
    
    WHAT: Catch-all for unhandled exceptions
    WHY: Prevent stack traces leaking to clients
    HOW: Log full error, return sanitized 500 response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return create_cors_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }
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
    
    # Business logic exceptions (specific ones first)
    app.add_exception_handler(SessionNotFoundException, session_not_found_handler)
    app.add_exception_handler(RoomNotFoundException, room_not_found_handler)
    app.add_exception_handler(NegotiationAlreadyActiveException, negotiation_already_active_handler)
    app.add_exception_handler(MaxSellersExceededException, max_sellers_exceeded_handler)
    app.add_exception_handler(InsufficientInventoryException, insufficient_inventory_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(NegotiationNotActiveException, negotiation_not_active_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)  # Generic catch-all
    
    # Pydantic validation errors
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)
    
    # Generic exception catch-all
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered")

