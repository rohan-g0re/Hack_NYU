"""
Decision engine for Phase 3.

WHAT: Validate buyer decisions and apply tie-breakers
WHY: Ensure chosen deals are valid and select best offer when multiple exist
HOW: Check constraints, compare offers, apply tie-breaking rules
"""

from typing import Optional, List, Dict, Tuple
from ..models.message import Offer
from ..models.agent import BuyerConstraints
from ..utils.logger import get_logger

logger = get_logger(__name__)


def validate_decision(
    selected_seller_id: str,
    final_offer: Optional[Dict],
    buyer_constraints: BuyerConstraints,
    all_offers: List[Dict]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a buyer decision is within constraints.
    
    WHAT: Check if chosen deal meets buyer's price/quantity requirements
    WHY: Enforce business rules before finalizing
    HOW: Validate price and quantity against buyer constraints
    
    Args:
        selected_seller_id: ID of selected seller
        final_offer: Final offer dict with 'price' and 'quantity'
        buyer_constraints: Buyer's constraints for this item
        all_offers: List of all offers from negotiation (for validation context)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not final_offer:
        return False, "No offer provided"
    
    price = final_offer.get("price")
    quantity = final_offer.get("quantity")
    
    if price is None or quantity is None:
        return False, "Offer missing price or quantity"
    
    # Check price constraints
    if price < buyer_constraints.min_price_per_unit:
        return False, f"Price ${price:.2f} below minimum ${buyer_constraints.min_price_per_unit:.2f}"
    
    if price > buyer_constraints.max_price_per_unit:
        return False, f"Price ${price:.2f} above maximum ${buyer_constraints.max_price_per_unit:.2f}"
    
    # Check quantity constraints
    if quantity < 1:
        return False, "Quantity must be at least 1"
    
    if quantity > buyer_constraints.quantity_needed:
        return False, f"Quantity {quantity} exceeds needed {buyer_constraints.quantity_needed}"
    
    return True, None


def select_best_offer(
    offers: List[Dict],
    buyer_constraints: BuyerConstraints,
    tie_breaker: str = "price"
) -> Optional[Dict]:
    """
    Select best offer from multiple valid offers using tie-breakers.
    
    WHAT: Choose best offer when multiple sellers make valid offers
    WHY: Provide deterministic selection logic
    HOW: Apply tie-breakers: price (lowest), responsiveness (most messages), rounds (fewer)
    
    Args:
        offers: List of offer dicts, each with 'seller_id', 'price', 'quantity', 'round_number', 'message_count'
        buyer_constraints: Buyer's constraints
        tie_breaker: Primary tie-breaker: 'price', 'responsiveness', 'rounds'
    
    Returns:
        Best offer dict or None if no valid offers
    """
    if not offers:
        return None
    
    # Filter valid offers (within constraints)
    valid_offers = []
    for offer in offers:
        price = offer.get("price")
        quantity = offer.get("quantity")
        
        if price is None or quantity is None:
            continue
        
        if (buyer_constraints.min_price_per_unit <= price <= buyer_constraints.max_price_per_unit and
            1 <= quantity <= buyer_constraints.quantity_needed):
            valid_offers.append(offer)
    
    if not valid_offers:
        return None
    
    # Sort by tie-breaker priority
    if tie_breaker == "price":
        # Lowest price first
        valid_offers.sort(key=lambda x: x.get("price", float('inf')))
    elif tie_breaker == "responsiveness":
        # Most messages first (higher message_count)
        valid_offers.sort(key=lambda x: x.get("message_count", 0), reverse=True)
    elif tie_breaker == "rounds":
        # Fewer rounds first (lower round_number)
        valid_offers.sort(key=lambda x: x.get("round_number", float('inf')))
    else:
        # Default to price
        valid_offers.sort(key=lambda x: x.get("price", float('inf')))
    
    # Apply secondary tie-breakers
    # If prices are equal (within 0.01), prefer fewer rounds
    if tie_breaker == "price":
        # Group by similar price (within $0.01)
        price_groups = {}
        for offer in valid_offers:
            price_key = round(offer.get("price", 0), 2)
            if price_key not in price_groups:
                price_groups[price_key] = []
            price_groups[price_key].append(offer)
        
        # Within each price group, prefer fewer rounds
        for price_key in sorted(price_groups.keys()):
            price_groups[price_key].sort(key=lambda x: x.get("round_number", float('inf')))
            return price_groups[price_key][0]
    
    return valid_offers[0]


def compute_total_cost(price_per_unit: float, quantity: int) -> float:
    """Compute total cost for an offer."""
    return price_per_unit * quantity

