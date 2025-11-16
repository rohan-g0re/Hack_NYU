"""
Custom exceptions for Phase 2 agents and negotiation logic.

WHAT: Structured exceptions with context for agent errors
WHY: Clear error handling and debugging with correlation IDs
HOW: Exception classes carrying room_id, round_number, seller_id
"""


class BuyerAgentError(Exception):
    """Error in buyer agent processing."""
    
    def __init__(self, message: str, room_id: str | None = None, round_number: int | None = None):
        self.room_id = room_id
        self.round_number = round_number
        super().__init__(message)
    
    def __str__(self):
        parts = [super().__str__()]
        if self.room_id:
            parts.append(f"room_id={self.room_id}")
        if self.round_number is not None:
            parts.append(f"round={self.round_number}")
        return f"{parts[0]} ({', '.join(parts[1:])})" if len(parts) > 1 else parts[0]


class SellerAgentError(Exception):
    """Error in seller agent processing."""
    
    def __init__(self, message: str, seller_id: str | None = None, room_id: str | None = None, round_number: int | None = None):
        self.seller_id = seller_id
        self.room_id = room_id
        self.round_number = round_number
        super().__init__(message)
    
    def __str__(self):
        parts = [super().__str__()]
        if self.seller_id:
            parts.append(f"seller_id={self.seller_id}")
        if self.room_id:
            parts.append(f"room_id={self.room_id}")
        if self.round_number is not None:
            parts.append(f"round={self.round_number}")
        return f"{parts[0]} ({', '.join(parts[1:])})" if len(parts) > 1 else parts[0]


class NegotiationGraphError(Exception):
    """Error in negotiation graph orchestration."""
    
    def __init__(self, message: str, room_id: str | None = None, round_number: int | None = None):
        self.room_id = room_id
        self.round_number = round_number
        super().__init__(message)
    
    def __str__(self):
        parts = [super().__str__()]
        if self.room_id:
            parts.append(f"room_id={self.room_id}")
        if self.round_number is not None:
            parts.append(f"round={self.round_number}")
        return f"{parts[0]} ({', '.join(parts[1:])})" if len(parts) > 1 else parts[0]

