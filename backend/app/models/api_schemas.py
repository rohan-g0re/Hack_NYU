"""
Pydantic API schemas for Phase 4 endpoints.

WHAT: Request and response models for FastAPI
WHY: Type-safe validation and serialization matching frontend interfaces
HOW: Pydantic v2 models with validators and constraints
"""

from typing import Optional, List, Dict, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime

from ..core.config import settings


# ========== Buyer Configuration ==========

class ShoppingItem(BaseModel):
    """Shopping item in buyer's list."""
    id: str = Field(..., min_length=1, max_length=50, description="Item ID")
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    quantity: int = Field(..., gt=0, description="Quantity needed")
    min_price: float = Field(..., ge=0, description="Minimum acceptable price per unit")
    max_price: float = Field(..., gt=0, description="Maximum acceptable price per unit")
    
    @model_validator(mode='after')
    def validate_price_range(self):
        """Ensure max_price > min_price."""
        if self.max_price <= self.min_price:
            raise ValueError(f"max_price ({self.max_price}) must be greater than min_price ({self.min_price})")
        return self


class BuyerConfig(BaseModel):
    """Buyer configuration."""
    id: str = Field(default="buyer_1", min_length=1, max_length=50, description="Buyer ID")
    name: str = Field(..., min_length=1, max_length=50, description="Buyer name")
    items: List[ShoppingItem] = Field(..., min_length=1, description="Shopping list")


# ========== Seller Configuration ==========

class InventoryItem(BaseModel):
    """Inventory item for seller."""
    item_id: str = Field(..., min_length=1, max_length=50, description="Item ID")
    item_name: str = Field(..., min_length=1, max_length=100, description="Item name")
    cost_price: float = Field(..., ge=0, description="Cost price")
    selling_price: float = Field(..., gt=0, description="Selling price")
    least_price: float = Field(..., gt=0, description="Minimum acceptable price")
    quantity_available: int = Field(..., gt=0, description="Available quantity")
    
    @model_validator(mode='after')
    def validate_price_constraints(self):
        """Ensure cost_price < least_price < selling_price."""
        if self.selling_price <= self.cost_price:
            raise ValueError(f"selling_price ({self.selling_price}) must be greater than cost_price ({self.cost_price})")
        if self.least_price <= self.cost_price:
            raise ValueError(f"least_price ({self.least_price}) must be greater than cost_price ({self.cost_price})")
        if self.least_price >= self.selling_price:
            raise ValueError(f"least_price ({self.least_price}) must be less than selling_price ({self.selling_price})")
        return self


class SellerProfile(BaseModel):
    """Seller personality profile."""
    priority: Literal["maximize_profit", "customer_retention"] = Field(
        ..., 
        description="Seller's priority"
    )
    speaking_style: Literal["rude", "very_sweet", "neutral"] = Field(
        ..., 
        description="Seller's communication style"
    )


class SellerConfig(BaseModel):
    """Seller configuration."""
    id: str = Field(default="", max_length=50, description="Seller ID")
    name: str = Field(..., min_length=1, max_length=50, description="Seller name")
    inventory: List[InventoryItem] = Field(..., min_length=1, description="Seller inventory")
    profile: SellerProfile = Field(..., description="Seller profile")


# ========== LLM Configuration ==========

class LLMConfig(BaseModel):
    """LLM configuration."""
    model: str = Field(default="qwen3-1.7b", description="Model name")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(default=256, gt=0, le=4096, description="Max tokens")


# ========== Request Schemas ==========

class InitializeSessionRequest(BaseModel):
    """Request to initialize a new session."""
    buyer: BuyerConfig
    sellers: List[SellerConfig] = Field(..., min_length=1)
    llm_config: Optional[LLMConfig] = Field(default=None, description="Optional LLM configuration")
    
    @field_validator('sellers')
    @classmethod
    def validate_seller_count(cls, v):
        """Ensure seller count doesn't exceed maximum."""
        if len(v) > settings.MAX_SELLERS_PER_SESSION:
            raise ValueError(f"Maximum {settings.MAX_SELLERS_PER_SESSION} sellers allowed, got {len(v)}")
        return v


class SendMessageRequest(BaseModel):
    """Request to send a manual buyer message."""
    message: str = Field(..., min_length=1, max_length=1000, description="Message content")


