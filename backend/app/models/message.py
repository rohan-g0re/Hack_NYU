"""
Message models for negotiation history.

WHAT: Message structure for conversation history
WHY: Track messages, roles, and optional offers
HOW: TypedDict and dataclass for in-memory state
"""

from typing import TypedDict, Literal, Optional
from datetime import datetime


class Offer(TypedDict, total=False):
    """Offer made by a seller."""
    price: float
    quantity: int


class Message(TypedDict, total=False):
    """Message in negotiation history."""
    message_id: str
    turn_number: int
    timestamp: datetime
    sender_id: str
    sender_type: Literal["buyer", "seller"]
    sender_name: str
    content: str
    mentioned_sellers: list[str]  # List of seller IDs mentioned
    offer: Optional[Offer]  # Optional offer if from seller
    visibility: list[str]  # List of agent IDs who can see this message

