"""
LLM provider types, dataclasses, and exceptions.

WHAT: Standard type definitions for LLM interactions
WHY: Ensure consistent contracts across all providers
HOW: TypedDict for messages, dataclasses for results/status, custom exceptions for errors
"""

from typing import TypedDict, Literal
from dataclasses import dataclass


# Message format compatible with OpenAI-style APIs
ChatMessage = TypedDict(
    "ChatMessage",
    {"role": Literal["system", "user", "assistant"], "content": str}
)


@dataclass
class TokenChunk:
    """Individual token from a streaming response."""
    token: str
    index: int
    is_end: bool = False


@dataclass
class LLMResult:
    """Complete LLM generation result."""
    text: str
    usage: dict
    model: str


@dataclass
class ProviderStatus:
    """Health status of an LLM provider."""
    available: bool
    base_url: str
    models: list[str] | None = None
    error: str | None = None


# Provider exceptions
class ProviderTimeoutError(Exception):
    """Request to provider timed out."""
    pass


class ProviderUnavailableError(Exception):
    """Provider is not reachable or down."""
    pass


class ProviderDisabledError(Exception):
    """Provider is disabled in configuration."""
    pass


class ProviderResponseError(Exception):
    """Provider returned an invalid or error response."""
    pass

