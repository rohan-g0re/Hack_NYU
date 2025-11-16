"""
Message routing and mention parsing.

WHAT: Extract seller mentions from buyer messages
WHY: Route messages to specific sellers based on @mentions
HOW: Regex parsing with name normalization
"""

import re
from typing import List
from ..models.agent import Seller
from ..utils.logger import get_logger

logger = get_logger(__name__)


def parse_mentions(text: str, sellers: List[Seller]) -> List[str]:
    """
    Parse @mentions from text and return matching seller IDs.
    
    WHAT: Extract @SellerName mentions and map to seller IDs
    WHY: Route messages to specific sellers based on mentions
    HOW: Regex pattern matching with name normalization
    
    Args:
        text: Message text to parse
        sellers: List of available sellers
        
    Returns:
        List of seller IDs mentioned in the text
    """
    if not text or not sellers:
        return []
    
    # Create normalization map: normalized_name -> seller_id
    # Normalize: lowercase, remove spaces/special chars
    normalization_map: dict[str, str] = {}
    for seller in sellers:
        normalized = _normalize_name(seller.name)
        normalization_map[normalized] = seller.seller_id
        # Also map original name (case-insensitive)
        normalization_map[seller.name.lower()] = seller.seller_id
    
    # Find all @mentions using regex
    # Pattern matches @ followed by one or more words (letters, numbers, underscores)
    # Words can be separated by spaces, stops at punctuation or another @
    mention_pattern = r'@([A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+)*)'
    matches = re.findall(mention_pattern, text)
    
    logger.debug(f"Parsing mentions from text: {text[:100]}")
    logger.debug(f"Found mention matches: {matches}")
    logger.debug(f"Available sellers: {[(s.name, s.seller_id) for s in sellers]}")
    
    mentioned_ids = []
    seen_ids = set()
    
    for match in matches:
        # Strip whitespace from the match
        match = match.strip()
        if not match:
            continue
            
        normalized = _normalize_name(match)
        seller_id = normalization_map.get(normalized) or normalization_map.get(match.lower())
        
        if seller_id:
            if seller_id not in seen_ids:
                logger.debug(f"Matched mention '{match}' (normalized: '{normalized}') to seller ID: {seller_id}")
                mentioned_ids.append(seller_id)
                seen_ids.add(seller_id)
        else:
            logger.warning(f"Could not match mention '{match}' (normalized: '{normalized}') to any seller")
    
    logger.debug(f"Final mentioned seller IDs: {mentioned_ids}")
    return mentioned_ids


def _normalize_name(name: str) -> str:
    """
    Normalize seller name for matching.
    
    WHAT: Convert name to matchable format
    WHY: Handle case-insensitive and whitespace variations
    HOW: Lowercase and remove special characters
    """
    # Lowercase and remove spaces/special chars (keep alphanumeric and underscore)
    normalized = re.sub(r'[^a-z0-9_]', '', name.lower())
    return normalized

