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
        max_tokens: int = 1024
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
            # Generate response - use model from room_state if available
            result = await self.provider.generate(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=None,
                model=getattr(room_state, 'llm_model', None)  # Use model from session if available
            )
            
            # Sanitize message
            message_text = self._sanitize_message(result.text)
            
            # Parse offer from JSON block if present
            offer = self._parse_offer(result.text)
            
            # Clamp offer to constraints
            if offer:
                offer = self._clamp_offer(offer)
            
            # Fallback: if message is empty but offer exists, generate a basic message
            if not message_text and offer:
                message_text = f"I can offer ${offer['price']:.2f} per unit for {offer['quantity']} units."
            
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
        Sanitize LLM output, removing JSON blocks and echoed conversation history.
        
        WHAT: Clean message text, remove offer JSON and prevent echo of conversation history
        WHY: Keep only the seller's original message, not repeated buyer messages
        HOW: Remove JSON blocks, detect and remove echoed history patterns, normalize whitespace
        """
        if not text:
            return ""
        
        # Remove JSON code blocks
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        # Remove JSON offer blocks and malformed JSON fragments
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\}\s*\}+', '', text)  # Remove trailing closing braces like "} }"
        
        # Split into lines and filter out echoed conversation history
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Skip lines that are clearly echoed conversation history
            # Pattern: "Name: message" where Name matches common buyer/seller names
            # This detects when the LLM is repeating the conversation history format
            if re.match(r'^(John Doe|Buyer|CompuWorld|GadgetHub|TechStore|Unknown):\s+', stripped, re.IGNORECASE):
                # This looks like echoed history, skip it
                # But allow if it's the seller's own name (they might reference themselves)
                if not stripped.startswith(f"{self.seller.name}:") and not stripped.startswith(f"{self.seller.name.upper()}:"):
                    continue
            
            # Also skip lines that look like conversation history markers
            # Pattern: "Conversation history:" or similar
            if re.match(r'^(Conversation history|Recent conversation|History):', stripped, re.IGNORECASE):
                continue
                
            filtered_lines.append(line)
        
        text = '\n'.join(filtered_lines)
        
        # Additional check: if the entire text starts with a name pattern that's not the seller's name,
        # it's likely echoed history - remove the leading name pattern
        # This handles cases where the buyer's entire message is echoed at the start
        seller_name_pattern = re.escape(self.seller.name)
        if not re.match(rf'^{seller_name_pattern}:', text, re.IGNORECASE):
            # Remove leading "Name: " pattern if present (but keep the rest)
            text = re.sub(r'^[A-Za-z\s]+:\s+', '', text, count=1)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Final check: if after all filtering the text is empty or only contains
        # remnants of echoed content (like just "@mentions" without context),
        # return empty string to trigger fallback message
        if not text or (len(text) < 10 and '@' in text):
            return ""
        
        # Limit length - increased for longer responses
        if len(text) > 2000:
            text = text[:1997] + "..."
        
        return text
    
    def _parse_offer(self, text: str) -> Optional[Offer]:
        """
        Parse offer from LLM output - try JSON first, then regex fallback.
        
        WHAT: Extract offer from text using multiple parsing strategies
        WHY: LLMs may not always format JSON correctly, need fallback
        HOW: Try JSON parsing first, then regex for price/quantity mentions
        """
        if not text:
            return None
        
        # Strategy 1: Try JSON block parsing
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
        
        # Strategy 2: Regex fallback - look for price mentions
        # Pattern: $XX.XX or XX.XX dollars/per unit/each
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)\s*(?:per unit|each|dollars?|USD)?',
            r'(\d+(?:\.\d{2})?)\s*(?:dollars?|USD)\s*(?:per unit|each)?',
            r'price[:\s]+(?:of\s+)?\$?(\d+(?:\.\d{2})?)',
            r'offer[:\s]+(?:of\s+)?\$?(\d+(?:\.\d{2})?)',
        ]
        
        # Pattern: quantity mentions
        qty_patterns = [
            r'(\d+)\s*(?:units?|items?|pieces?|qty)',
            r'quantity[:\s]+(\d+)',
        ]
        
        price = None
        quantity = None
        
        # Try to extract price
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        # Try to extract quantity
        for pattern in qty_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    quantity = int(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        # If we found price, return offer (use default quantity if not found)
        if price is not None:
            if quantity is None:
                quantity = self.inventory_item.quantity_available
            return {
                "price": price,
                "quantity": quantity
            }
        
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

