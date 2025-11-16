"""
LLM provider protocol definition.

WHAT: Abstract interface for LLM providers
WHY: Decouple calling code from specific provider implementations
HOW: Use Protocol to define async methods for ping, generate, and stream
"""

from typing import Protocol, AsyncIterator
from .types import ChatMessage, LLMResult, TokenChunk, ProviderStatus


class LLMProvider(Protocol):
    """Protocol defining the interface all LLM providers must implement."""
    
    async def ping(self) -> ProviderStatus:
        """Check provider health and availability."""
        ...
    
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: list[str] | None = None,
        model: str | None = None
    ) -> LLMResult:
        """Generate a complete response (non-streaming)."""
        ...
    
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: list[str] | None = None,
        model: str | None = None
    ) -> AsyncIterator[TokenChunk]:
        """Stream response tokens as they're generated."""
        ...

