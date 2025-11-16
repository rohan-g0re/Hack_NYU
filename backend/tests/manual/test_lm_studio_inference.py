"""
Comprehensive LM Studio inference testing script.

WHAT: Test LM Studio provider with actual running server
WHY: Verify connectivity, ping, generate, and streaming work correctly
HOW: Direct provider testing with multiple connection attempts
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.lm_studio import LMStudioProvider
from app.llm.types import ChatMessage
from app.core.config import settings
from app.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def test_ping(provider: LMStudioProvider, label: str = ""):
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
            print(f"   Models: {', '.join(status.models)}")
        if status.error:
            print(f"   Error: {status.error}")
        return status.available
    except Exception as e:
        print(f"[FAIL] Ping Failed: {e}")
        return False


async def test_generate(provider: LMStudioProvider, label: str = ""):
    """Test non-streaming generation."""
    print(f"\n{'='*60}")
    print(f"Testing Generate (Non-Streaming) {label}")
    print(f"{'='*60}")
    
    messages: list[ChatMessage] = [
        {"role": "user", "content": "Say 'Hello from LM Studio!' in exactly 5 words."}
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
        print(f"   Response: {result.text}")
        print(f"   Usage: {result.usage}")
        return True
        
    except Exception as e:
        print(f"[FAIL] Generate Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stream(provider: LMStudioProvider, label: str = ""):
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
        print(f"   Full text: {full_text.strip()}")
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Stream Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_url(base_url: str, model: str):
    """Test provider with specific base URL."""
    print(f"\n{'#'*60}")
    print(f"Testing with Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"{'#'*60}")
    
    # Create provider with custom URL
    provider = LMStudioProvider()
    provider.base_url = base_url
    provider.default_model = model
    
    label = f"({base_url})"
    
    # Test ping
    ping_ok = await test_ping(provider, label)
    if not ping_ok:
        print(f"\n[WARN] Ping failed, skipping generate/stream tests")
        return False
    
    # Test generate
    generate_ok = await test_generate(provider, label)
    
    # Test stream
    stream_ok = await test_stream(provider, label)
    
    return ping_ok and generate_ok and stream_ok


async def main():
    """Main test function."""
    print(f"\n{'='*60}")
    print(f"LM Studio Inference Testing")
    print(f"{'='*60}")
    
    print(f"\n[*] Current Configuration:")
    print(f"   LLM_PROVIDER: {settings.LLM_PROVIDER}")
    print(f"   LM_STUDIO_BASE_URL: {settings.LM_STUDIO_BASE_URL}")
    print(f"   LM_STUDIO_DEFAULT_MODEL: {settings.LM_STUDIO_DEFAULT_MODEL}")
    print(f"   LM_STUDIO_TIMEOUT: {settings.LM_STUDIO_TIMEOUT}")
    
    # Test URLs to try
    test_urls = [
        settings.LM_STUDIO_BASE_URL,  # Current config
        "http://localhost:1234/v1",   # Standard localhost
        "http://10.20.24.113:1234/v1", # Network IP from screenshot
    ]
    
    # Remove duplicates
    test_urls = list(dict.fromkeys(test_urls))
    
    model = settings.LM_STUDIO_DEFAULT_MODEL
    
    print(f"\n[*] Testing {len(test_urls)} URL(s)...")
    
    success_count = 0
    for url in test_urls:
        try:
            result = await test_with_url(url, model)
            if result:
                success_count += 1
                print(f"\n[OK] SUCCESS with {url}")
                print(f"\n[!] Recommendation: Update LM_STUDIO_BASE_URL in .env to:")
                print(f"   LM_STUDIO_BASE_URL={url}")
                break  # Stop on first success
            else:
                print(f"\n[FAIL] FAILED with {url}")
        except Exception as e:
            print(f"\n[ERROR] ERROR with {url}: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}")
    print(f"   URLs tested: {len(test_urls)}")
    print(f"   Successful: {success_count}")
    
    if success_count > 0:
        print(f"\n[OK] LM Studio inference is working!")
        print(f"   Update your .env file with the working URL above.")
    else:
        print(f"\n[FAIL] All connection attempts failed.")
        print(f"\n[*] Troubleshooting:")
        print(f"   1. Verify LM Studio server is running")
        print(f"   2. Check the server URL in LM Studio (Server Settings)")
        print(f"   3. Ensure model '{model}' is loaded")
        print(f"   4. Check firewall/network settings")
        print(f"   5. Try: curl {test_urls[0]}/models")
    
    return success_count > 0


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

