"""
Text processing utilities.

WHAT: Helper functions for cleaning and sanitizing text
WHY: Centralize common text operations (thinking token stripping moved to frontend)
HOW: Regex-based text processing utilities
"""

import re


def strip_thinking(text: str) -> str:
    """
    Remove reasoning/thinking segments from LLM output.
    
    NOTE: This function is now deprecated as thinking token stripping has been moved to the frontend.
    Backend providers now emit raw, unfiltered tokens to allow full responses to reach the client.
    The frontend handles thinking token removal via stripThinking() in utils/formatters.ts.
    
    This function is kept for backward compatibility and debugging purposes only.
    
    Args:
        text: Raw LLM output text
        
    Returns:
        Text unchanged (no longer strips thinking tokens)
    """
    # TODO: Remove this function entirely once confirmed no backend code depends on it
    from ..utils.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("strip_thinking() called but thinking token stripping is now handled by frontend only")
    
    return text  # Return text unchanged

