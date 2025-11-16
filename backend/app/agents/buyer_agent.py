"""
Buyer agent implementation.

WHAT: Autonomous buyer agent for negotiations
WHY: Represent buyer interests with LLM-powered decision making
HOW: LLM provider integration with sanitization and mention parsing
"""

import re
from typing import List
from datetime import datetime

from ..llm.provider import LLMProvider
from ..llm.types import ProviderTimeoutError, ProviderResponseError, ProviderUnavailableError
from ..llm.streaming_handler import coalesce_and_bound
from ..models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    Message,
    BuyerTurnResult
)
from ..services.visibility_filter import filter_for_buyer
from ..services.message_router import parse_mentions
from ..agents.prompts import render_buyer_prompt
from ..utils.exceptions import BuyerAgentError
from ..utils.logger import get_logger
from ..utils.word_limit import enforce_word_limit, count_words, MAX_WORDS_PER_MESSAGE
from ..core.config import settings

logger = get_logger(__name__)


class BuyerAgent:
    """
    Buyer agent that negotiates on behalf of the buyer.
    
    WHAT: LLM-powered agent representing buyer in negotiations
    WHY: Autonomous negotiation within defined constraints
    HOW: Prompt engineering + provider calls + output sanitization
    """
    
    def __init__(
        self,
        provider: LLMProvider,
        constraints: BuyerConstraints,
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None
    ):
        """
        Initialize buyer agent.
        
        Args:
            provider: LLM provider instance
            constraints: Buyer's negotiation constraints
            stream: Whether to use streaming mode
            temperature: Override default temperature
            max_tokens: Override default max tokens
        """
        self.provider = provider
        self.constraints = constraints
        self.stream = stream
        self.temperature = temperature or settings.LLM_DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_DEFAULT_MAX_TOKENS
        
        logger.info(f"BuyerAgent initialized (stream={stream}, temp={self.temperature})")
    
    async def run_turn(self, room_state: NegotiationRoomState) -> BuyerTurnResult:
        """
        Execute one buyer turn in the negotiation.
        
        WHAT: Generate buyer message for current round
        WHY: Advance negotiation on buyer's behalf
        HOW: Filter history, render prompt, call LLM, sanitize output
        
        Args:
            room_state: Current negotiation state
        
        Returns:
            BuyerTurnResult with message and mentioned sellers
        
        Raises:
            BuyerAgentError: If agent processing fails
        """
        try:
            # Filter conversation to buyer-visible messages
            visible_history = filter_for_buyer(room_state.message_history, room_state.buyer_id)
            
            # Fast dev mode: trim history to last 4 messages (2 exchanges) to reduce context
            if room_state.metadata.get("fast_dev", False):
                visible_history = visible_history[-4:]
            
            # Render prompt
            messages = render_buyer_prompt(room_state, visible_history)
            
            logger.debug(
                f"Buyer turn in room {room_state.room_id}, round {room_state.current_round}, "
                f"{len(messages)} messages in prompt"
            )
            
            # Call LLM provider
            if self.stream:
                raw_text = await self._generate_streaming(messages)
            else:
                raw_text = await self._generate_blocking(messages)
            
            # Sanitize output
            sanitized_text, was_sanitized = self._sanitize_output(raw_text)
            
            if was_sanitized:
                logger.info(f"Buyer output sanitized in room {room_state.room_id}")
            
            # Enforce 30-word limit
            word_count = count_words(sanitized_text)
            if word_count > MAX_WORDS_PER_MESSAGE:
                logger.warning(
                    f"Buyer message exceeded word limit: {word_count} words "
                    f"(limit: {MAX_WORDS_PER_MESSAGE}), truncating"
                )
                sanitized_text = enforce_word_limit(sanitized_text, MAX_WORDS_PER_MESSAGE)
                was_sanitized = True
            
            # Parse mentions
            mentioned_sellers = parse_mentions(sanitized_text, room_state.seller_profiles)
            
            logger.info(
                f"Buyer turn complete: {len(sanitized_text)} chars, "
                f"{len(mentioned_sellers)} mentions"
            )
            
            return BuyerTurnResult(
                message=sanitized_text,
                mentioned_sellers=mentioned_sellers,
                raw_text=raw_text,
                sanitized=was_sanitized
            )
            
        except (ProviderTimeoutError, ProviderResponseError, ProviderUnavailableError) as e:
            logger.error(f"Provider error in buyer turn: {e}")
            raise BuyerAgentError(
                f"LLM provider error: {str(e)}",
                room_id=room_state.room_id,
                round_number=room_state.current_round
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in buyer turn: {e}", exc_info=True)
            raise BuyerAgentError(
                f"Buyer agent error: {str(e)}",
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
        chunks = await self.provider.stream(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Coalesce and bound stream
        bounded = coalesce_and_bound(chunks, max_chars=2000)
        
        # Collect all chunks
        text_parts = []
        async for text_chunk in bounded:
            text_parts.append(text_chunk)
        
        return "".join(text_parts)
    
    def _sanitize_output(self, text: str) -> tuple[str, bool]:
        """
        Sanitize buyer output to remove leaked information and ensure tone.
        
        WHAT: Clean LLM output for safety and compliance
        WHY: Prevent leaked seller internals, maintain tone
        HOW: Regex filtering + length limits
        
        Args:
            text: Raw LLM output
        
        Returns:
            Tuple of (sanitized_text, was_modified)
        """
        original = text
        modified = False
        
        # Trim whitespace
        text = text.strip()
        
        # Remove or mask forbidden internal terms
        forbidden_patterns = [
            (r'\bleast\s+price\b', '[price]', 'least price'),
            (r'\bcost\s+price\b', '[price]', 'cost price'),
            (r'\btheir\s+cost\b', '[cost]', 'their cost'),
            (r'\binternal\s+(?:price|cost)\b', '[internal info]', 'internal price/cost'),
            (r'\bseller[\'s]*\s+(?:cost|floor|minimum)\b', '[seller info]', 'seller cost/floor'),
        ]
        
        for pattern, replacement, desc in forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                modified = True
                logger.warning(f"Sanitized forbidden term: {desc}")
        
        # Basic profanity filter (minimal set for production use)
        profanity_patterns = [
            r'\b(fuck|shit|damn|hell|ass|crap)\w*\b'
        ]
        
        for pattern in profanity_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, '[removed]', text, flags=re.IGNORECASE)
                modified = True
                logger.warning("Sanitized profanity")
        
        # Enforce max length (2000 chars hard limit)
        if len(text) > 2000:
            text = text[:2000].rsplit(' ', 1)[0] + "..."
            modified = True
            logger.warning("Truncated long output")
        
        # Ensure it ends with proper punctuation
        if text and text[-1] not in '.!?':
            text = text + '.'
            modified = True
        
        return text, modified or (text != original)

