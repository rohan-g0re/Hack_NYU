"""
Seller agent implementation.

WHAT: Deterministic seller agent that generates responses and offers
WHY: Core seller behavior for negotiation rounds
HOW: Use LLM provider, parse offers, clamp to constraints
"""

import json
import re
from typing import Optional
from ..llm.provider import LLMProvider
from ..models.agent import Seller, InventoryItem, BuyerConstraints
from ..models.negotiation import NegotiationRoomState
from ..models.message import Message, Offer
from .prompts import render_seller_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SellerAgent:
    """Seller agent that generates responses and offers."""
    
    def __init__(
        self,
        provider: LLMProvider,
        seller: Seller,
        inventory_item: InventoryItem,
        *,
        temperature: float = 0.0,
        max_tokens: int = 256
    ):
        """
        Initialize seller agent.
        
        Args:
            provider: LLM provider instance
            seller: Seller configuration
            inventory_item: Item being negotiated
            temperature: LLM temperature (default 0.0 for determinism)
            max_tokens: Maximum tokens to generate
        """
        self.provider = provider
        self.seller = seller
        self.inventory_item = inventory_item
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def respond(
        self,
        room_state: NegotiationRoomState,
        buyer_name: str,
        constraints: BuyerConstraints
    ) -> dict:
        """
        Generate seller's response for current turn.
        
        WHAT: Use LLM to generate seller message and optional offer
        WHY: Seller needs to negotiate based on conversation and constraints
        HOW: Render prompt, call provider, parse offer JSON, clamp to constraints
        
        Args:
            room_state: Current negotiation room state
            buyer_name: Name of the buyer
            constraints: Buyer's constraints
            
        Returns:
            Dict with "message" (str) and optional "offer" (dict with price, quantity)
        """
        # Render prompt with context
        messages = render_seller_prompt(
            seller=self.seller,
            constraints=constraints,
            conversation_history=room_state.conversation_history,
            buyer_name=buyer_name
        )
        
        try:
            # Generate response (sanitization handles thinking removal)
            result = await self.provider.generate(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=None
            )
            
            # Sanitize message
            message_text = self._sanitize_message(result.text)
            
            # Parse offer from JSON block if present
            offer = self._parse_offer(result.text)
            
            # Clamp offer to constraints
            if offer:
                offer = self._clamp_offer(offer)
            
            logger.info(
                f"Seller {self.seller.name} generated response "
                f"(offer: {offer is not None})"
            )
            
            return {
                "message": message_text,
                "offer": offer
            }
            
        except Exception as e:
            logger.error(f"Seller agent error for {self.seller.name}: {e}")
            # Fallback message
            return {
                "message": "I'm reviewing your request. Let me get back to you.",
                "offer": None
            }
    
    def _sanitize_message(self, text: str) -> str:
        """
        Sanitize LLM output, removing JSON blocks and thinking tags.
        
        WHAT: Clean message text, remove offer JSON and internal reasoning
        WHY: Keep only the conversational message
        HOW: Remove JSON blocks, thinking tags, normalize whitespace
        """
        if not text:
            return ""
        
        # Remove thinking tags and their content
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove sentence continuation patterns (Bug #3 fix)
        # Detect if message starts with lowercase or ellipsis (likely continuation)
        continuation_patterns = [
            r'^\.\.\.+\s*',  # Starting with ellipsis
            r'^\.\s+',  # Starting with period
            r'^,\s+',  # Starting with comma
            r'^and\s+',  # Starting with "and"
            r'^but\s+',  # Starting with "but"
            r'^or\s+',  # Starting with "or"
            r'^so\s+',  # Starting with "so" (when used as connector)
        ]
        
        for pattern in continuation_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove meta-commentary patterns
        meta_patterns = [
            r'^Okay,?\s*let\'?s?\s*see\.?\s*',  # "Okay, let's see"
            r'^Let me think\.?\s*',  # "Let me think"
            r'^I should\s+.*?\.?\s*',  # "I should..."
        ]
        
        for pattern in meta_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove JSON code blocks
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        # Remove JSON offer blocks
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Limit length
        if len(text) > 400:
            text = text[:397] + "..."
        
        return text
    
    def _parse_offer(self, text: str) -> Optional[Offer]:
        """
        Parse offer JSON from LLM output.
        
        WHAT: Extract offer JSON block from text
        WHY: Seller may include structured offer
        HOW: Find JSON block, parse, extract offer dict
        """
        if not text:
            return None
        
        # Try to find JSON block
        json_pattern = r'\{[^}]*"offer"[^}]*\}'
        matches = re.findall(json_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "offer" in data and isinstance(data["offer"], dict):
                    offer = data["offer"]
                    if "price" in offer and "quantity" in offer:
                        return {
                            "price": float(offer["price"]),
                            "quantity": int(offer["quantity"])
                        }
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        return None
    
    def _clamp_offer(self, offer: Offer) -> Optional[Offer]:
        """
        Clamp offer to seller's constraints.
        
        WHAT: Ensure offer is within valid bounds
        WHY: Enforce business rules (price range, quantity limits)
        HOW: Clamp price and quantity to valid ranges
        
        Args:
            offer: Offer dict with price and quantity
            
        Returns:
            Clamped offer or None if invalid
        """
        if not offer:
            return None
        
        price = offer.get("price", 0)
        quantity = offer.get("quantity", 0)
        
        # Clamp price to [least_price, selling_price]
        price = max(self.inventory_item.least_price, price)
        price = min(self.inventory_item.selling_price, price)
        
        # Clamp quantity to [1, quantity_available]
        quantity = max(1, quantity)
        quantity = min(self.inventory_item.quantity_available, quantity)
        
        # Validate final offer
        if price < self.inventory_item.least_price:
            logger.warning(
                f"Seller {self.seller.name} offer price {price} below minimum "
                f"{self.inventory_item.least_price}, rejecting"
            )
            return None
        
        if price > self.inventory_item.selling_price:
            logger.warning(
                f"Seller {self.seller.name} offer price {price} above maximum "
                f"{self.inventory_item.selling_price}, rejecting"
            )
            return None
        
        if quantity < 1 or quantity > self.inventory_item.quantity_available:
            logger.warning(
                f"Seller {self.seller.name} offer quantity {quantity} invalid, "
                f"available: {self.inventory_item.quantity_available}"
            )
            return None
        
        return {
            "price": price,
            "quantity": quantity
        }