class ForceDecisionRequest(BaseModel):
    """Request to force a decision."""
    force_select_seller: Optional[str] = Field(default=None, description="Optional seller ID to select")


# ========== Response Schemas ==========

class SellerParticipant(BaseModel):
    """Seller participating in negotiation."""
    seller_id: str
    seller_name: str


class BuyerConstraints(BaseModel):
    """Buyer constraints for an item."""
    min_price_per_unit: float
    max_price_per_unit: float


class NegotiationRoom(BaseModel):
    """Negotiation room information."""
    room_id: str
    item_id: str
    item_name: str
    quantity_needed: int
    buyer_constraints: BuyerConstraints
    participating_sellers: List[SellerParticipant]
    status: str
    reason: Optional[str] = None


class InitializeSessionResponse(BaseModel):
    """Response after initializing a session."""
    session_id: str
    created_at: str
    buyer_id: str
    seller_ids: List[str]
    negotiation_rooms: List[NegotiationRoom]
    total_rooms: int
    skipped_items: List[str]


class SessionNegotiationRoom(BaseModel):
    """Negotiation room info in session details."""
    room_id: str
    item_name: str
    status: str
    current_round: int
    participating_sellers_count: int


class SessionDetails(BaseModel):
    """Detailed session information."""
    session_id: str
    status: str
    created_at: str
    buyer: Dict[str, str]
    sellers: List[Dict[str, str]]
    negotiation_rooms: List[SessionNegotiationRoom]
    llm_provider: str


class Offer(BaseModel):
    """Offer details."""
    price: float
    quantity: int
    timestamp: str


class Message(BaseModel):
    """Message in conversation."""
    message_id: str
    turn: int
    timestamp: str
    sender_type: Literal["buyer", "seller", "system"]
    sender_id: Optional[str] = None
    sender_name: str
    message: str
    mentioned_agents: Optional[List[str]] = None
    updated_offer: Optional[Offer] = None


class OfferWithSeller(Offer):
    """Offer with seller name."""
    seller_name: str


class NegotiationStateResponse(BaseModel):
    """Current negotiation state."""
    room_id: str
    item_name: str
    status: str
    current_round: int
    max_rounds: int
    conversation_history: List[Message]
    current_offers: Dict[str, OfferWithSeller]
    buyer_constraints: BuyerConstraints


class StartNegotiationResponse(BaseModel):
    """Response after starting negotiation."""
    room_id: str
    status: str
    item_name: str
    participating_sellers: List[str]
    buyer_opening_message: str
    stream_url: str


class SelectedSellerInfo(BaseModel):
    """Selected seller information."""
    seller_id: str
    seller_name: str
    final_price: float
    quantity: int


class DecisionResponse(BaseModel):
    """Response after making a decision."""
    room_id: str
    decision_made: bool
    selected_seller: Optional[SelectedSellerInfo] = None
    decision_reason: str
    total_rounds: int
    negotiation_duration_seconds: float


class DeleteSessionResponse(BaseModel):
    """Response after deleting a session."""
    session_id: str
    deleted: bool
    logs_saved: bool
    logs_path: Optional[str] = None


# ========== Summary Schemas ==========

class PurchaseSummary(BaseModel):
    """Summary of a single purchase."""
    item_name: str
    quantity: int
    selected_seller: str
    final_price_per_unit: float
    total_cost: float
    negotiation_rounds: int
    duration_seconds: float


class FailedItem(BaseModel):
    """Failed negotiation item."""
    item_name: str
    reason: str


class TotalCostSummary(BaseModel):
    """Total cost summary."""
    total_spent: float
    items_purchased: int
    average_savings_per_item: float


class NegotiationMetrics(BaseModel):
    """Negotiation metrics."""
    average_rounds: float
    average_duration_seconds: float
    total_messages_exchanged: int


class SessionSummaryResponse(BaseModel):
    """Session summary response."""
    session_id: str
    buyer_name: str
    total_items_requested: int
    completed_purchases: int
    failed_purchases: int
    purchases: List[PurchaseSummary]
    failed_items: List[FailedItem]
    total_cost_summary: TotalCostSummary
    negotiation_metrics: NegotiationMetrics


# ========== Error Response ==========

class ErrorDetail(BaseModel):
    """Error detail."""
    field: str
    issue: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input",
                    "details": [{"field": "price", "issue": "Must be positive"}],
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }

