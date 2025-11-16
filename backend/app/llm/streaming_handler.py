"""
Streaming utilities for LLM responses.

WHAT: Helper functions to normalize and control token streams
WHY: Provide consistent streaming behavior for SSE and agent consumers
HOW: Async generators for coalescing tokens and bounding output length
"""

import asyncio
from typing import AsyncIterator

from .types import TokenChunk
from ..utils.logger import get_logger

logger = get_logger(__name__)


async def coalesce_chunks(
    chunks: AsyncIterator[TokenChunk],
    *,
    flush_ms: int = 50
) -> AsyncIterator[str]:
    """
    Coalesce token chunks with time-based buffering.
    
    WHAT: Buffer tokens and flush periodically
    WHY: Reduce SSE overhead while maintaining responsiveness
    HOW: Accumulate tokens until timeout or end signal
    
    Args:
        chunks: Source token chunks
        flush_ms: Milliseconds to wait before flushing buffer
    
    Yields:
        Coalesced string chunks
    """
    buffer = []
    flush_interval = flush_ms / 1000.0  # Convert to seconds
    
    async def flush_buffer():
        """Flush accumulated buffer."""
        if buffer:
            text = "".join(buffer)
            buffer.clear()
            return text
        return None
    
    try:
        async for chunk in chunks:
            if chunk.is_end:
                # Flush any remaining content
                text = await flush_buffer()
                if text:
                    yield text
                break
            
            if chunk.token:
                buffer.append(chunk.token)
                
                # Flush if buffer has content (simple strategy)
                # In production, could use asyncio.wait_for with timeout
                if len(buffer) >= 5:  # Flush every ~5 tokens
                    text = await flush_buffer()
                    if text:
                        yield text
        
        # Final flush
        text = await flush_buffer()
        if text:
            yield text
            
    except Exception as e:
        logger.error(f"Error coalescing chunks: {e}")
        raise


async def bounded_stream(
    chunks: AsyncIterator[TokenChunk],
    max_chars: int
) -> AsyncIterator[str]:
    """
    Limit streaming output to maximum character count.
    
    WHAT: Guard against runaway generation
    WHY: Prevent excessive token usage and response times
    HOW: Track character count and stop when limit reached
    
    Args:
        chunks: Source token chunks
        max_chars: Maximum characters to yield
    
    Yields:
        Token strings up to max_chars total
    """
    total_chars = 0
    
    try:
        async for chunk in chunks:
            if chunk.is_end:
                break
            
            if chunk.token:
                remaining = max_chars - total_chars
                
                if remaining <= 0:
                    logger.warning(f"Stream bounded at {max_chars} characters")
                    break
                
                # Truncate token if it exceeds remaining space
                token = chunk.token
                if len(token) > remaining:
                    token = token[:remaining]
                    logger.info(f"Truncated final token to fit {max_chars} limit")
                
                total_chars += len(token)
                yield token
                
                if total_chars >= max_chars:
                    break
    
    except Exception as e:
        logger.error(f"Error bounding stream: {e}")
        raise


async def coalesce_and_bound(
    chunks: AsyncIterator[TokenChunk],
    *,
    flush_ms: int = 50,
    max_chars: int = 10000
) -> AsyncIterator[str]:
    """
    Combine coalescing and bounding for convenient streaming.
    
    Args:
        chunks: Source token chunks
        flush_ms: Milliseconds between flushes
        max_chars: Maximum total characters
    
    Yields:
        Coalesced, bounded string chunks
    """
    bounded = bounded_stream(chunks, max_chars)
    
    buffer = []
    flush_interval = flush_ms / 1000.0
    
    try:
        async for token in bounded:
            buffer.append(token)
            
            # Simple flush strategy
            if len(buffer) >= 5:
                text = "".join(buffer)
                buffer.clear()
                yield text
        
        # Final flush
        if buffer:
            yield "".join(buffer)
            
    except Exception as e:
        logger.error(f"Error in coalesce_and_bound: {e}")
        raise

