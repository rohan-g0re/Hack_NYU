"""
Negotiation domain models for Phase 2.

WHAT: Core data structures for buyer/seller agents and negotiation state
WHY: Consistent typing across agents, graph, and future persistence
HOW: Pydantic v2 models compatible with FastAPI schemas
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Any
from datetime import datetime
from uuid import UUID, uuid4


class BuyerConstraints(BaseModel):
    """Constraints and goals for the buyer agent."""
    
    item_id: str
    item_name: str
    quantity_needed: int = Field(ge=1)
    min_price_per_unit: float = Field(ge=0.0)
    max_price_per_unit: float = Field(gt=0.0)
    budget_per_item: float | None = Field(
        default=None, 
        ge=0.0,
        description="Individual budget ceiling for this specific item (total cost = price * quantity)"
    )
    tone: Literal["neutral", "friendly", "assertive"] = "neutral"
    priority_notes: str = ""
    
    @model_validator(mode='before')
    @classmethod
    def handle_budget_ceiling_alias(cls, data):
        """Handle backward compatibility: budget_ceiling -> budget_per_item."""
        if isinstance(data, dict):
            if 'budget_ceiling' in data and 'budget_per_item' not in data:
                data['budget_per_item'] = data.pop('budget_ceiling')
        return data
    
    @property
    def budget_ceiling(self) -> float | None:
        """Backward compatibility property."""
        return self.budget_per_item
    
    @field_validator("max_price_per_unit")
    @classmethod
    def validate_price_range(cls, v: float, info) -> float:
        """Ensure max >= min price."""
        min_price = info.data.get("min_price_per_unit")
        if min_price is not None and v < min_price:
            raise ValueError("max_price_per_unit must be >= min_price_per_unit")
        return v


class SellerProfile(BaseModel):
    """Personality and configuration for a seller agent."""
    
    seller_id: str
    display_name: str = Field(min_length=1, max_length=50)
    priority: Literal["maximize_profit", "customer_retention"] = "maximize_profit"
    speaking_style: Literal["rude", "neutral", "very_sweet"] = "neutral"
    persona_notes: str = ""


class InventoryItem(BaseModel):
    """Inventory item with pricing constraints."""
    
    item_id: str
    name: str
    quantity_available: int = Field(ge=0)
    cost_price: float = Field(ge=0.0)
    least_price: float = Field(gt=0.0)  # Floor price (must cover costs + margin)
    selling_price: float = Field(gt=0.0)  # Target/listed price
    
    @field_validator("least_price")
    @classmethod
    def validate_least_price(cls, v: float, info) -> float:
        """Ensure least_price >= cost_price."""
        cost = info.data.get("cost_price")
        if cost is not None and v < cost:
            raise ValueError("least_price must be >= cost_price")
        return v
    
    @field_validator("selling_price")
    @classmethod
    def validate_selling_price(cls, v: float, info) -> float:
        """Ensure selling_price >= least_price."""
        least = info.data.get("least_price")
        if least is not None and v < least:
            raise ValueError("selling_price must be >= least_price")
        return v


class Message(BaseModel):
    """A message in the negotiation conversation."""
    
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    sender_id: str
    sender_type: Literal["buyer", "seller", "system"]
    content: str = Field(max_length=5000)
    round_number: int = Field(ge=0)
    visible_to: list[str] = Field(default_factory=lambda: ["all"])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Offer(BaseModel):
    """A concrete offer from a seller."""
    
    offer_id: str = Field(default_factory=lambda: str(uuid4()))
    seller_id: str
    item_id: str
    price: float = Field(gt=0.0)
    quantity: int = Field(ge=1)
    round_number: int = Field(ge=0)
    status: Literal["pending", "accepted", "rejected", "withdrawn"] = "pending"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NegotiationRoomState(BaseModel):
    """Complete state of a negotiation room."""
    
    room_id: str = Field(default_factory=lambda: str(uuid4()))
    seed: int = Field(default=42)
    current_round: int = Field(default=0, ge=0)
    max_rounds: int = Field(default=5, ge=1)  # Now means exchanges per seller (default 5)
    
    buyer_id: str = "buyer"
    buyer_constraints: BuyerConstraints
    
    seller_profiles: dict[str, SellerProfile] = Field(default_factory=dict)
    seller_inventories: dict[str, list[InventoryItem]] = Field(default_factory=dict)
    
    message_history: list[Message] = Field(default_factory=list)
    offer_history: list[Offer] = Field(default_factory=list)
    
    active_sellers: list[str] = Field(default_factory=list)
    current_seller_index: int = Field(default=0, ge=0)  # Which seller in current round sequence
    exchanges_completed: dict[str, int] = Field(default_factory=dict)  # seller_id → exchange count
    
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"arbitrary_types_allowed": True}


class BuyerTurnResult(BaseModel):
    """Result from a buyer agent turn."""
    
    message: str
    mentioned_sellers: list[str] = Field(default_factory=list)
    raw_text: str
    sanitized: bool = False


class SellerResponse(BaseModel):
    """Result from a seller agent response."""
    
    seller_id: str
    message: str
    offer: Offer | None = None
    violations: list[str] = Field(default_factory=list)
    raw_text: str


class NegotiationOutcome(BaseModel):
    """Final outcome of a negotiation."""
    
    winner_id: str | None = None
    winning_offer: Offer | None = None
    total_rounds: int
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

