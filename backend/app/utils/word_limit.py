"""
Word limit enforcement utilities.

WHAT: Helper functions to enforce word count limits on agent responses
WHY: Ensure concise communication (30 words max per message)
HOW: Word counting and intelligent truncation
"""

import re
from typing import Tuple
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Maximum words allowed per message
MAX_WORDS_PER_MESSAGE = 30


def count_words(text: str) -> int:
    """
    Count words in text.
    
    WHAT: Simple word counter
    WHY: Enforce word limits accurately
    HOW: Split on whitespace and count non-empty tokens
    
    Args:
        text: Input text
    
    Returns:
        Number of words
    """
    if not text or not text.strip():
        return 0
    
    # Split on whitespace and filter empty strings
    words = [w for w in re.split(r'\s+', text.strip()) if w]
    return len(words)


def truncate_to_word_limit(text: str, max_words: int = MAX_WORDS_PER_MESSAGE) -> Tuple[str, bool]:
    """
    Truncate text to maximum word count, preserving sentence boundaries when possible.
    
    WHAT: Intelligent truncation at word boundaries
    WHY: Enforce limits while maintaining readability
    HOW: Count words, truncate at sentence end if possible, else at word boundary
    
    Args:
        text: Input text to truncate
        max_words: Maximum number of words allowed
    
    Returns:
        Tuple of (truncated_text, was_truncated)
    """
    if not text:
        return text, False
    
    word_count = count_words(text)
    
    if word_count <= max_words:
        return text, False
    
    # Try to truncate at sentence boundary
    words = text.split()
    truncated_words = words[:max_words]
    
    # Check if we can end at a sentence boundary
    truncated_text = ' '.join(truncated_words)
    
    # Look for sentence-ending punctuation in the last few words
    last_few = ' '.join(words[max(0, max_words-5):max_words])
    sentence_end_match = re.search(r'[.!?]\s*$', last_few)
    
    if sentence_end_match:
        # Already ends with sentence punctuation
        truncated_text = ' '.join(words[:max_words])
    else:
        # Try to find a sentence end in the truncated portion
        # Look backwards from max_words for sentence punctuation
        for i in range(max_words - 1, max(0, max_words - 10), -1):
            if words[i] and words[i][-1] in '.!?':
                truncated_text = ' '.join(words[:i+1])
                break
        else:
            # No sentence boundary found, just truncate and add ellipsis
            truncated_text = ' '.join(words[:max_words]) + '...'
    
    logger.warning(
        f"Truncated message from {word_count} words to {count_words(truncated_text)} words "
        f"(limit: {max_words})"
    )
    
    return truncated_text, True


def enforce_word_limit(text: str, max_words: int = MAX_WORDS_PER_MESSAGE) -> str:
    """
    Enforce word limit on text, truncating if necessary.
    
    WHAT: Simple wrapper for truncation
    WHY: Consistent word limit enforcement
    HOW: Call truncate_to_word_limit and return text
    
    Args:
        text: Input text
        max_words: Maximum words allowed
    
    Returns:
        Text truncated to word limit if needed
    """
    truncated, _ = truncate_to_word_limit(text, max_words)
    return truncated

