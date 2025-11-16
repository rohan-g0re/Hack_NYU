"""
Comprehensive OpenRouter inference testing script.

WHAT: Test OpenRouter provider with actual API
WHY: Verify connectivity, ping, generate, and streaming work correctly
HOW: Direct provider testing with API key from environment
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.openrouter import OpenRouterProvider
from app.llm.types import ChatMessage
from app.core.config import settings
from app.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def test_ping(provider: OpenRouterProvider, label: str = ""):
    """Test ping endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing Ping {label}")
    print(f"{'='*60}")
    
    try:
        status = await provider.ping()
        print(f"[OK] Ping Successful!")
        print(f"   Available: {status.available}")
        print(f"   Base URL: {status.base_url}")
        if status.models:
            print(f"   Models Available: {len(status.models)} models")
            print(f"   Sample Models: {', '.join(status.models[:5])}")
        if status.error:
            print(f"   Error: {status.error}")
        return status.available
    except Exception as e:
        print(f"[FAIL] Ping Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generate(provider: OpenRouterProvider, label: str = ""):
    """Test non-streaming generation."""
    print(f"\n{'='*60}")
    print(f"Testing Generate (Non-Streaming) {label}")
    print(f"{'='*60}")
    
    messages: list[ChatMessage] = [
        {"role": "user", "content": "Say 'Hello from OpenRouter!' in exactly 5 words."}
    ]
    
    try:
        print(f"[*] Sending request...")
        print(f"   Messages: {len(messages)}")
        print(f"   Model: {provider.default_model}")
        print(f"   Temperature: 0.7")
        print(f"   Max Tokens: 50")
        
        result = await provider.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"\n[OK] Generate Successful!")
        print(f"   Model: {result.model}")
        print(f"   Response: {result.text[:200]}...")
        print(f"   Usage: {result.usage}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Generate Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stream(provider: OpenRouterProvider, label: str = ""):
    """Test streaming generation."""
    print(f"\n{'='*60}")
    print(f"Testing Stream {label}")
    print(f"{'='*60}")
    
    messages: list[ChatMessage] = [
        {"role": "user", "content": "Count from 1 to 5, one number per line."}
    ]
    
    try:
        print(f"[*] Starting stream...")
        print(f"   Messages: {len(messages)}")
        print(f"   Model: {provider.default_model}")
        
        tokens_received = 0
        full_text = ""
        
        print(f"\n[*] Streaming response:")
        print(f"   ", end="", flush=True)
        
        async for chunk in provider.stream(
            messages=messages,
            temperature=0.7,
            max_tokens=50
        ):
            tokens_received += 1
            full_text += chunk.token
            print(chunk.token, end="", flush=True)
            
            if chunk.is_end:
                print(f"\n")
                break
        
        print(f"\n[OK] Stream Successful!")
        print(f"   Tokens received: {tokens_received}")
        print(f"   Full text: {full_text.strip()[:200]}...")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Stream Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print(f"\n{'='*60}")
    print(f"OpenRouter Inference Testing")
    print(f"{'='*60}")
    
    print(f"\n[*] Current Configuration:")
    print(f"   LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"   LLM_ENABLE_OPENROUTER: {settings.LLM_ENABLE_OPENROUTER}")
    print(f"   OPENROUTER_BASE_URL: {settings.OPENROUTER_BASE_URL}")
    print(f"   OPENROUTER_DEFAULT_MODEL: {settings.OPENROUTER_DEFAULT_MODEL}")
    print(f"   OPENROUTER_TIMEOUT: {settings.OPENROUTER_TIMEOUT}")
    print(f"   OPENROUTER_API_KEY: {'*' * 20 if settings.OPENROUTER_API_KEY else 'NOT SET'}")
    
    if not settings.LLM_ENABLE_OPENROUTER:
        print(f"\n[WARN] OpenRouter is disabled!")
        print(f"   Set LLM_ENABLE_OPENROUTER=true in .env to enable")
        return False
    
    if not settings.OPENROUTER_API_KEY:
        print(f"\n[WARN] OPENROUTER_API_KEY is not set!")
        print(f"   Add your API key to .env file")
        return False
    
    # Create provider
    provider = OpenRouterProvider()
    
    if not provider.enabled:
        print(f"\n[FAIL] Provider is disabled")
        return False
    
    print(f"\n[*] Testing OpenRouter provider...")
    
    # Test ping
    ping_ok = await test_ping(provider)
    if not ping_ok:
        print(f"\n[WARN] Ping failed, skipping generate/stream tests")
        print(f"\n[*] Troubleshooting:")
        print(f"   1. Verify OPENROUTER_API_KEY is correct")
        print(f"   2. Check network connection")
        print(f"   3. Verify API key has credits/permissions")
        return False
    
    # Test generate
    generate_ok = await test_generate(provider)
    
    # Test stream
    stream_ok = await test_stream(provider)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"   Ping: {'[OK]' if ping_ok else '[FAIL]'}")
    print(f"   Generate: {'[OK]' if generate_ok else '[FAIL]'}")
    print(f"   Stream: {'[OK]' if stream_ok else '[FAIL]'}")
    
    success = ping_ok and generate_ok and stream_ok
    
    if success:
        print(f"\n[OK] OpenRouter inference is working!")
    else:
        print(f"\n[FAIL] Some tests failed")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n[WARN] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

