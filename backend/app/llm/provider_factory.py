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


def get_provider(fast_dev: bool = False) -> "LLMProvider":
    """
    Get the configured LLM provider singleton.
    
    Args:
        fast_dev: If True, use aggressive timeout/retry settings for faster iteration
    
    Returns:
        LLMProvider instance based on settings.LLM_PROVIDER
    
    Raises:
        ValueError: If provider name is unknown
    """
    global _provider_instance
    
    # In fast dev mode, don't use singleton (create new instance with fast settings)
    if fast_dev:
        from ..core.config import settings
        from ..utils.logger import get_logger
        
        logger = get_logger(__name__)
        provider_name = settings.LLM_PROVIDER
        
        if provider_name == "lm_studio":
            from .lm_studio import LMStudioProvider
            timeout = settings.LM_STUDIO_FAST_TIMEOUT or 12  # 12s is faster than 30s but gives LM Studio time to respond
            max_retries = settings.LLM_FAST_MAX_RETRIES or 1
            retry_delay = settings.LLM_FAST_RETRY_DELAY or 1
            logger.info(f"LLM provider initialized (FAST DEV): {provider_name}, timeout={timeout}s, retries={max_retries}")
            return LMStudioProvider(
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay
            )
        elif provider_name == "openrouter":
            from .openrouter import OpenRouterProvider
            logger.info(f"LLM provider initialized (FAST DEV): {provider_name}")
            return OpenRouterProvider()
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    # Normal mode: use singleton
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

