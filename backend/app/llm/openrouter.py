"""
OpenRouter provider stub.

WHAT: External LLM provider via OpenRouter API (currently disabled by default)
WHY: Future support for cloud-based models when local inference insufficient
HOW: OpenAI-compatible API with authorization headers, disabled unless explicitly enabled
"""

import httpx
from typing import AsyncIterator

from .types import (
    ChatMessage,
    LLMResult,
    TokenChunk,
    ProviderStatus,
    ProviderDisabledError,
)
from ..core.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterProvider:
    """OpenRouter LLM provider (stub - disabled by default)."""
    
    def __init__(self):
        """Initialize OpenRouter provider (checks if enabled)."""
        self.enabled = settings.LLM_ENABLE_OPENROUTER
        self.base_url = settings.OPENROUTER_BASE_URL
        self.api_key = settings.OPENROUTER_API_KEY
        
        if self.enabled and not self.api_key:
            logger.warning("OpenRouter enabled but OPENROUTER_API_KEY not set")
        
        if self.enabled:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, read=30.0),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": settings.APP_NAME,
                    "X-Title": settings.APP_NAME,
                }
            )
            logger.info("OpenRouter provider initialized (enabled)")
        else:
            logger.info("OpenRouter provider initialized (disabled)")
    
    def _check_enabled(self):
        """Raise exception if provider is disabled."""
        if not self.enabled:
            raise ProviderDisabledError("OpenRouter provider is disabled. Set LLM_ENABLE_OPENROUTER=true to enable.")
    
    async def ping(self) -> ProviderStatus:
        """
        Check OpenRouter availability.
        
        Returns:
            ProviderStatus
        
        Raises:
            ProviderDisabledError: If OpenRouter is disabled
        """
        self._check_enabled()
        
        # Stub implementation - would check API status
        return ProviderStatus(
            available=True,
            base_url=self.base_url,
            models=None,
            error=None
        )
    
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: list[str] | None = None
    ) -> LLMResult:
        """
        Generate complete response (stub).
        
        Raises:
            ProviderDisabledError: If OpenRouter is disabled
        """
        self._check_enabled()
        
        # Stub - actual implementation would call OpenRouter API
        raise NotImplementedError("OpenRouter generation not yet implemented")
    
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: list[str] | None = None
    ) -> AsyncIterator[TokenChunk]:
        """
        Stream response tokens (stub).
        
        Raises:
            ProviderDisabledError: If OpenRouter is disabled
        """
        self._check_enabled()
        
        # Stub - actual implementation would stream from OpenRouter API
        raise NotImplementedError("OpenRouter streaming not yet implemented")
        # Make this a proper async generator
        yield  # pragma: no cover
    
    async def close(self):
        """Close the HTTP client if enabled."""
        if self.enabled:
            await self.client.aclose()

