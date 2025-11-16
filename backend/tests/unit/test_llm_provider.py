"""
Unit tests for LLM provider factory and implementations.

WHAT: Test provider selection, LM Studio operations, error handling
WHY: Ensure provider layer works correctly before integration
HOW: Mock HTTP with respx, test success and failure paths
"""

import pytest
import respx
import httpx
import json
from unittest.mock import patch

from app.llm.provider_factory import get_provider, reset_provider
from app.llm.lm_studio import LMStudioProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.types import (
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderDisabledError,
    ProviderResponseError,
)


@pytest.mark.phase1
@pytest.mark.unit
class TestProviderFactory:
    """Test provider factory selection logic."""
    
    @patch("app.core.config.settings")
    def test_factory_returns_lm_studio(self, mock_settings):
        """Test factory returns LM Studio provider when configured."""
        mock_settings.LLM_PROVIDER = "lm_studio"
        mock_settings.LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
        mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
        mock_settings.LM_STUDIO_TIMEOUT = 30
        mock_settings.LLM_MAX_RETRIES = 3
        mock_settings.LLM_RETRY_DELAY = 2
        
        provider = get_provider()
        assert isinstance(provider, LMStudioProvider)
    
    @patch("app.core.config.settings")
    def test_factory_returns_openrouter(self, mock_settings):
        """Test factory returns OpenRouter provider when configured."""
        mock_settings.LLM_PROVIDER = "openrouter"
        mock_settings.LLM_ENABLE_OPENROUTER = True
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        mock_settings.APP_NAME = "Test App"
        
        provider = get_provider()
        assert isinstance(provider, OpenRouterProvider)
    
    @patch("app.core.config.settings")
    def test_factory_raises_on_unknown_provider(self, mock_settings):
        """Test factory raises ValueError for unknown provider."""
        mock_settings.LLM_PROVIDER = "unknown_provider"
        
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_provider()
    
    @patch("app.core.config.settings")
    def test_factory_returns_singleton(self, mock_settings):
        """Test factory returns same instance on repeated calls."""
        mock_settings.LLM_PROVIDER = "lm_studio"
        mock_settings.LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
        mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
        mock_settings.LM_STUDIO_TIMEOUT = 30
        mock_settings.LLM_MAX_RETRIES = 3
        mock_settings.LLM_RETRY_DELAY = 2
        
        provider1 = get_provider()
        provider2 = get_provider()
        assert provider1 is provider2


@pytest.mark.phase1
@pytest.mark.unit
class TestLMStudioProvider:
    """Test LM Studio provider implementation."""
    
    @pytest.fixture
    def provider(self):
        """Create LM Studio provider with test config."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
            mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
            mock_settings.LM_STUDIO_TIMEOUT = 30
            mock_settings.LLM_MAX_RETRIES = 3
            mock_settings.LLM_RETRY_DELAY = 0.1  # Fast retries for tests
            provider = LMStudioProvider()
        return provider
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_ping_success(self, provider):
        """Test successful ping returns available status."""
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": "model-1"}, {"id": "model-2"}]}
            )
        )
        
        status = await provider.ping()
        assert status.available is True
        assert status.models == ["model-1", "model-2"]
        assert status.error is None
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_ping_timeout(self, provider):
        """Test ping timeout returns unavailable status."""
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        status = await provider.ping()
        assert status.available is False
        assert "timeout" in status.error.lower()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_ping_connection_refused(self, provider):
        """Test ping connection refused returns unavailable status."""
        respx.get("http://localhost:1234/v1/models").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        status = await provider.ping()
        assert status.available is False
        assert "refused" in status.error.lower()
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_success(self, provider):
        """Test successful generation."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Hello, world!"}}],
                    "usage": {"total_tokens": 10},
                    "model": "test-model"
                }
            )
        )
        
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        )
        
        assert result.text == "Hello, world!"
        assert result.usage["total_tokens"] == 10
        assert result.model == "test-model"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_timeout_raises(self, provider):
        """Test generation timeout raises ProviderTimeoutError."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        with pytest.raises(ProviderTimeoutError):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_connection_error_raises(self, provider):
        """Test generation connection error raises ProviderUnavailableError."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        
        with pytest.raises(ProviderUnavailableError):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_500_error_retries(self, provider):
        """Test generation retries on 500 errors."""
        # Mock 500 twice, then success
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(500, text="Server error"),
                httpx.Response(500, text="Server error"),
                httpx.Response(
                    200,
                    json={
                        "choices": [{"message": {"content": "Success"}}],
                        "usage": {"total_tokens": 5},
                        "model": "test-model"
                    }
                )
            ]
        )
        
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        )
        
        assert result.text == "Success"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_invalid_json_raises(self, provider):
        """Test generation with invalid JSON raises ProviderResponseError."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(200, json={"invalid": "structure"})
        )
        
        with pytest.raises(ProviderResponseError):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_success(self, provider):
        """Test successful streaming."""
        # Mock SSE stream
        sse_data = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
        ]
        
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(200, text="".join(sse_data))
        )
        
        chunks = []
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        ):
            chunks.append(chunk)
        
        assert len(chunks) >= 2
        assert chunks[0].token == "Hello"
        assert chunks[1].token == " world"
        assert chunks[-1].is_end is True


@pytest.mark.phase1
@pytest.mark.unit
class TestOpenRouterProvider:
    """Test OpenRouter provider stub."""
    
    @pytest.fixture
    def disabled_provider(self):
        """Create disabled OpenRouter provider."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LLM_ENABLE_OPENROUTER = False
            mock_settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            mock_settings.OPENROUTER_API_KEY = ""
            mock_settings.APP_NAME = "Test App"
            provider = OpenRouterProvider()
        return provider
    
    @pytest.mark.asyncio
    async def test_disabled_provider_ping_raises(self, disabled_provider):
        """Test disabled provider raises ProviderDisabledError on ping."""
        with pytest.raises(ProviderDisabledError, match="disabled"):
            await disabled_provider.ping()
    
    @pytest.mark.asyncio
    async def test_disabled_provider_generate_raises(self, disabled_provider):
        """Test disabled provider raises ProviderDisabledError on generate."""
        with pytest.raises(ProviderDisabledError, match="disabled"):
            await disabled_provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    async def test_disabled_provider_stream_raises(self, disabled_provider):
        """Test disabled provider raises ProviderDisabledError on stream."""
        with pytest.raises(ProviderDisabledError, match="disabled"):
            async for _ in disabled_provider.stream(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            ):
                pass


