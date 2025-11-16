"""
Manual test script for Phase 1 - LLM Provider Layer.

WHAT: Interactive test to verify LM Studio integration works
WHY: Quick manual verification that Phase 1 is functional
HOW: Run this script to test ping, generate, and streaming

Usage:
    conda activate hackathon
    cd backend
    python test_phase1_manual.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.llm.lm_studio import LMStudioProvider
from app.llm.streaming_handler import coalesce_chunks
from app.core.config import settings


async def test_ping():
    """Test 1: Check if LM Studio is reachable."""
    print("=" * 60)
    print("TEST 1: Ping LM Studio")
    print("=" * 60)
    
    provider = LMStudioProvider()
    status = await provider.ping()
    
    print(f"Available: {status.available}")
    print(f"Base URL: {status.base_url}")
    print(f"Models: {status.models}")
    print(f"Error: {status.error}")
    
    if not status.available:
        print("\n❌ LM Studio is not available!")
        print("Make sure LM Studio is running at http://127.0.0.1:1234")
        return False
    
    print(f"\n✅ LM Studio is available with {len(status.models) if status.models else 0} models")
    return True


async def test_generate(prompt: str = "Can you tell me who are sidemen in 50 words or more"):
    """Test 2: Generate a complete response (non-streaming)."""
    print("\n" + "=" * 60)
    print("TEST 2: Generate (Non-Streaming)")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print("-" * 60)
    
    provider = LMStudioProvider()
    
    try:
        result = await provider.generate(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"Response: {result.text}")
        print(f"\nModel: {result.model}")
        print(f"Usage: {result.usage}")
        print("\n✅ Generate test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Generate test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stream(prompt: str = "Count from 1 to 5."):
    """Test 3: Stream a response token by token."""
    print("\n" + "=" * 60)
    print("TEST 3: Stream (Token by Token)")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print("-" * 60)
    print("Streaming response: ", end="", flush=True)
    
    provider = LMStudioProvider()
    
    try:
        full_text = []
        chunk_count = 0
        
        async for chunk in provider.stream(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        ):
            if chunk.is_end:
                break
            if chunk.token:
                print(chunk.token, end="", flush=True)
                full_text.append(chunk.token)
                chunk_count += 1
        
        print(f"\n\n✅ Stream test passed! ({chunk_count} chunks received)")
        return True
        
    except Exception as e:
        print(f"\n\n❌ Stream test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_coalesced_stream(prompt: str = "Explain what AI is in one sentence."):
    """Test 4: Stream with coalescing (buffered chunks)."""
    print("\n" + "=" * 60)
    print("TEST 4: Coalesced Stream (Buffered)")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print("-" * 60)
    print("Coalesced response: ", end="", flush=True)
    
    provider = LMStudioProvider()
    
    try:
        chunks_stream = provider.stream(
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be very concise."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=80
        )
        
        coalesced = coalesce_chunks(chunks_stream, flush_ms=50)
        chunk_count = 0
        
        async for text in coalesced:
            print(text, end="", flush=True)
            chunk_count += 1
        
        print(f"\n\n✅ Coalesced stream test passed! ({chunk_count} coalesced chunks)")
        return True
        
    except Exception as e:
        print(f"\n\n❌ Coalesced stream test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_prompt():
    """Test 5: Your own custom prompt."""
    print("\n" + "=" * 60)
    print("TEST 5: Custom Prompt")
    print("=" * 60)
    
    # You can change this to test your own prompt
    custom_prompt = "Write a haiku about coding."
    
    print(f"Prompt: {custom_prompt}")
    print("-" * 60)
    print("Response: ", end="", flush=True)
    
    provider = LMStudioProvider()
    
    try:
        async for chunk in provider.stream(
            messages=[
                {"role": "user", "content": custom_prompt}
            ],
            temperature=0.8,
            max_tokens=100
        ):
            if chunk.is_end:
                break
            if chunk.token:
                print(chunk.token, end="", flush=True)
        
        print("\n\n✅ Custom prompt test passed!")
        return True
        
    except Exception as e:
        print(f"\n\n❌ Custom prompt test failed: {e}")
        return False


async def run_all_tests():
    """Run all Phase 1 tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PHASE 1 MANUAL TEST SUITE" + " " * 23 + "║")
    print("║" + " " * 10 + "LLM Provider Layer Verification" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    print(f"LM Studio URL: {settings.LM_STUDIO_BASE_URL}")
    print(f"Model: {settings.LM_STUDIO_DEFAULT_MODEL}")
    print()
    
    results = []
    
    # Test 1: Ping
    try:
        result = await test_ping()
        results.append(("Ping", result))
        if not result:
            print("\n⚠️  Stopping tests - LM Studio not available")
            return
    except Exception as e:
        print(f"\n❌ Ping test crashed: {e}")
        results.append(("Ping", False))
        return
    
    # Test 2: Generate
    try:
        result = await test_generate()
        results.append(("Generate", result))
    except Exception as e:
        print(f"\n❌ Generate test crashed: {e}")
        results.append(("Generate", False))
    
    # Test 3: Stream
    try:
        result = await test_stream()
        results.append(("Stream", result))
    except Exception as e:
        print(f"\n❌ Stream test crashed: {e}")
        results.append(("Stream", False))
    
    # Test 4: Coalesced Stream
    try:
        result = await test_coalesced_stream()
        results.append(("Coalesced Stream", result))
    except Exception as e:
        print(f"\n❌ Coalesced stream test crashed: {e}")
        results.append(("Coalesced Stream", False))
    
    # Test 5: Custom Prompt
    try:
        result = await test_custom_prompt()
        results.append(("Custom Prompt", result))
    except Exception as e:
        print(f"\n❌ Custom prompt test crashed: {e}")
        results.append(("Custom Prompt", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 1 tests passed! The LLM provider layer is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("\nStarting Phase 1 manual tests...")
    print("Press Ctrl+C to stop\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

