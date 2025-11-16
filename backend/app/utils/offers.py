"""
Offer parsing and formatting utilities.

WHAT: Parse structured offers from LLM text output
WHY: Extract concrete price/quantity from natural language
HOW: Regex + JSON parsing with fallback handling
"""

import json
import re
from typing import Dict, Any

from ..utils.logger import get_logger

logger = get_logger(__name__)


def parse_offer_block(text: str) -> Dict[str, Any] | None:
    """
    Parse an offer block from LLM-generated text.
    
    Expected formats:
    - ```offer {"price": 10.5, "quantity": 100, "item_id": "widget"}```
    - Offer: {"price": 10.5, "quantity": 100}
    - JSON anywhere in text with price and quantity keys
    
    Args:
        text: LLM response text potentially containing an offer
    
    Returns:
        Dict with price, quantity, item_id (optional) or None if no valid offer
    """
    if not text:
        return None
    
    # Try fenced code block first: ```offer {...}```
    fence_pattern = r'```offer\s*(\{[^`]+\})\s*```'
    fence_match = re.search(fence_pattern, text, re.IGNORECASE | re.DOTALL)
    
    if fence_match:
        try:
            offer_data = json.loads(fence_match.group(1))
            if _validate_offer_structure(offer_data):
                logger.debug("Parsed offer from fenced block")
                return offer_data
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in fenced offer block: {e}")
    
    # Try "Offer:" prefix pattern
    prefix_pattern = r'Offer:\s*(\{[^}]+\})'
    prefix_match = re.search(prefix_pattern, text, re.IGNORECASE)
    
    if prefix_match:
        try:
            offer_data = json.loads(prefix_match.group(1))
            if _validate_offer_structure(offer_data):
                logger.debug("Parsed offer from Offer: prefix")
                return offer_data
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in Offer: prefix: {e}")
    
    # Try any JSON object with price and quantity
    json_pattern = r'\{[^}]*"price"[^}]*"quantity"[^}]*\}'
    json_matches = re.finditer(json_pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in json_matches:
        try:
            offer_data = json.loads(match.group(0))
            if _validate_offer_structure(offer_data):
                logger.debug("Parsed offer from inline JSON")
                return offer_data
        except json.JSONDecodeError:
            continue
    
    logger.debug("No valid offer found in text")
    return None


def _validate_offer_structure(data: Dict[str, Any]) -> bool:
    """
    Validate that offer dict has required fields with correct types.
    
    Args:
        data: Parsed offer dictionary
    
    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    # Must have price and quantity
    if "price" not in data or "quantity" not in data:
        return False
    
    # Type validation
    try:
        price = float(data["price"])
        quantity = int(data["quantity"])
        
        if price <= 0 or quantity <= 0:
            return False
        
        # item_id is optional
        if "item_id" in data and not isinstance(data["item_id"], str):
            return False
        
        return True
    except (ValueError, TypeError):
        return False


def format_offer_block(price: float, quantity: int, item_id: str | None = None) -> str:
    """
    Format an offer as structured text for LLM instruction examples.
    
    Args:
        price: Price per unit
        quantity: Quantity offered
        item_id: Optional item identifier
    
    Returns:
        Formatted offer string
    """
    offer_dict = {
        "price": price,
        "quantity": quantity
    }
    
    if item_id:
        offer_dict["item_id"] = item_id
    
    return f'```offer\n{json.dumps(offer_dict, indent=2)}\n```'


def extract_price_quantity_from_text(text: str) -> tuple[float | None, int | None]:
    """
    Extract price and quantity from natural language as fallback.
    
    Args:
        text: Natural language text
    
    Returns:
        Tuple of (price, quantity) or (None, None) if not found
    """
    price = None
    quantity = None
    
    # Try to extract price (various formats: $10, 10 USD, 10.50, etc.)
    price_patterns = [
        r'\$\s*(\d+(?:\.\d{2})?)',  # $10.50
        r'(\d+(?:\.\d{2})?)\s*(?:USD|dollars?)',  # 10.50 USD
        r'price[:\s]+\$?\s*(\d+(?:\.\d{2})?)',  # price: $10.50
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1))
                break
            except ValueError:
                continue
    
    # Try to extract quantity
    quantity_patterns = [
        r'(\d+)\s+units?',  # 100 units
        r'quantity[:\s]+(\d+)',  # quantity: 100
        r'(\d+)\s+pieces?',  # 100 pieces
    ]
    
    for pattern in quantity_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                quantity = int(match.group(1))
                break
            except ValueError:
                continue
    
    return price, quantity