@pytest.mark.phase1
@pytest.mark.unit
class TestLMStudioProviderEdgeCases:
    """Additional edge case tests for LM Studio provider."""
    
    @pytest.fixture
    def provider(self):
        """Create LM Studio provider with test config."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
            mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
            mock_settings.LM_STUDIO_TIMEOUT = 30
            mock_settings.LLM_MAX_RETRIES = 3
            mock_settings.LLM_RETRY_DELAY = 0.1
            provider = LMStudioProvider()
        return provider
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_with_stop_sequences(self, provider):
        """Test generation with stop sequences."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Hello"}}],
                    "usage": {"total_tokens": 5},
                    "model": "test-model"
                }
            )
        )
        
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100,
            stop=["\n", "END"]
        )
        
        assert result.text == "Hello"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_400_error_no_retry(self, provider):
        """Test generation with 400 error doesn't retry."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(400, json={"error": "Bad request"})
        )
        
        with pytest.raises(ProviderResponseError, match="400"):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_exhausts_retries(self, provider):
        """Test generation that exhausts all retries."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            side_effect=httpx.Response(500, text="Server error")
        )
        
        with pytest.raises(ProviderResponseError, match="500"):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_with_done_signal(self, provider):
        """Test streaming with [DONE] signal."""
        sse_data = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            'data: [DONE]\n',
        ]
        
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(200, text="".join(sse_data))
        )
        
        chunks = []
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 2
        assert chunks[0].token == "Hello"
        assert chunks[1].is_end is True
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_invalid_chunk_raises(self, provider):
        """Test streaming with invalid JSON chunk raises error."""
        sse_data = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            'data: {invalid json}\n',
        ]
        
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(200, text="".join(sse_data))
        )
        
        with pytest.raises(ProviderResponseError, match="Invalid streaming chunk"):
            chunks = []
            async for chunk in provider.stream(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            ):
                chunks.append(chunk)
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_empty_content(self, provider):
        """Test streaming with empty content chunks."""
        sse_data = [
            'data: {"choices":[{"delta":{}}]}\n',  # Empty delta
            'data: {"choices":[{"delta":{"content":""}}]}\n',  # Empty content
            'data: {"choices":[{"delta":{"content":"Hi"}}]}\n',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
        ]
        
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(200, text="".join(sse_data))
        )
        
        chunks = []
        async for chunk in provider.stream(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        ):
            if chunk.token:  # Only collect non-empty tokens
                chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0].token == "Hi"
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_timeout_raises(self, provider):
        """Test streaming timeout raises ProviderTimeoutError."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        
        with pytest.raises(ProviderTimeoutError):
            async for _ in provider.stream(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            ):
                pass
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_stream_http_error_raises(self, provider):
        """Test streaming HTTP error raises ProviderResponseError."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(503, text="Service unavailable")
        )
        
        with pytest.raises(ProviderResponseError, match="503"):
            async for _ in provider.stream(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            ):
                pass
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_ping_empty_models_list(self, provider):
        """Test ping with empty models list."""
        respx.get("http://localhost:1234/v1/models").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        
        status = await provider.ping()
        assert status.available is True
        assert status.models is None  # Empty list converted to None
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_missing_usage_field(self, provider):
        """Test generation with missing usage field."""
        respx.post("http://localhost:1234/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "Hello"}}],
                    "model": "test-model"
                }
            )
        )
        
        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.7,
            max_tokens=100
        )
        
        assert result.text == "Hello"
        assert result.usage == {}  # Empty dict when missing

