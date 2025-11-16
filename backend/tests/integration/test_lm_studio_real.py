"""
Integration tests with real LM Studio instance (optional).

WHAT: Test actual LM Studio connection when available
WHY: Verify provider works with real LM Studio server
HOW: Attempt connection to localhost:1234, skip if not available
"""

import pytest
import httpx
from unittest.mock import patch

from app.llm.lm_studio import LMStudioProvider
from app.llm.types import ProviderStatus, LLMResult


# Check if LM Studio is available
async def check_lm_studio_available():
    """Check if LM Studio is running on localhost:1234."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:1234/v1/models", timeout=2.0)
            return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
async def provider():
    """Create LM Studio provider for real testing."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
        mock_settings.LM_STUDIO_DEFAULT_MODEL = "llama-3-8b-instruct"
        mock_settings.LM_STUDIO_TIMEOUT = 30
        mock_settings.LLM_MAX_RETRIES = 3
        mock_settings.LLM_RETRY_DELAY = 2
        provider = LMStudioProvider()
    yield provider
    await provider.close()


@pytest.mark.phase1
@pytest.mark.integration
@pytest.mark.requires_lm_studio
@pytest.mark.slow
class TestRealLMStudio:
    """Integration tests with real LM Studio instance."""
    
    @pytest.mark.asyncio
    async def test_ping_real_lm_studio(self, provider):
        """Test ping with real LM Studio instance."""
        # Skip if LM Studio not available
        available = await check_lm_studio_available()
        if not available:
            pytest.skip("LM Studio not running on localhost:1234")
        
        status = await provider.ping()
        
        assert isinstance(status, ProviderStatus)
        assert status.available is True
        assert status.base_url == "http://127.0.0.1:1234/v1"
        assert status.models is not None
        assert isinstance(status.models, list)
        assert len(status.models) > 0
        print(f"Available models: {status.models}")
    
    @pytest.mark.asyncio
    async def test_generate_real_lm_studio(self, provider):
        """Test generation with real LM Studio instance."""
        # Skip if LM Studio not available
        available = await check_lm_studio_available()
        if not available:
            pytest.skip("LM Studio not running on localhost:1234")
        
        result = await provider.generate(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello' and nothing else."}
            ],
            temperature=0.3,
            max_tokens=10
        )
        
        assert isinstance(result, LLMResult)
        assert isinstance(result.text, str)
        assert len(result.text) > 0
        assert "hello" in result.text.lower()
        assert isinstance(result.usage, dict)
        assert "total_tokens" in result.usage or "completion_tokens" in result.usage
        print(f"Generated text: {result.text}")
        print(f"Usage: {result.usage}")
    
    @pytest.mark.asyncio
    async def test_stream_real_lm_studio(self, provider):
        """Test streaming with real LM Studio instance."""
        # Skip if LM Studio not available
        available = await check_lm_studio_available()
        if not available:
            pytest.skip("LM Studio not running on localhost:1234")
        
        chunks = []
        async for chunk in provider.stream(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count to 3."}
            ],
            temperature=0.3,
            max_tokens=20
        ):
            chunks.append(chunk)
            if chunk.is_end:
                break
        
        assert len(chunks) > 0
        
        # Collect text from chunks
        text_chunks = [c.token for c in chunks if c.token and not c.is_end]
        full_text = "".join(text_chunks)
        
        assert len(full_text) > 0
        print(f"Streamed text: {full_text}")
        print(f"Total chunks: {len(chunks)}")
        
        # Should have at least one end marker
        end_chunks = [c for c in chunks if c.is_end]
        assert len(end_chunks) > 0
    
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider):
        """Test generation with system prompt."""
        # Skip if LM Studio not available
        available = await check_lm_studio_available()
        if not available:
            pytest.skip("LM Studio not running on localhost:1234")
        
        result = await provider.generate(
            messages=[
                {"role": "system", "content": "You are a pirate. Speak like one."},
                {"role": "user", "content": "How are you?"}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        assert isinstance(result.text, str)
        assert len(result.text) > 0
        print(f"Pirate response: {result.text}")


@pytest.mark.phase1
@pytest.mark.integration
@pytest.mark.requires_lm_studio
class TestLMStudioErrorHandling:
    """Test error handling with LM Studio."""
    
    @pytest.mark.asyncio
    async def test_ping_wrong_port(self):
        """Test ping with wrong port fails gracefully."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LM_STUDIO_BASE_URL = "http://localhost:9999/v1"
            mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
            mock_settings.LM_STUDIO_TIMEOUT = 5
            mock_settings.LLM_MAX_RETRIES = 1
            mock_settings.LLM_RETRY_DELAY = 0.1
            provider = LMStudioProvider()
        
        status = await provider.ping()
        
        assert status.available is False
        assert status.error is not None
        assert "refused" in status.error.lower() or "timeout" in status.error.lower()
        
        await provider.close()
    
    @pytest.mark.asyncio
    async def test_generate_wrong_endpoint(self):
        """Test generation with unreachable endpoint."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.LM_STUDIO_BASE_URL = "http://localhost:9999/v1"
            mock_settings.LM_STUDIO_DEFAULT_MODEL = "test-model"
            mock_settings.LM_STUDIO_TIMEOUT = 5
            mock_settings.LLM_MAX_RETRIES = 1
            mock_settings.LLM_RETRY_DELAY = 0.1
            provider = LMStudioProvider()
        
        from app.llm.types import ProviderUnavailableError
        
        with pytest.raises(ProviderUnavailableError):
            await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                temperature=0.7,
                max_tokens=100
            )
        
        await provider.close()

