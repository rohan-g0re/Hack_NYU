"""
OpenRouter provider implementation.

WHAT: External LLM provider via OpenRouter API
WHY: Cloud-based models when local inference insufficient
HOW: OpenAI-compatible API with authorization headers, retry logic, SSE streaming
"""

import asyncio
import httpx
import json
from typing import AsyncIterator

from .types import (
    ChatMessage,
    LLMResult,
    TokenChunk,
    ProviderStatus,
    ProviderDisabledError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderResponseError,
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
        self.default_model = settings.OPENROUTER_DEFAULT_MODEL
        self.max_retries = settings.LLM_MAX_RETRIES
        self.retry_delay = settings.LLM_RETRY_DELAY
        
        if self.enabled:
            # Validate API key is set and not empty
            if not self.api_key or not self.api_key.strip():
                logger.error("OpenRouter enabled but OPENROUTER_API_KEY is not set or empty!")
                raise ProviderDisabledError(
                    "OpenRouter is enabled but OPENROUTER_API_KEY is not set or empty. "
                    "Please set OPENROUTER_API_KEY in your .env file with a valid API key from https://openrouter.ai/keys"
                )
            
            # Create HTTP client with API key
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, read=60.0),  # Longer timeout for cloud API
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": settings.APP_NAME,
                    "X-Title": settings.APP_NAME,
                },
                http2=False  # Windows ARM compatibility
            )
            logger.info(f"OpenRouter provider initialized (enabled, model: {self.default_model}, API key: {'*' * 10 + self.api_key[-4:] if len(self.api_key) > 4 else '***'})")
        else:
            logger.info("OpenRouter provider initialized (disabled)")
    
    def _check_enabled(self):
        """Raise exception if provider is disabled."""
        if not self.enabled:
            raise ProviderDisabledError("OpenRouter provider is disabled. Set LLM_ENABLE_OPENROUTER=true to enable.")
    
    async def ping(self) -> ProviderStatus:
        """
        Check OpenRouter availability by fetching models list.
        
        Returns:
            ProviderStatus with available models
        
        Raises:
            ProviderDisabledError: If OpenRouter is disabled
        """
        self._check_enabled()
        
        try:
            response = await self.client.get(f"{self.base_url}/models", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Extract model IDs
            models = [model.get("id") for model in data.get("data", [])]
            
            logger.info(f"OpenRouter ping success ({len(models)} models available)")
            
            return ProviderStatus(
                available=True,
                base_url=self.base_url,
                models=models[:10] if models else None,  # Return first 10
                error=None
            )
        except httpx.TimeoutException:
            logger.warning("OpenRouter ping timeout")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                models=None,
                error="Request timed out"
            )
        except httpx.ConnectError:
            logger.warning("OpenRouter not reachable")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                models=None,
                error="Connection refused"
            )
        except Exception as e:
            logger.error(f"OpenRouter ping failed: {e}")
            return ProviderStatus(
                available=False,
                base_url=self.base_url,
                models=None,
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
            ProviderUnavailableError: OpenRouter not reachable
            ProviderResponseError: Invalid response from OpenRouter
        """
        self._check_enabled()
        
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
                
                logger.info(f"OpenRouter generate success (model: {response_model}, tokens: {usage.get('total_tokens', 'unknown')})")
                
                return LLMResult(
                    text=text,
                    usage=usage,
                    model=response_model
                )
                
            except httpx.TimeoutException as e:
                logger.warning(f"OpenRouter timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise ProviderTimeoutError(f"Request timed out after {self.max_retries} attempts") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except httpx.ConnectError as e:
                logger.error(f"OpenRouter connection refused (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    raise ProviderUnavailableError("OpenRouter is not reachable") from e
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.error(f"OpenRouter server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries})")
                    if attempt == self.max_retries - 1:
                        raise ProviderResponseError(f"Server error: {e.response.status_code}") from e
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    # Client errors don't retry
                    raise ProviderResponseError(f"HTTP {e.response.status_code}: {e.response.text}") from e
                    
            except (KeyError, json.JSONDecodeError) as e:
                logger.error(f"Invalid response from OpenRouter: {e}")
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
            ProviderUnavailableError: OpenRouter not reachable
            ProviderResponseError: Invalid streaming response
        """
        self._check_enabled()
        
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
                
                logger.info(f"OpenRouter stream completed ({index} chunks)")
                
        except httpx.TimeoutException as e:
            logger.error("OpenRouter streaming timeout")
            raise ProviderTimeoutError("Streaming request timed out") from e
            
        except httpx.ConnectError as e:
            logger.error("OpenRouter connection refused during streaming")
            raise ProviderUnavailableError("OpenRouter is not reachable") from e
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter streaming HTTP error: {e.response.status_code}")
            raise ProviderResponseError(f"HTTP {e.response.status_code}: {e.response.text}") from e
    
    async def close(self):
        """Close the HTTP client if enabled."""
        if self.enabled:
            await self.client.aclose()

