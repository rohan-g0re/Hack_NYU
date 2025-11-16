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
        max_tokens: int = 192
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
            # Generate response
            result = await self.provider.generate(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=None
            )
            
            raw_response = result.text  # Store for debug event
            
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
                "offer": offer,
                "raw_response": raw_response  # Include raw response for debugging
            }
            
        except Exception as e:
            logger.error(f"Seller agent error for {self.seller.name}: {e}")
            # Fallback message
            return {
                "message": "I'm reviewing your request. Let me get back to you.",
                "offer": None,
                "raw_response": f"ERROR: {str(e)}"
            }
    
    def _sanitize_message(self, text: str) -> str:
        """
        Sanitize LLM output based on observed qwen3-1.7b format.
        
        WHAT: Clean message text, remove offer JSON and meta-commentary
        WHY: Keep only natural conversational dialogue
        HOW: Extract actual message after </think> tags, remove all artifacts
        
        Expected format: <think>...</think> [actual message] [optional: JSON offer]
        """
        if not text:
            return ""
        
        # Strategy 1: If </think> exists, take everything after the LAST </think>
        if '</think>' in text.lower():
            # Find the last occurrence of </think> (case-insensitive)
            parts = re.split(r'</think>', text, flags=re.IGNORECASE | re.DOTALL)
            if len(parts) > 1:
                # Take everything after the last </think>
                text = parts[-1]
        
        # Strategy 2: Remove any remaining <think>...</think> blocks (in case of nested or malformed)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove any orphaned opening tags
        text = re.sub(r'<think>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<reasoning>', '', text, flags=re.IGNORECASE)
        
        # Remove JSON code blocks
        text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'```\s*', '', text)
        
        # Remove JSON offer blocks
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove "---" separator that might appear between thinking and message
        text = re.sub(r'\s*---+\s*', ' ', text)
        
        # Remove common meta-commentary patterns (more aggressive)
        text = re.sub(r'^(Okay,?\s+)?(let me|let\'s|I need to|I should|I want to|I will)\s+.*?[.!]\s+', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'^(Okay,?\s+)?(the user wants|user mentioned|John Doe|the buyer|user said)\s+.*?[.!]\s+', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'(First,?\s+|Second,?\s+|Then,?\s+|Also,?\s+|Maybe\s+)', '', text, flags=re.IGNORECASE)
        
        # Remove any sentences that contain meta-commentary keywords
        sentences = text.split('. ')
        filtered_sentences = []
        meta_keywords = ['check the', 'address each', 'current offer', 'should ask', 'need to', 'want to', 'let me', 'I should', 'maybe', 'user is', 'user has', 'buyer is', 'buyer has']
        for sentence in sentences:
            if not any(keyword in sentence.lower() for keyword in meta_keywords):
                filtered_sentences.append(sentence)
        text = '. '.join(filtered_sentences)
        
        # Remove any remaining XML-like tags as a catch-all
        text = re.sub(r'<[^>]+>', '', text)
        
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

