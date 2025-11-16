"""
Custom business exceptions for Phase 4 API endpoints.

WHAT: Domain-specific exceptions that map to HTTP status codes
WHY: Consistent error handling across all API endpoints
HOW: Custom exception classes with error codes and messages
"""

from typing import Optional, List, Dict, Any


class BusinessException(Exception):
    """Base class for business logic exceptions."""
    
    def __init__(self, message: str, code: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class SessionNotFoundException(BusinessException):
    """Raised when a session is not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session not found: {session_id}",
            code="SESSION_NOT_FOUND",
            details={"session_id": session_id}
        )


class RoomNotFoundException(BusinessException):
    """Raised when a negotiation room is not found."""
    
    def __init__(self, room_id: str):
        super().__init__(
            message=f"Negotiation room not found: {room_id}",
            code="ROOM_NOT_FOUND",
            details={"room_id": room_id}
        )


class NegotiationAlreadyActiveException(BusinessException):
    """Raised when attempting to start an already active negotiation."""
    
    def __init__(self, room_id: str):
        super().__init__(
            message=f"Negotiation already active for room: {room_id}",
            code="NEGOTIATION_ALREADY_ACTIVE",
            details={"room_id": room_id}
        )


class MaxSellersExceededException(BusinessException):
    """Raised when the number of sellers exceeds the maximum allowed."""
    
    def __init__(self, count: int, max_allowed: int):
        super().__init__(
            message=f"Maximum {max_allowed} sellers allowed, got {count}",
            code="MAX_SELLERS_EXCEEDED",
            details={"count": count, "max_allowed": max_allowed}
        )


class InsufficientInventoryException(BusinessException):
    """Raised when seller doesn't have enough inventory."""
    
    def __init__(self, seller_id: str, item_id: str, requested: int, available: int):
        super().__init__(
            message=f"Insufficient inventory: seller {seller_id} has {available} of item {item_id}, requested {requested}",
            code="INSUFFICIENT_INVENTORY",
            details={
                "seller_id": seller_id,
                "item_id": item_id,
                "requested": requested,
                "available": available
            }
        )


class ValidationException(BusinessException):
    """Raised for validation errors."""
    
    def __init__(self, message: str, field_errors: Optional[List[Dict[str, str]]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field_errors": field_errors} if field_errors else None
        )


class NegotiationNotActiveException(BusinessException):
    """Raised when attempting to operate on an inactive negotiation."""
    
    def __init__(self, room_id: str, current_status: str):
        super().__init__(
            message=f"Negotiation not active for room {room_id}. Current status: {current_status}",
            code="NEGOTIATION_NOT_ACTIVE",
            details={"room_id": room_id, "current_status": current_status}
        )

