"""
LLM provider factory with singleton pattern.

WHAT: Factory to get the configured LLM provider
WHY: Centralize provider selection and avoid multiple instances
HOW: Read LLM_PROVIDER from config, cache singleton, log selection
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .provider import LLMProvider

# Singleton instance
_provider_instance: "LLMProvider | None" = None


def get_provider() -> "LLMProvider":
    """
    Get the configured LLM provider singleton.
    
    Returns:
        LLMProvider instance based on settings.LLM_PROVIDER
    
    Raises:
        ValueError: If provider name is unknown
    """
    global _provider_instance
    
    if _provider_instance is None:
        # Import here to avoid circular dependencies
        from ..core.config import settings
        from ..utils.logger import get_logger
        
        logger = get_logger(__name__)
        provider_name = settings.LLM_PROVIDER
        
        if provider_name == "lm_studio":
            from .lm_studio import LMStudioProvider
            _provider_instance = LMStudioProvider()
        elif provider_name == "openrouter":
            from .openrouter import OpenRouterProvider
            _provider_instance = OpenRouterProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        
        logger.info(f"LLM provider initialized: {provider_name}")
    
    return _provider_instance


def reset_provider() -> None:
    """Reset the provider singleton (useful for testing)."""
    global _provider_instance
    _provider_instance = None

