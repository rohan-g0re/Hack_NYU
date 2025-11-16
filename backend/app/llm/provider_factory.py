"""
LLM provider factory with singleton pattern.

WHAT: Factory to get the configured LLM provider
WHY: Centralize provider selection and avoid multiple instances
HOW: Read LLM_PROVIDER from config, cache singleton, log selection
"""

from typing import TYPE_CHECKING, Dict, Literal

if TYPE_CHECKING:
    from .provider import LLMProvider

# Cache for provider instances (provider_name -> instance)
_provider_cache: Dict[str, "LLMProvider"] = {}


def get_provider(provider_name: str | None = None) -> "LLMProvider":
    """
    Get the LLM provider by name or use the default from settings.
    
    Args:
        provider_name: Optional provider name ('lm_studio' or 'openrouter'). 
                      If None, uses settings.LLM_PROVIDER
    
    Returns:
        LLMProvider instance
    
    Raises:
        ValueError: If provider name is unknown
    """
    # Import here to avoid circular dependencies
    from ..core.config import settings
    from ..utils.logger import get_logger
    
    logger = get_logger(__name__)
    
    # Use default provider if not specified
    if provider_name is None:
        provider_name = settings.LLM_PROVIDER
    
    # Return cached instance if available
    if provider_name in _provider_cache:
        return _provider_cache[provider_name]
    
    # Create new provider instance
    if provider_name == "lm_studio":
        from .lm_studio import LMStudioProvider
        provider = LMStudioProvider()
    elif provider_name == "openrouter":
        from .openrouter import OpenRouterProvider
        provider = OpenRouterProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    # Cache the instance
    _provider_cache[provider_name] = provider
    logger.info(f"LLM provider initialized: {provider_name}")
    
    return provider


def reset_provider() -> None:
    """Reset all provider instances (useful for testing)."""
    global _provider_cache
    _provider_cache = {}

