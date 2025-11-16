"""
Seller agent implementation.

WHAT: Autonomous seller agent for negotiations
WHY: Represent seller interests with personality and constraints
HOW: LLM provider integration with offer validation and style enforcement
"""

import re
from typing import List
from datetime import datetime

from ..llm.provider import LLMProvider
from ..llm.types import ProviderTimeoutError, ProviderResponseError, ProviderUnavailableError
from ..models.negotiation import (
    NegotiationRoomState,
    SellerProfile,
    InventoryItem,
    Offer,
    SellerResponse
)
from ..services.visibility_filter import filter_for_seller
from ..agents.prompts import render_seller_prompt
from ..utils.offers import parse_offer_block
from ..utils.exceptions import SellerAgentError
from ..utils.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class SellerAgent:
    """
    Seller agent that negotiates on behalf of a seller.
    
    WHAT: LLM-powered agent representing seller in negotiations
    WHY: Autonomous negotiation with personality and business constraints
    HOW: Prompt engineering + provider calls + offer validation
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        profile: SellerProfile,
        inventory: List[InventoryItem],
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None
    ):
        """
        Initialize seller agent.
        
        Args:
            provider: LLM provider instance
            profile: Seller's profile (personality, priorities)
            inventory: List of inventory items
            stream: Whether to use streaming mode
            temperature: Override default temperature
            max_tokens: Override default max tokens
        """
        self.provider = provider
        self.profile = profile
        self.inventory = inventory
        self.stream = stream
        self.temperature = temperature or settings.LLM_DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_DEFAULT_MAX_TOKENS
        
        # Build inventory lookup
        self.inventory_map = {item.item_id: item for item in inventory}
        
        logger.info(
            f"SellerAgent initialized: {profile.display_name} "
            f"({profile.priority}, {profile.speaking_style}), "
            f"{len(inventory)} items"
        )
    
    async def respond(self, room_state: NegotiationRoomState) -> SellerResponse:
        """
        Generate seller response to current negotiation state.
        
        WHAT: Produce seller message and optional offer
        WHY: Advance negotiation on seller's behalf
        HOW: Filter history, render prompt, call LLM, validate offer
        
        Args:
            room_state: Current negotiation state
        
        Returns:
            SellerResponse with message, offer, and any violations
        
        Raises:
            SellerAgentError: If agent processing fails
        """
        try:
            # Filter conversation to seller-visible messages
            visible_history = filter_for_seller(
                room_state.message_history,
                self.profile.seller_id
            )
            
            # Render prompt
            messages = render_seller_prompt(
                room_state,
                self.profile.seller_id,
                visible_history
            )
            
            logger.debug(
                f"Seller {self.profile.seller_id} responding in room {room_state.room_id}, "
                f"round {room_state.current_round}, {len(messages)} messages in prompt"
            )
            
            # Call LLM provider
            if self.stream:
                raw_text = await self._generate_streaming(messages)
            else:
                raw_text = await self._generate_blocking(messages)
            
            # Apply style enforcement
            styled_text = self._enforce_style(raw_text)
            
            # Parse and validate offer
            offer, violations = self._extract_and_validate_offer(
                styled_text,
                room_state
            )
            
            if violations:
                logger.warning(
                    f"Seller {self.profile.seller_id} offer violations: {violations}"
                )
            
            logger.info(
                f"Seller {self.profile.seller_id} response complete: "
                f"{len(styled_text)} chars, offer={'yes' if offer else 'no'}"
            )
            
            return SellerResponse(
                seller_id=self.profile.seller_id,
                message=styled_text,
                offer=offer,
                violations=violations,
                raw_text=raw_text
            )
            
        except (ProviderTimeoutError, ProviderResponseError, ProviderUnavailableError) as e:
            logger.error(f"Provider error in seller {self.profile.seller_id} response: {e}")
            raise SellerAgentError(
                f"LLM provider error: {str(e)}",
                seller_id=self.profile.seller_id,
                room_id=room_state.room_id,
                round_number=room_state.current_round
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error in seller {self.profile.seller_id} response: {e}",
                exc_info=True
            )
            raise SellerAgentError(
                f"Seller agent error: {str(e)}",
                seller_id=self.profile.seller_id,
                room_id=room_state.room_id,
                round_number=room_state.current_round
            ) from e
    
    async def _generate_blocking(self, messages: List) -> str:
        """Generate response using blocking LLM call."""
        result = await self.provider.generate(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return result.text
    
    async def _generate_streaming(self, messages: List) -> str:
        """Generate response using streaming LLM call."""
        from ..llm.streaming_handler import coalesce_and_bound
        
        chunks = await self.provider.stream(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Coalesce and bound stream
        bounded = coalesce_and_bound(chunks, max_chars=1500)
        
        # Collect all chunks
        text_parts = []
        async for text_chunk in bounded:
            text_parts.append(text_chunk)
        
        return "".join(text_parts)
    
    def _enforce_style(self, text: str) -> str:
        """
        Enforce speaking style on output.
        
        WHAT: Adjust text to match seller's speaking_style
        WHY: Ensure personality consistency
        HOW: Inject style markers if missing
        
        Args:
            text: Raw LLM output
        
        Returns:
            Style-adjusted text
        """
        text = text.strip()
        
        if self.profile.speaking_style == "rude":
            # Ensure blunt, no pleasantries
            # Remove overly polite phrases if present
            polite_patterns = [
                r'\bplease\b',
                r'\bthank you\b',
                r'\bI appreciate\b',
                r'\bI\'m happy to\b'
            ]
            for pattern in polite_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
            # Make more direct if too wordy
            if len(text) > 300:
                text = text[:300].rsplit('.', 1)[0] + '.'
        
        elif self.profile.speaking_style == "very_sweet":
            # Ensure warm, appreciative tone
            # Check for positive markers
            sweet_markers = [
                'appreciate', 'thank', 'wonderful', 'great', 'happy',
                'pleased', 'excited', 'delighted'
            ]
            
            has_sweet_marker = any(
                marker in text.lower() for marker in sweet_markers
            )
            
            if not has_sweet_marker and len(text) < 500:
                # Inject appreciation
                if not text.endswith('!'):
                    text = text.rstrip('.') + '!'
        
        # Trim to max length
        if len(text) > 1500:
            text = text[:1500].rsplit(' ', 1)[0] + '...'
        
        return text
    
    def _extract_and_validate_offer(
        self,
        text: str,
        room_state: NegotiationRoomState
    ) -> tuple[Offer | None, List[str]]:
        """
        Extract offer from text and validate against constraints.
        
        WHAT: Parse offer block and validate price/quantity
        WHY: Ensure offers comply with business rules
        HOW: Parse JSON, check bounds, return violations
        
        Args:
            text: Seller message text
            room_state: Current negotiation state
        
        Returns:
            Tuple of (validated_offer, violations_list)
        """
        violations = []
        
        # Try to parse offer
        offer_data = parse_offer_block(text)
        
        if not offer_data:
            # No offer found, that's okay
            return None, violations
        
        # Extract fields
        price = offer_data.get("price")
        quantity = offer_data.get("quantity")
        item_id = offer_data.get("item_id", room_state.buyer_constraints.item_id)
        
        # Find inventory item
        inventory_item = self.inventory_map.get(item_id)
        
        if not inventory_item:
            violations.append(f"Unknown item_id: {item_id}")
            return None, violations
        
        # Validate price bounds
        if price < inventory_item.least_price:
            violations.append(
                f"Price ${price:.2f} below least_price ${inventory_item.least_price:.2f}"
            )
            # Don't create offer below least_price
            return None, violations
        
        if price > inventory_item.selling_price * 1.5:  # Allow some markup but not absurd
            violations.append(
                f"Price ${price:.2f} unreasonably high (>1.5x selling price)"
            )
            # Cap at reasonable maximum
            price = inventory_item.selling_price * 1.2
        
        # Validate quantity
        if quantity > inventory_item.quantity_available:
            violations.append(
                f"Quantity {quantity} exceeds available {inventory_item.quantity_available}"
            )
            # Cap at available
            quantity = inventory_item.quantity_available
        
        if quantity <= 0:
            violations.append(f"Invalid quantity: {quantity}")
            return None, violations
        
        # Create valid offer
        offer = Offer(
            seller_id=self.profile.seller_id,
            item_id=item_id,
            price=price,
            quantity=quantity,
            round_number=room_state.current_round,
            status="pending"
        )
        
        return offer, violations

