"""
Room building utilities for negotiation setup.

WHAT: Helper functions to build and configure negotiation rooms
WHY: Centralize logic for seller filtering and room initialization
HOW: Simple lookup functions based on item_id matching
"""

from typing import Dict, List
from ..models.negotiation import InventoryItem
from ..utils.logger import get_logger

logger = get_logger(__name__)


def filter_sellers_by_item(
    item_id: str,
    seller_inventories: Dict[str, List[InventoryItem]]
) -> List[str]:
    """
    Filter sellers to only those who have the requested item.
    
    WHAT: Simple lookup to find sellers with matching item_id
    WHY: Only spawn negotiation rooms with relevant sellers
    HOW: Check each seller's inventory for matching item_id
    
    Args:
        item_id: The item the buyer wants (from BuyerConstraints.item_id)
        seller_inventories: Dict of seller_id -> list of InventoryItem
    
    Returns:
        List of seller IDs who have this item in their inventory
    
    Example:
        >>> inventories = {
        ...     "seller1": [InventoryItem(item_id="widget", ...)],
        ...     "seller2": [InventoryItem(item_id="gadget", ...)]
        ... }
        >>> filter_sellers_by_item("widget", inventories)
        ["seller1"]
    """
    matching_sellers = []
    
    for seller_id, inventory in seller_inventories.items():
        # Check if any item in this seller's inventory matches
        for item in inventory:
            if item.item_id == item_id:
                matching_sellers.append(seller_id)
                logger.debug(f"Seller {seller_id} has item {item_id}")
                break  # Found it, move to next seller
    
    logger.info(
        f"Filtered sellers for item_id '{item_id}': "
        f"{len(matching_sellers)} sellers found out of {len(seller_inventories)} total"
    )
    
    return matching_sellers

