"""
LM Studio provider implementation.

WHAT: Local LLM inference via LM Studio with streaming support
WHY: Enable local-first inference without external API dependencies
HOW: HTTPX client with retries, SSE parsing, OpenAI-compatible API
"""

import httpx
import json
import asyncio
from typing import AsyncIterator

from .types import (
    ChatMessage,
    LLMResult,
    TokenChunk,
    ProviderStatus,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderResponseError,
)
from ..core.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LMStudioProvider:
    """LM Studio LLM provider with retry logic and streaming."""
    
    def __init__(
        self,
        *,
        timeout: int | None = None,
        max_retries: int | None = None,
        retry_delay: int | None = None,
    ):
        """
        Initialize LM Studio provider with httpx client.
        
        Args:
            timeout: Override timeout (seconds). If None, uses settings.LM_STUDIO_TIMEOUT
            max_retries: Override max retries. If None, uses settings.LLM_MAX_RETRIES
            retry_delay: Override retry delay (seconds). If None, uses settings.LLM_RETRY_DELAY
        """
        self.base_url = settings.LM_STUDIO_BASE_URL
        self.default_model = settings.LM_STUDIO_DEFAULT_MODEL
        self.timeout = timeout if timeout is not None else settings.LM_STUDIO_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES
        self.retry_delay = retry_delay if retry_delay is not None else settings.LLM_RETRY_DELAY
        
        # Create async client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, read=self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            ),
            http2=False  # Windows ARM compatibility
        )
    
    async def ping(self) -> ProviderStatus:
        """
        Check LM Studio availability.
        
        Returns:
            ProviderStatus with availability and model list
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/models",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            models = [m.get("id") for m in data.get("data", [])]
            
            return ProviderStatus(
                available=True,
                base_url=self.base_url,
                models=models if models else None
            )
        except httpx.TimeoutException:
            logger.warning("LM Studio ping timed out")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                error="Connection timeout"
            )
        except httpx.ConnectError:
            logger.warning("LM Studio not reachable")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                error="Connection refused - is LM Studio running?"
            )
        except Exception as e:
            logger.error(f"LM Studio ping failed: {e}")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                error=str(e)
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
        Generate complete response (non-streaming).
        
        Args:
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
        
        Returns:
            LLMResult with text, usage, and model
        
        Raises:
            ProviderTimeoutError: Request timed out
            ProviderUnavailableError: LM Studio not reachable
            ProviderResponseError: Invalid response from LM Studio
        """
        payload = {
            "model": self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        if stop:
            payload["stop"] = stop
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract response
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                model = data.get("model", self.default_model)
                
                logger.info(f"LM Studio generate success (tokens: {usage.get('total_tokens', 'unknown')})")
                
                return LLMResult(
                    text=text,
                    usage=usage,
                    model=model
                )
                
            except httpx.TimeoutException as e:
                logger.warning(f"LM Studio timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise ProviderTimeoutError(f"Request timed out after {self.max_retries} attempts") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except httpx.ConnectError as e:
                logger.error(f"LM Studio connection refused (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise ProviderUnavailableError("LM Studio is not reachable") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.error(f"LM Studio server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries})")
                    if attempt == self.max_retries - 1:
                        raise ProviderResponseError(f"Server error: {e.response.status_code}") from e
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    # Client errors don't retry
                    raise ProviderResponseError(f"HTTP {e.response.status_code}: {e.response.text}") from e
                    
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Invalid response from LM Studio: {e}")
                raise ProviderResponseError(f"Invalid response format: {e}") from e
    
    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float,
        max_tokens: int,
        stop: list[str] | None = None
    ) -> AsyncIterator[TokenChunk]:
        """
        Stream response tokens as they're generated.
        
        Args:
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
        
        Yields:
            TokenChunk for each token
        
        Raises:
            ProviderTimeoutError: Request timed out
            ProviderUnavailableError: LM Studio not reachable
            ProviderResponseError: Invalid streaming response
        """
        payload = {
            "model": self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        if stop:
            payload["stop"] = stop
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                
                index = 0
                async for line in response.aiter_lines():
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # SSE format: "data: {json}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        # Check for end signal
                        if data_str == "[DONE]":
                            yield TokenChunk(token="", index=index, is_end=True)
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield TokenChunk(token=content, index=index, is_end=False)
                                index += 1
                            
                            # Check if this is the last chunk
                            finish_reason = data["choices"][0].get("finish_reason")
                            if finish_reason:
                                yield TokenChunk(token="", index=index, is_end=True)
                                break
                                
                        except (KeyError, json.JSONDecodeError) as e:
                            logger.error(f"Invalid SSE chunk: {line[:100]}")
                            raise ProviderResponseError(f"Invalid streaming chunk: {e}") from e
                
                logger.info(f"LM Studio stream completed ({index} chunks)")
                
        except httpx.TimeoutException as e:
            logger.error("LM Studio streaming timeout")
            raise ProviderTimeoutError("Streaming request timed out") from e
            
        except httpx.ConnectError as e:
            logger.error("LM Studio connection refused during streaming")
            raise ProviderUnavailableError("LM Studio is not reachable") from e
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LM Studio streaming HTTP error: {e.response.status_code}")
            raise ProviderResponseError(f"HTTP {e.response.status_code}") from e
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

