"""
Message routing utilities for mention parsing and seller targeting.

WHAT: Parse @mentions and route messages to appropriate sellers
WHY: Enable buyer to selectively address sellers in negotiations
HOW: Regex extraction + normalized name mapping
"""

import re
from typing import List, Dict
from ..models.negotiation import SellerProfile
from ..utils.logger import get_logger

logger = get_logger(__name__)


def normalize_handle(name: str) -> str:
    """
    Normalize a seller handle/name for matching.
    
    WHAT: Convert display name to normalized form
    WHY: Case-insensitive, spacing-tolerant matching
    HOW: Lowercase, remove spaces/punctuation except underscores
    
    Args:
        name: Original display name or handle
    
    Returns:
        Normalized handle string
    """
    # Lowercase
    normalized = name.lower()
    
    # Remove spaces
    normalized = normalized.replace(" ", "")
    
    # Remove punctuation except underscores and alphanumerics
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    # Collapse multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    
    # Strip leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def parse_mentions(text: str, sellers: List[SellerProfile] | Dict[str, SellerProfile]) -> List[str]:
    """
    Parse @mentions from text and resolve to seller IDs.
    
    WHAT: Extract @SellerName mentions and map to seller IDs
    WHY: Determine which sellers should respond to buyer message
    HOW: Regex for @handles, normalize and match against seller profiles
    
    Args:
        text: Message text potentially containing @mentions
        sellers: List or dict of SellerProfile objects
    
    Returns:
        List of seller IDs in order of first mention (no duplicates)
    """
    if not text:
        return []
    
    # Convert dict to list if needed
    seller_list = list(sellers.values()) if isinstance(sellers, dict) else sellers
    
    if not seller_list:
        return []
    
    # Build normalized name -> seller_id mapping
    name_map: Dict[str, str] = {}
    for seller in seller_list:
        normalized = normalize_handle(seller.display_name)
        name_map[normalized] = seller.seller_id
        
        # Also map by seller_id itself (in case they use that)
        normalized_id = normalize_handle(seller.seller_id)
        if normalized_id not in name_map:  # Don't override display name mapping
            name_map[normalized_id] = seller.seller_id
    
    # Extract @mentions using regex
    mention_pattern = r'@([A-Za-z0-9_]+)'
    matches = re.finditer(mention_pattern, text)
    
    mentioned_ids: List[str] = []
    seen: set[str] = set()
    
    for match in matches:
        handle = match.group(1)
        normalized = normalize_handle(handle)
        
        if normalized in name_map:
            seller_id = name_map[normalized]
            if seller_id not in seen:
                mentioned_ids.append(seller_id)
                seen.add(seller_id)
                logger.debug(f"Matched @{handle} to seller {seller_id}")
        else:
            logger.debug(f"Unknown mention: @{handle}")
    
    return mentioned_ids


def select_targets(
    mentioned_ids: List[str],
    active_sellers: List[str],
    fallback_to_all: bool = True
) -> List[str]:
    """
    Select target sellers for a message, with fallback logic.
    
    WHAT: Determine final list of sellers to respond
    WHY: Handle cases where buyer doesn't mention anyone
    HOW: Use mentions if present, otherwise fallback to all active
    
    Args:
        mentioned_ids: Seller IDs explicitly mentioned
        active_sellers: List of currently active seller IDs
        fallback_to_all: If True and no mentions, return all active sellers
    
    Returns:
        List of seller IDs to route message to
    """
    # If mentions exist, filter to only active ones
    if mentioned_ids:
        targets = [sid for sid in mentioned_ids if sid in active_sellers]
        if targets:
            logger.debug(f"Routing to mentioned sellers: {targets}")
            return targets
        else:
            logger.warning(f"Mentioned sellers not active: {mentioned_ids}")
    
    # Fallback to all active sellers if configured
    if fallback_to_all:
        logger.debug(f"Routing to all active sellers: {active_sellers}")
        return active_sellers.copy()
    
    logger.debug("No targets selected")
    return []

