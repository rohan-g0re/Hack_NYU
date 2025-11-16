"""
Pytest configuration and shared fixtures for backend tests.

WHAT: Centralized test configuration with phase markers
WHY: Enable test organization, filtering, and shared test utilities
HOW: Define pytest markers, fixtures, and test helpers
"""

import pytest
import asyncio
from typing import AsyncIterator
from unittest.mock import patch

from app.llm.provider_factory import reset_provider


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
        mock.CORS_ORIGINS = "http://localhost:3000"
        mock.cors_origins_list = ["http://localhost:3000"]
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

