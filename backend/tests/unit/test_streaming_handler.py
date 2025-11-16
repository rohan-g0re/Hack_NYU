"""
Unit tests for streaming handler utilities.

WHAT: Test coalesce_chunks, bounded_stream, and combined streaming utilities
WHY: Ensure streaming control works correctly for SSE and agent consumers
HOW: Mock token streams and verify buffering and bounding behavior
"""

import pytest
from app.llm.types import TokenChunk
from app.llm.streaming_handler import (
    coalesce_chunks,
    bounded_stream,
    coalesce_and_bound
)


@pytest.mark.phase1
@pytest.mark.unit
class TestCoalesceChunks:
    """Test token chunk coalescing with time-based buffering."""
    
    async def make_chunk_stream(self, tokens: list[str]):
        """Helper to create token chunk stream."""
        for i, token in enumerate(tokens):
            yield TokenChunk(token=token, index=i, is_end=False)
        yield TokenChunk(token="", index=len(tokens), is_end=True)
    
    @pytest.mark.asyncio
    async def test_coalesce_basic(self):
        """Test basic chunk coalescing."""
        chunks = self.make_chunk_stream(["Hello", " ", "world", "!"])
        
        results = []
        async for text in coalesce_chunks(chunks, flush_ms=50):
            results.append(text)
        
        # Should coalesce some chunks together
        full_text = "".join(results)
        assert full_text == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_coalesce_empty_stream(self):
        """Test coalescing with empty stream."""
        async def empty_stream():
            yield TokenChunk(token="", index=0, is_end=True)
        
        results = []
        async for text in coalesce_chunks(empty_stream(), flush_ms=50):
            results.append(text)
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_coalesce_single_token(self):
        """Test coalescing with single token."""
        chunks = self.make_chunk_stream(["Hello"])
        
        results = []
        async for text in coalesce_chunks(chunks, flush_ms=50):
            results.append(text)
        
        assert len(results) >= 1
        assert "".join(results) == "Hello"
    
    @pytest.mark.asyncio
    async def test_coalesce_many_tokens(self):
        """Test coalescing with many tokens."""
        tokens = [f"token{i}" for i in range(20)]
        chunks = self.make_chunk_stream(tokens)
        
        results = []
        async for text in coalesce_chunks(chunks, flush_ms=50):
            results.append(text)
        
        # Should flush multiple times due to buffer size
        assert len(results) > 1
        assert "".join(results) == "".join(tokens)
    
    @pytest.mark.asyncio
    async def test_coalesce_preserves_content(self):
        """Test that coalescing preserves all content."""
        tokens = ["The", " ", "quick", " ", "brown", " ", "fox"]
        chunks = self.make_chunk_stream(tokens)
        
        results = []
        async for text in coalesce_chunks(chunks, flush_ms=50):
            results.append(text)
        
        assert "".join(results) == "The quick brown fox"


@pytest.mark.phase1
@pytest.mark.unit
class TestBoundedStream:
    """Test bounded streaming with character limits."""
    
    async def make_chunk_stream(self, tokens: list[str]):
        """Helper to create token chunk stream."""
        for i, token in enumerate(tokens):
            yield TokenChunk(token=token, index=i, is_end=False)
        yield TokenChunk(token="", index=len(tokens), is_end=True)
    
    @pytest.mark.asyncio
    async def test_bounded_within_limit(self):
        """Test bounded stream when content is within limit."""
        chunks = self.make_chunk_stream(["Hello", " ", "world"])
        
        results = []
        async for text in bounded_stream(chunks, max_chars=100):
            results.append(text)
        
        assert "".join(results) == "Hello world"
    
    @pytest.mark.asyncio
    async def test_bounded_exceeds_limit(self):
        """Test bounded stream when content exceeds limit."""
        tokens = ["Hello", " ", "world", " ", "this", " ", "is", " ", "long"]
        chunks = self.make_chunk_stream(tokens)
        
        results = []
        async for text in bounded_stream(chunks, max_chars=10):
            results.append(text)
        
        full_text = "".join(results)
        assert len(full_text) <= 10
        assert full_text == "Hello worl"  # Should be truncated
    
    @pytest.mark.asyncio
    async def test_bounded_exact_limit(self):
        """Test bounded stream at exact character limit."""
        chunks = self.make_chunk_stream(["Hello"])
        
        results = []
        async for text in bounded_stream(chunks, max_chars=5):
            results.append(text)
        
        assert "".join(results) == "Hello"
    
    @pytest.mark.asyncio
    async def test_bounded_zero_limit(self):
        """Test bounded stream with zero limit."""
        chunks = self.make_chunk_stream(["Hello", " ", "world"])
        
        results = []
        async for text in bounded_stream(chunks, max_chars=0):
            results.append(text)
        
        assert "".join(results) == ""
    
    @pytest.mark.asyncio
    async def test_bounded_truncates_long_token(self):
        """Test that bounded stream truncates individual long tokens."""
        chunks = self.make_chunk_stream(["VeryLongToken"])
        
        results = []
        async for text in bounded_stream(chunks, max_chars=5):
            results.append(text)
        
        assert "".join(results) == "VeryL"
    
    @pytest.mark.asyncio
    async def test_bounded_multiple_tokens_hits_limit(self):
        """Test bounded stream with multiple tokens hitting limit."""
        chunks = self.make_chunk_stream(["ABC", "DEF", "GHI"])
        
        results = []
        async for text in bounded_stream(chunks, max_chars=7):
            results.append(text)
        
        full_text = "".join(results)
        assert len(full_text) <= 7
        assert full_text == "ABCDEFG"


