"""
Mock LLM provider for deterministic testing.

WHAT: Fake LLM provider that returns scripted responses
WHY: Test agents without real LLM dependency
HOW: Implement LLMProvider protocol with canned responses
"""

from typing import AsyncIterator, Dict, List
from app.llm.types import ChatMessage, LLMResult, TokenChunk, ProviderStatus


class MockLLMProvider:
    """
    Mock LLM provider for testing with scripted responses.
    
    Can be configured to return specific responses or raise errors.
    """
    
    def __init__(self, responses: List[str] | None = None, should_fail: bool = False):
        """
        Initialize mock provider.
        
        Args:
            responses: List of canned responses (cycled through)
            should_fail: If True, raise errors instead of responding
        """
        self.responses = responses or ["Mock response"]
        self.should_fail = should_fail
        self.call_count = 0
        self.calls: List[Dict] = []
    
    async def ping(self) -> ProviderStatus:
        """Mock ping."""
        return ProviderStatus(
            available=not self.should_fail,
            base_url="http://mock:1234/v1",
            models=["mock-model"] if not self.should_fail else None,
            error="Mock failure" if self.should_fail else None
        )
    
    async def generate(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: List[str] | None = None
    ) -> LLMResult:
        """Mock generate."""
        if self.should_fail:
            from app.llm.types import ProviderResponseError
            raise ProviderResponseError("Mock provider error")
        
        # Record call
        self.calls.append({
            "method": "generate",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop
        })
        
        # Return scripted response
        response_idx = self.call_count % len(self.responses)
        response_text = self.responses[response_idx]
        self.call_count += 1
        
        return LLMResult(
            text=response_text,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            model="mock-model"
        )
    
    async def stream(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: List[str] | None = None
    ) -> AsyncIterator[TokenChunk]:
        """Mock stream."""
        if self.should_fail:
            from app.llm.types import ProviderResponseError
            raise ProviderResponseError("Mock provider error")
        
        # Record call
        self.calls.append({
            "method": "stream",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop
        })
        
        # Return scripted response as chunks
        response_idx = self.call_count % len(self.responses)
        response_text = self.responses[response_idx]
        self.call_count += 1
        
        # Split into words and yield as chunks
        words = response_text.split()
        for idx, word in enumerate(words):
            yield TokenChunk(token=word + " ", index=idx, is_end=False)
        
        yield TokenChunk(token="", index=len(words), is_end=True)
