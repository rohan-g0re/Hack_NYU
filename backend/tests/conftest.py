"""
Pytest configuration and shared fixtures for backend tests.

WHAT: Centralized test configuration with phase markers
WHY: Enable test organization, filtering, and shared test utilities
HOW: Define pytest markers, fixtures, and test helpers
"""

import pytest
import asyncio
import os
import httpx
from typing import AsyncIterator
from unittest.mock import patch

from app.llm.provider_factory import reset_provider
from app.core.config import settings


def pytest_configure(config):
    """Register custom markers for test phases."""
    config.addinivalue_line(
        "markers", "phase1: Phase 1 tests (Inference Setup - LM Studio + OpenRouter Stub)"
    )
    config.addinivalue_line(
        "markers", "phase2: Phase 2 tests (Complete Agent Logic - Buyer/Seller + Graph)"
    )
    config.addinivalue_line(
        "markers", "phase3: Phase 3 tests (Database & Orchestration - Sessions, Runs, State)"
    )
    config.addinivalue_line(
        "markers", "phase4: Phase 4 tests (FastAPI Endpoints & SSE)"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests (isolated component tests)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (multiple components)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (full system)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take significant time to run"
    )
    config.addinivalue_line(
        "markers", "requires_lm_studio: Tests that require running LM Studio instance"
    )
    config.addinivalue_line(
        "markers", "requires_openrouter: Tests that require OpenRouter API key and enabled provider"
    )
    config.addinivalue_line(
        "markers", "perf: Performance tests that measure latency and throughput"
    )


@pytest.fixture(autouse=True)
def reset_provider_singleton():
    """
    Reset provider singleton before each test.
    
    WHAT: Clear provider cache between tests
    WHY: Prevent test pollution and ensure clean state
    HOW: Call reset_provider() before and after each test
    """
    reset_provider()
    yield
    reset_provider()


@pytest.fixture
def mock_settings():
    """
    Mock application settings for tests.
    
    WHAT: Provide consistent test configuration
    WHY: Isolate tests from environment variables
    HOW: Patch settings with test-friendly values
    """
    with patch("app.core.config.settings") as mock:
        mock.APP_NAME = "Test App"
        mock.APP_VERSION = "0.1.0"
        mock.DEBUG = True
        mock.DATABASE_URL = "sqlite:///./test.db"
        mock.LLM_PROVIDER = "lm_studio"
        mock.LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
        mock.LM_STUDIO_DEFAULT_MODEL = "test-model"
        mock.LM_STUDIO_TIMEOUT = 30
        mock.LLM_MAX_RETRIES = 3
        mock.LLM_RETRY_DELAY = 0.1  # Fast retries for tests
        mock.LLM_ENABLE_OPENROUTER = False
        mock.OPENROUTER_API_KEY = ""
        mock.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
        mock.CORS_ORIGINS = ["http://localhost:3000"]
        mock.LOG_LEVEL = "DEBUG"
        mock.LOG_FILE = "./test_logs/app.log"
        yield mock


@pytest.fixture
def event_loop():
    """
    Create an event loop for async tests.
    
    WHAT: Provide event loop for pytest-asyncio
    WHY: Enable proper async test execution
    HOW: Create and cleanup loop per test
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_token_chunks() -> AsyncIterator:
    """
    Generate mock token chunks for streaming tests.
    
    WHAT: Produce sample TokenChunk stream
    WHY: Test streaming handlers without real LLM
    HOW: Yield predefined chunks with end marker
    """
    from app.llm.types import TokenChunk
    
    async def chunk_generator():
        chunks = [
            TokenChunk(token="Hello", index=0, is_end=False),
            TokenChunk(token=" ", index=1, is_end=False),
            TokenChunk(token="world", index=2, is_end=False),
            TokenChunk(token="!", index=3, is_end=False),
            TokenChunk(token="", index=4, is_end=True),
        ]
        for chunk in chunks:
            yield chunk
    
    return chunk_generator()


# Test data constants
MOCK_LLM_RESPONSE = {
    "choices": [{"message": {"content": "Test response"}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    "model": "test-model"
}

MOCK_STREAMING_CHUNKS = [
    'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
    'data: {"choices":[{"delta":{"content":" "}}]}\n',
    'data: {"choices":[{"delta":{"content":"world"}}]}\n',
    'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
]

MOCK_MODELS_RESPONSE = {
    "data": [
        {"id": "model-1", "object": "model"},
        {"id": "model-2", "object": "model"}
    ]
}


# Skip logic helpers for live provider tests
def check_openrouter_available():
    """
    Check if OpenRouter is available for testing.
    
    WHAT: Verify OpenRouter provider is enabled and API key is set
    WHY: Skip tests if provider not configured
    HOW: Check env vars and settings
    """
    run_live = os.getenv("RUN_LIVE_PROVIDER_TESTS", "false").lower() == "true"
    if not run_live:
        return False
    
    provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER)
    enable_openrouter = os.getenv("LLM_ENABLE_OPENROUTER", str(settings.LLM_ENABLE_OPENROUTER)).lower() == "true"
    api_key = os.getenv("OPENROUTER_API_KEY", settings.OPENROUTER_API_KEY)
    
    return provider == "openrouter" and enable_openrouter and bool(api_key)


async def check_lm_studio_available():
    """
    Check if LM Studio is available for testing.
    
    WHAT: Verify LM Studio server is reachable
    WHY: Skip tests if server not running
    HOW: Attempt HTTP connection to base URL
    """
    run_live = os.getenv("RUN_LIVE_PROVIDER_TESTS", "false").lower() == "true"
    if not run_live:
        return False
    
    provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER)
    if provider != "lm_studio":
        return False
    
    base_url = os.getenv("LM_STUDIO_BASE_URL", settings.LM_STUDIO_BASE_URL)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/models", timeout=2.0)
            return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def skip_if_no_openrouter():
    """Skip test if OpenRouter not available."""
    if not check_openrouter_available():
        pytest.skip("OpenRouter not available (set RUN_LIVE_PROVIDER_TESTS=true, LLM_PROVIDER=openrouter, LLM_ENABLE_OPENROUTER=true, OPENROUTER_API_KEY)")


@pytest.fixture
async def skip_if_no_lm_studio():
    """Skip test if LM Studio not available."""
    if not await check_lm_studio_available():
        pytest.skip("LM Studio not available (set RUN_LIVE_PROVIDER_TESTS=true, LLM_PROVIDER=lm_studio, ensure LM Studio server running)")

