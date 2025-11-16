"""
Negotiation state and event models for Phase 2.

WHAT: In-memory state for negotiation rooms and events
WHY: Track negotiation progress without database dependencies
HOW: TypedDict for events, dataclass for room state
"""

from typing import TypedDict, Literal, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .agent import BuyerConstraints, Seller
from .message import Message


class NegotiationEvent(TypedDict, total=False):
    """Event emitted during negotiation."""
    type: Literal["buyer_message", "seller_response", "negotiation_complete", "error", "heartbeat"]
    data: dict
    timestamp: datetime


@dataclass
class NegotiationRoomState:
    """In-memory state for a negotiation room."""
    room_id: str
    buyer_id: str
    buyer_name: str
    buyer_constraints: BuyerConstraints
    sellers: list[Seller]
    conversation_history: list[Message] = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 10
    seed: Optional[int] = None  # For deterministic testing
    status: Literal["pending", "active", "completed", "no_sellers_available", "aborted"] = "pending"
    selected_seller_id: Optional[str] = None
    final_offer: Optional[dict] = None  # {"price": float, "quantity": int}
    decision_reason: Optional[str] = None
    llm_provider: str = "lm_studio"  # LLM provider for this negotiation ('lm_studio' or 'openrouter')
    llm_model: Optional[str] = None  # LLM model name from session (uses provider default if None)

