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
    
    def __init__(self):
        """Initialize LM Studio provider with httpx client."""
        self.base_url = settings.LM_STUDIO_BASE_URL
        self.default_model = settings.LM_STUDIO_DEFAULT_MODEL
        self.timeout = settings.LM_STUDIO_TIMEOUT
        self.max_retries = settings.LLM_MAX_RETRIES
        self.retry_delay = settings.LLM_RETRY_DELAY
        
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
        stop: list[str] | None = None,
        model: str | None = None
    ) -> LLMResult:
        """
        Generate complete response (non-streaming).
        
        Args:
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
            model: Optional model name (uses default_model if not provided)
        
        Returns:
            LLMResult with text, usage, and model
        
        Raises:
            ProviderTimeoutError: Request timed out
            ProviderUnavailableError: LM Studio not reachable
            ProviderResponseError: Invalid response from LM Studio
        """
        # Use provided model or fall back to default
        model_to_use = model or self.default_model
        logger.debug(f"Using model: {model_to_use} (requested: {model}, default: {self.default_model})")
        
        payload = {
            "model": model_to_use,
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
                response_model = data.get("model", model_to_use)
                
                logger.info(f"LM Studio generate success (model: {response_model}, tokens: {usage.get('total_tokens', 'unknown')})")
                
                return LLMResult(
                    text=text,
                    usage=usage,
                    model=response_model
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
        stop: list[str] | None = None,
        model: str | None = None
    ) -> AsyncIterator[TokenChunk]:
        """
        Stream response tokens as they're generated (unfiltered).
        
        Args:
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop: Optional stop sequences
            model: Optional model name (uses default_model if not provided)
        
        Yields:
            TokenChunk for each token (raw, unfiltered)
        
        Raises:
            ProviderTimeoutError: Request timed out
            ProviderUnavailableError: LM Studio not reachable
            ProviderResponseError: Invalid streaming response
        """
        # Use provided model or fall back to default
        model_to_use = model or self.default_model
        logger.debug(f"Streaming with model: {model_to_use} (requested: {model}, default: {self.default_model})")
        
        payload = {
            "model": model_to_use,
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
                            
                            # Ignore structured reasoning streams if present (future-proofing)
                            if delta.get("reasoning"):
                                continue
                            
                            token = delta.get("content", "")
                            if not token:
                                # Check for finish
                                finish_reason = data["choices"][0].get("finish_reason")
                                if finish_reason:
                                    yield TokenChunk(token="", index=index, is_end=True)
                                    break
                                continue
                            
                            # Emit raw token without filtering
                            yield TokenChunk(token=token, index=index, is_end=False)
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