@pytest.mark.phase1
@pytest.mark.unit
class TestCoalesceAndBound:
    """Test combined coalescing and bounding."""
    
    async def make_chunk_stream(self, tokens: list[str]):
        """Helper to create token chunk stream."""
        for i, token in enumerate(tokens):
            yield TokenChunk(token=token, index=i, is_end=False)
        yield TokenChunk(token="", index=len(tokens), is_end=True)
    
    @pytest.mark.asyncio
    async def test_coalesce_and_bound_basic(self):
        """Test combined coalescing and bounding."""
        chunks = self.make_chunk_stream(["Hello", " ", "world", "!"])
        
        results = []
        async for text in coalesce_and_bound(chunks, flush_ms=50, max_chars=100):
            results.append(text)
        
        full_text = "".join(results)
        assert full_text == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_coalesce_and_bound_exceeds_limit(self):
        """Test combined coalescing and bounding when exceeding limit."""
        tokens = ["The", " ", "quick", " ", "brown", " ", "fox", " ", "jumps"]
        chunks = self.make_chunk_stream(tokens)
        
        results = []
        async for text in coalesce_and_bound(chunks, flush_ms=50, max_chars=15):
            results.append(text)
        
        full_text = "".join(results)
        assert len(full_text) <= 15
        assert full_text.startswith("The quick")
    
    @pytest.mark.asyncio
    async def test_coalesce_and_bound_large_stream(self):
        """Test combined utilities with large token stream."""
        tokens = [f"word{i} " for i in range(100)]
        chunks = self.make_chunk_stream(tokens)
        
        results = []
        async for text in coalesce_and_bound(chunks, flush_ms=50, max_chars=500):
            results.append(text)
        
        full_text = "".join(results)
        assert len(full_text) <= 500
        assert len(results) > 1  # Should be coalesced into multiple chunks
    
    @pytest.mark.asyncio
    async def test_coalesce_and_bound_empty(self):
        """Test combined utilities with empty stream."""
        async def empty_stream():
            yield TokenChunk(token="", index=0, is_end=True)
        
        results = []
        async for text in coalesce_and_bound(empty_stream(), flush_ms=50, max_chars=100):
            results.append(text)
        
        assert len(results) == 0


@pytest.mark.phase1
@pytest.mark.unit
class TestStreamingEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_stream_with_empty_tokens(self):
        """Test streaming with some empty tokens."""
        async def chunk_stream():
            yield TokenChunk(token="Hello", index=0, is_end=False)
            yield TokenChunk(token="", index=1, is_end=False)  # Empty token
            yield TokenChunk(token=" world", index=2, is_end=False)
            yield TokenChunk(token="", index=3, is_end=True)
        
        results = []
        async for text in coalesce_chunks(chunk_stream(), flush_ms=50):
            results.append(text)
        
        assert "".join(results) == "Hello world"
    
    @pytest.mark.asyncio
    async def test_bounded_stream_with_unicode(self):
        """Test bounded stream with unicode characters."""
        async def chunk_stream():
            yield TokenChunk(token="Hello ", index=0, is_end=False)
            yield TokenChunk(token="🌍", index=1, is_end=False)
            yield TokenChunk(token=" world", index=2, is_end=False)
            yield TokenChunk(token="", index=3, is_end=True)
        
        results = []
        async for text in bounded_stream(chunk_stream(), max_chars=20):
            results.append(text)
        
        full_text = "".join(results)
        assert "Hello 🌍 world" == full_text
    
    @pytest.mark.asyncio
    async def test_immediate_end_signal(self):
        """Test stream that ends immediately."""
        async def chunk_stream():
            yield TokenChunk(token="", index=0, is_end=True)
        
        results = []
        async for text in coalesce_chunks(chunk_stream(), flush_ms=50):
            results.append(text)
        
        assert len(results) == 0

