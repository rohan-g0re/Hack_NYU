"""
Agent configuration models for Phase 2.

WHAT: Data structures for buyer constraints, seller profiles, and inventory
WHY: Type-safe configuration for agents without database dependencies
HOW: Dataclasses and TypedDicts for in-memory state
"""

from dataclasses import dataclass
from typing import TypedDict, Literal


@dataclass
class BuyerConstraints:
    """Buyer's constraints for a single item."""
    item_id: str
    item_name: str
    quantity_needed: int
    min_price_per_unit: float
    max_price_per_unit: float


@dataclass
class InventoryItem:
    """Seller's inventory item with pricing constraints."""
    item_id: str
    item_name: str
    cost_price: float
    selling_price: float
    least_price: float  # Minimum price seller can accept
    quantity_available: int


@dataclass
class SellerProfile:
    """Seller's behavioral profile."""
    priority: Literal["customer_retention", "maximize_profit"]
    speaking_style: Literal["rude", "very_sweet"]


@dataclass
class Seller:
    """Complete seller configuration."""
    seller_id: str
    name: str
    profile: SellerProfile
    inventory: list[InventoryItem]  # List of items seller has

