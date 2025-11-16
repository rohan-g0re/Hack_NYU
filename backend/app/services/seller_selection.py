"""
Seller selection logic for negotiation participation.

WHAT: Select sellers who can fulfill buyer's item requirements
WHY: Only matching sellers should participate in negotiations
HOW: Validate inventory, quantity, and price range overlap
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
from ..models.agent import Seller, BuyerConstraints, InventoryItem
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SelectionResult:
    """Result of seller selection process."""
    selected_sellers: List[Seller]
    skipped_sellers: Dict[str, str]  # seller_id -> skip_reason


def select_sellers_for_item(
    item_constraints: BuyerConstraints,
    all_sellers: List[Seller]
) -> SelectionResult:
    """
    Select sellers who can fulfill buyer's item request.
    
    WHAT: Filter sellers based on inventory availability and price overlap
    WHY: Prevent sellers without matching items from participating
    HOW: Check item_id match, quantity, and price range
    
    Selection Criteria:
    1. Seller has item with matching item_id
    2. Seller has sufficient quantity available
    3. Price ranges overlap (seller's least_price <= buyer's max_price)
    
    Args:
        item_constraints: Buyer's requirements for the item
        all_sellers: List of all potential sellers
        
    Returns:
        SelectionResult with selected sellers and skip reasons
    """
    selected_sellers = []
    skipped_sellers = {}
    
    for seller in all_sellers:
        can_participate, skip_reason = validate_seller_inventory(
            seller=seller,
            item_id=item_constraints.item_id,
            quantity_needed=item_constraints.quantity_needed,
            max_price=item_constraints.max_price_per_unit
        )
        
        if can_participate:
            selected_sellers.append(seller)
            logger.info(f"Selected seller {seller.name} for item {item_constraints.item_name}")
        else:
            skipped_sellers[seller.seller_id] = skip_reason
            logger.info(f"Skipped seller {seller.name}: {skip_reason}")
    
    logger.info(
        f"Selection complete for {item_constraints.item_name}: "
        f"{len(selected_sellers)} selected, {len(skipped_sellers)} skipped"
    )
    
    return SelectionResult(
        selected_sellers=selected_sellers,
        skipped_sellers=skipped_sellers
    )


def validate_seller_inventory(
    seller: Seller,
    item_id: str,
    quantity_needed: int,
    max_price: float
) -> Tuple[bool, Optional[str]]:
    """
    Validate if seller can participate in negotiation.
    
    WHAT: Check if seller meets all requirements
    WHY: Ensure only qualified sellers participate
    HOW: Validate inventory item exists, quantity sufficient, price compatible
    
    Args:
        seller: Seller to validate
        item_id: Required item ID
        quantity_needed: Minimum quantity buyer needs
        max_price: Maximum price buyer will pay
        
    Returns:
        Tuple of (can_participate: bool, skip_reason: Optional[str])
    """
    # Find matching inventory item
    matching_item: Optional[InventoryItem] = None
    for item in seller.inventory:
        if item.item_id == item_id:
            matching_item = item
            break
    
    # Check 1: Has the item
    if matching_item is None:
        return False, "no_inventory"
    
    # Check 2: Sufficient quantity
    if matching_item.quantity_available < quantity_needed:
        return False, f"insufficient_quantity (has {matching_item.quantity_available}, needs {quantity_needed})"
    
    # Check 3: Price range overlap
    # Seller's minimum acceptable (least_price) must be <= buyer's maximum willing to pay
    # This ensures there's a negotiation window
    if matching_item.least_price > max_price:
        return False, f"price_mismatch (seller minimum ${matching_item.least_price:.2f} > buyer maximum ${max_price:.2f})"
    
    # All checks passed
    return True, None


def get_seller_item(seller: Seller, item_id: str) -> Optional[InventoryItem]:
    """
    Get seller's inventory item by item_id.
    
    WHAT: Find specific inventory item for seller
    WHY: Helper for retrieving item details
    HOW: Linear search through seller's inventory
    
    Args:
        seller: Seller to search
        item_id: Item ID to find
        
    Returns:
        InventoryItem if found, None otherwise
    """
    for item in seller.inventory:
        if item.item_id == item_id:
            return item
    return None


def calculate_overlap_score(
    seller_item: InventoryItem,
    buyer_constraints: BuyerConstraints
) -> float:
    """
    Calculate how well seller's pricing overlaps with buyer's budget.
    
    WHAT: Measure compatibility between seller and buyer price ranges
    WHY: Prioritize sellers with better price alignment
    HOW: Calculate overlap ratio between price ranges
    
    Score Interpretation:
    - 1.0: Perfect overlap (seller's range entirely within buyer's range)
    - 0.5: Partial overlap
    - 0.0: No overlap (shouldn't happen if seller was selected)
    
    Args:
        seller_item: Seller's inventory item
        buyer_constraints: Buyer's constraints
        
    Returns:
        Overlap score between 0.0 and 1.0
    """
    # Seller's negotiable range
    seller_min = seller_item.least_price
    seller_max = seller_item.selling_price
    
    # Buyer's acceptable range
    buyer_min = buyer_constraints.min_price_per_unit
    buyer_max = buyer_constraints.max_price_per_unit
    
    # Calculate overlap
    overlap_start = max(seller_min, buyer_min)
    overlap_end = min(seller_max, buyer_max)
    
    if overlap_end < overlap_start:
        # No overlap
        return 0.0
    
    overlap_size = overlap_end - overlap_start
    
    # Calculate as percentage of buyer's range
    buyer_range = buyer_max - buyer_min
    if buyer_range > 0:
        return min(1.0, overlap_size / buyer_range)
    else:
        # Buyer has fixed price, any overlap is good
        return 1.0 if overlap_size >= 0 else 0.0

