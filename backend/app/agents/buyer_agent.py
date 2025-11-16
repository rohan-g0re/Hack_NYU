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
            # Generate response
            result = await self.provider.generate(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stop=None
            )
            
            raw_response = result.text  # Store for debug event
            
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
                "mentioned_sellers": mentioned_sellers,
                "raw_response": raw_response  # Include raw response for debugging
            }
            
        except Exception as e:
            logger.error(f"Buyer agent error: {e}")
            # Fallback message
            return {
                "message": "I'm considering the offers. Please give me a moment.",
                "mentioned_sellers": [],
                "raw_response": f"ERROR: {str(e)}"
            }
    
    def _sanitize_message(self, text: str) -> str:
        """
        Sanitize LLM output based on observed qwen3-1.7b format.
        
        WHAT: Clean and normalize message text
        WHY: Remove artifacts, thinking tags, meta-commentary
        HOW: Extract actual message after </think> tags, remove all meta-commentary
        
        Expected format: <think>...</think> [actual message]
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
        
        # Remove markdown code blocks
        text = re.sub(r'```[a-z]*\n?', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove JSON blocks (seller offers, not buyer)
        text = re.sub(r'\{[^}]*"offer"[^}]*\}', '', text, flags=re.IGNORECASE)
        
        # Remove "---" separator that might appear between thinking and message
        text = re.sub(r'\s*---+\s*', ' ', text)
        
        # Remove common meta-commentary patterns (more aggressive)
        text = re.sub(r'^(Okay,?\s+)?(let me|let\'s|I need to|I should|I want to|I will)\s+.*?[.!]\s+', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'^(Okay,?\s+)?(the user wants|user mentioned|user said|the available)\s+.*?[.!]\s+', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'(First,?\s+|Second,?\s+|Then,?\s+|Also,?\s+|Maybe\s+)', '', text, flags=re.IGNORECASE)
        
        # Remove any sentences that contain meta-commentary keywords
        sentences = text.split('. ')
        filtered_sentences = []
        meta_keywords = ['check the', 'mention them', 'compare offers', 'should ask', 'need to', 'want to', 'let me', 'I should', 'maybe', 'user is', 'user has']
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
        
        # Limit length (safety check)
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text

