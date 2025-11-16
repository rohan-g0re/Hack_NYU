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
        max_tokens: int = 256
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
            # Generate response (sanitization handles thinking removal)
            result = await self.provider.generate(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=None
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
        WHY: Remove artifacts, normalize whitespace, hide internal thinking
        HOW: Trim, collapse whitespace, remove markdown code blocks and thinking tags
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
        
        # Remove meta-commentary and thinking patterns (buyer should not narrate)
        thinking_patterns = [
            r'^Okay,?\s*let\'?s?\s*see\.?\s*',  # "Okay, let's see"
            r'^Let\'?s?\s*see\.?\s*',  # "Let's see"
            r'^The user wants?\s+.*?\.?\s*',  # "The user wants..."
            r'^The user(?:\'s|s)?\s+.*?\.?\s*',  # "The user's..."
            r'^I need to\s+.*?\.?\s*',  # "I need to..." (meta)
            r'^First,?\s*I need to\s+.*?\.?\s*',  # "First, I need to..."
            r'^Now,?\s*I(?:\'ll| will)\s+.*?\.?\s*',  # "Now, I'll..." (meta)
            r'^Wait,?\s*the\s+.*?\.?\s*',  # "Wait, the..."
            r'^So\s+I\s+should\s+.*?\.?\s*',  # "So I should..."
            r'^They(?:\'ve| have)\s+already\s+.*?\.?\s*',  # "They've already..."
            r'^Since\s+there\s+are\s+no\s+offers.*?\.?\s*',  # "Since there are no offers..."
        ]
        
        for pattern in thinking_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove markdown code blocks if present
        text = re.sub(r'```[a-z]*\n?', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove JSON blocks (seller offers, not buyer)
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Limit length (safety check)
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text

