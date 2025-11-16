"""
Buyer agent implementation.

WHAT: Deterministic buyer agent that generates negotiation messages
WHY: Core buyer behavior for negotiation rounds
HOW: Use LLM provider with sanitization and mention extraction
"""

import re
from typing import Optional
from ..llm.provider import LLMProvider
from ..llm.types import ChatMessage
from ..models.agent import BuyerConstraints
from ..models.negotiation import NegotiationRoomState
from ..models.message import Message
from ..services.message_router import parse_mentions
from .prompts import render_buyer_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BuyerAgent:
    """Buyer agent that generates negotiation messages."""
    
    def __init__(
        self,
        provider: LLMProvider,
        constraints: BuyerConstraints,
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024
    ):
        """
        Initialize buyer agent.
        
        Args:
            provider: LLM provider instance
            constraints: Buyer's constraints for the item
            temperature: LLM temperature (default 0.0 for determinism)
            max_tokens: Maximum tokens to generate
        """
        self.provider = provider
        self.constraints = constraints
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    async def run_turn(
        self,
        room_state: NegotiationRoomState
    ) -> dict:
        """
        Generate buyer's message for current turn.
        
        WHAT: Use LLM to generate buyer message with constraints
        WHY: Buyer needs to negotiate based on conversation history
        HOW: Render prompt, call provider, sanitize output, extract mentions
        
        Args:
            room_state: Current negotiation room state
            
        Returns:
            Dict with "message" (str) and "mentioned_sellers" (list[str])
        """
        # Render prompt with context
        messages = render_buyer_prompt(
            buyer_name=room_state.buyer_name,
            constraints=self.constraints,
            conversation_history=room_state.conversation_history,
            available_sellers=room_state.sellers
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
            
            # Sanitize output
            message_text = self._sanitize_message(result.text)
            
            # Extract mentions
            mentioned_sellers = parse_mentions(message_text, room_state.sellers)
            
            logger.info(
                f"Buyer {room_state.buyer_name} generated message "
                f"(mentions: {len(mentioned_sellers)} sellers)"
            )
            
            return {
                "message": message_text,
                "mentioned_sellers": mentioned_sellers
            }
            
        except Exception as e:
            logger.error(f"Buyer agent error: {e}")
            # Fallback message
            return {
                "message": "I'm considering the offers. Please give me a moment.",
                "mentioned_sellers": []
            }
    
    def _sanitize_message(self, text: str) -> str:
        """
        Sanitize LLM output.
        
        WHAT: Clean and normalize message text
        WHY: Remove artifacts, normalize whitespace (reasoning tokens handled by frontend)
        HOW: Remove markdown/JSON blocks, normalize whitespace
        """
        if not text:
            return ""
        
        # Remove markdown code blocks if present
        text = re.sub(r'```[a-z]*\n?', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove JSON blocks (seller offers, not buyer)
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Limit length (safety check) - increased for longer messages
        if len(text) > 2000:
            text = text[:1997] + "..."
        
        return text

