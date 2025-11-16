"""
Conversation history truncation utilities.

WHAT: Intelligently truncate conversation history to prevent context overflow
WHY: LLM context windows are limited, need to stay within token/character limits
HOW: Keep most recent messages while respecting character limits
"""

from typing import List
from ..models.message import Message
from ..utils.logger import get_logger

logger = get_logger(__name__)


def truncate_conversation_history(
    history: List[Message],
    max_messages: int = 10,
    max_chars: int = 4000
) -> List[Message]:
    """
    Intelligently truncate conversation history to prevent context overflow.
    
    WHAT: Limit conversation history to fit within context window
    WHY: Prevent token overflow and reduce prompt size
    HOW: Keep most recent messages, remove oldest if over character limit
    
    Strategy:
    1. Keep most recent messages (up to max_messages)
    2. If total chars exceed max_chars, truncate oldest messages first
    3. Always keep the most recent message (even if it exceeds limit alone)
    
    Args:
        history: Full conversation history
        max_messages: Maximum number of messages to keep (default: 10)
        max_chars: Maximum total characters across all messages (default: 4000)
        
    Returns:
        Truncated list of messages that fit within limits
    """
    if not history:
        return []
    
    # Start with most recent messages
    truncated = history[-max_messages:] if len(history) > max_messages else history.copy()
    
    # Calculate total character count
    total_chars = sum(len(str(msg.get('content', ''))) for msg in truncated)
    
    # If over limit, remove oldest messages until under limit
    # But always keep at least the most recent message
    while total_chars > max_chars and len(truncated) > 1:
        removed = truncated.pop(0)
        removed_chars = len(str(removed.get('content', '')))
        total_chars -= removed_chars
        logger.debug(
            f"Truncated message from history: {removed.get('sender_name', 'Unknown')} "
            f"({removed_chars} chars, remaining: {total_chars}/{max_chars})"
        )
    
    # Log truncation if it occurred
    if len(truncated) < len(history):
        logger.info(
            f"Truncated conversation history: {len(history)} -> {len(truncated)} messages "
            f"({total_chars}/{max_chars} chars)"
        )
    
    return truncated

