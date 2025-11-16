#!/usr/bin/env python3
"""
Test both LM Studio and OpenRouter providers.

WHAT: Test both providers regardless of LLM_PROVIDER setting
WHY: Verify both providers work correctly
HOW: Temporarily override provider selection for each test
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.lm_studio import LMStudioProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.types import ChatMessage
from app.core.config import settings
from app.utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def test_lm_studio_direct():
    """Test LM Studio provider directly."""
    print(f"\n{'#'*60}")
    print(f"# Testing LM Studio Provider (Direct)")
    print(f"{'#'*60}")
    
    print(f"\n[*] Configuration:")
    print(f"  - Base URL: {settings.LM_STUDIO_BASE_URL}")
    print(f"  - Model: {settings.LM_STUDIO_DEFAULT_MODEL}")
    print(f"  - Timeout: {settings.LM_STUDIO_TIMEOUT}")
    
    provider = LMStudioProvider()
    results = []
    
    # Test ping
    print(f"\n[*] Testing ping...")
    try:
        status = await provider.ping()
        print(f"[OK] Ping: available={status.available}")
        if status.error:
            print(f"  Error: {status.error}")
        results.append(status.available)
    except Exception as e:
        print(f"[FAIL] Ping failed: {e}")
        results.append(False)
    
    if not results[0]:
        print(f"\n[SKIP] LM Studio not available, skipping generate/stream tests")
        return False
    
    # Test generate
    print(f"\n[*] Testing generate...")
    try:
        messages: list[ChatMessage] = [
            {"role": "user", "content": "Say 'Hello from LM Studio!'"}
        ]
        result = await provider.generate(messages=messages, temperature=0.7, max_tokens=30)
        print(f"[OK] Generate: {result.text[:50]}...")
        results.append(True)
    except Exception as e:
        print(f"[FAIL] Generate failed: {e}")
        results.append(False)
    
    # Test stream
    print(f"\n[*] Testing stream...")
    try:
        messages: list[ChatMessage] = [
            {"role": "user", "content": "Count 1, 2, 3"}
        ]
        tokens = []
        async for chunk in provider.stream(messages=messages, temperature=0.7, max_tokens=20):
            tokens.append(chunk.token)
            if chunk.is_end:
                break
        print(f"[OK] Stream: received {len(tokens)} tokens")
        results.append(len(tokens) > 0)
    except Exception as e:
        print(f"[FAIL] Stream failed: {e}")
        results.append(False)
    
    return all(results)


async def test_openrouter_direct():
    """Test OpenRouter provider directly."""
    print(f"\n{'#'*60}")
    print(f"# Testing OpenRouter Provider (Direct)")
    print(f"{'#'*60}")
    
    print(f"\n[*] Configuration:")
    print(f"  - Enabled: {settings.LLM_ENABLE_OPENROUTER}")
    print(f"  - Base URL: {settings.OPENROUTER_BASE_URL}")
    print(f"  - API Key: {'*' * 20 if settings.OPENROUTER_API_KEY else '(not set)'}")
    
    if not settings.LLM_ENABLE_OPENROUTER:
        print(f"\n[SKIP] OpenRouter is disabled (LLM_ENABLE_OPENROUTER=false)")
        return None
    
    if not settings.OPENROUTER_API_KEY:
        print(f"\n[SKIP] OpenRouter API key not set")
        return None
    
    provider = OpenRouterProvider()
    results = []
    
    # Test ping
    print(f"\n[*] Testing ping...")
    try:
        status = await provider.ping()
        print(f"[OK] Ping: available={status.available}")
        if status.error:
            print(f"  Error: {status.error}")
        results.append(status.available)
    except Exception as e:
        print(f"[FAIL] Ping failed: {e}")
        results.append(False)
    
    if not results[0]:
        print(f"\n[SKIP] OpenRouter not available, skipping generate/stream tests")
        return False
    
    # Test generate
    print(f"\n[*] Testing generate...")
    try:
        messages: list[ChatMessage] = [
            {"role": "user", "content": "Say 'Hello from OpenRouter!'"}
        ]
        result = await provider.generate(messages=messages, temperature=0.7, max_tokens=30)
        print(f"[OK] Generate: {result.text[:50]}...")
        results.append(True)
    except Exception as e:
        print(f"[FAIL] Generate failed: {e}")
        results.append(False)
    
    # Test stream
    print(f"\n[*] Testing stream...")
    try:
        messages: list[ChatMessage] = [
            {"role": "user", "content": "Count 1, 2, 3"}
        ]
        tokens = []
        async for chunk in provider.stream(messages=messages, temperature=0.7, max_tokens=20):
            tokens.append(chunk.token)
            if chunk.is_end:
                break
        print(f"[OK] Stream: received {len(tokens)} tokens")
        results.append(len(tokens) > 0)
    except Exception as e:
        print(f"[FAIL] Stream failed: {e}")
        results.append(False)
    
    return all(results)


async def main():
    """Run tests for both providers."""
    print("="*60)
    print("Phase 1 - Testing Both Providers")
    print("="*60)
    
    results = {}
    
    # Test LM Studio
    results["lm_studio"] = await test_lm_studio_direct()
    
    # Test OpenRouter
    results["openrouter"] = await test_openrouter_direct()
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    for provider, result in results.items():
        if result is None:
            print(f"  {provider}: SKIPPED (not configured)")
        elif result:
            print(f"  {provider}: PASSED")
        else:
            print(f"  {provider}: FAILED")
    
    all_passed = all(r for r in results.values() if r is not None)
    any_tested = any(r is not None for r in results.values())
    
    if any_tested and all_passed:
        print(f"\n[SUCCESS] All configured providers passed!")
        return 0
    elif any_tested:
        print(f"\n[PARTIAL] Some providers failed or were skipped")
        return 1
    else:
        print(f"\n[SKIP] No providers configured for testing")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Tests cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

