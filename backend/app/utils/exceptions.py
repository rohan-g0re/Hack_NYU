"""
Custom API exceptions for Phase 4.

WHAT: Domain-specific exceptions for API error handling
WHY: Consistent error responses with proper HTTP status codes
HOW: Custom exception classes mapped to HTTP status codes in error handler
"""


class APIException(Exception):
    """Base exception for API errors."""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        """
        Initialize API exception.
        
        Args:
            message: Human-readable error message
            code: Error code (e.g., "SESSION_NOT_FOUND")
            details: Additional error details
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Request validation error."""
    pass


class SessionNotFoundError(APIException):
    """Session not found error."""
    pass


class RoomNotFoundError(APIException):
    """Negotiation room not found error."""
    pass


class NegotiationAlreadyActiveError(APIException):
    """Negotiation already active error."""
    pass


class MaxSellersExceededError(APIException):
    """Maximum sellers per session exceeded."""
    pass


class InsufficientInventoryError(APIException):
    """Insufficient inventory error."""
    pass

