# Multi-Agent Marketplace Backend - Phase 1

Backend API for LLM-powered multi-agent negotiation marketplace.

## Phase 1: LLM Inference Setup ✅

**WHAT:** Robust LLM provider layer with streaming support  
**WHY:** Enable local-first inference for agent negotiations  
**HOW:** Provider abstraction with LM Studio + OpenRouter stub

### Implemented Features

- ✅ **Provider Architecture**
  - Protocol-based provider interface
  - Factory pattern with singleton caching
  - Support for multiple providers (LM Studio, OpenRouter)

- ✅ **LM Studio Provider**
  - Async HTTP client with connection pooling
  - Exponential backoff retry logic (3 retries, 2s base delay)
  - SSE streaming for real-time token generation
  - Comprehensive error mapping

- ✅ **OpenRouter Provider**
  - Stub implementation (disabled by default)
  - Ready for future cloud-based inference

- ✅ **Streaming Utilities**
  - Token coalescing with buffering
  - Bounded streaming to prevent runaway generation
  - Combined utilities for convenience

- ✅ **Health & Status**
  - `/api/v1/llm/status` - Provider and DB health
  - `/api/v1/health` - Overall system health with version
  - Real-time availability checks

- ✅ **Error Handling**
  - Custom exceptions for provider errors
  - HTTP status code mapping middleware
  - Clear error messages for debugging

- ✅ **Testing**
  - Unit tests for provider logic (respx mocking)
  - Integration tests for HTTP endpoints
  - Success and failure path coverage

## Setup

### Prerequisites

- Python 3.11+ (Windows ARM compatible)
- [LM Studio](https://lmstudio.ai/) running locally on port 1234
- Poetry for dependency management

### Installation

```bash
# Install dependencies
cd backend
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# (defaults should work for local LM Studio)
```

### Environment Variables

Key configuration (see `.env.example` for all options):

```env
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_DEFAULT_MODEL=llama-3-8b-instruct
LM_STUDIO_TIMEOUT=30
```

### Running

```bash
# Development mode with auto-reload
poetry run python -m app.main

# Or with uvicorn directly
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at `http://localhost:8000`

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_llm_provider.py -v

# Run integration tests only
poetry run pytest tests/integration/ -v
```

## API Endpoints

### Status & Health

- `GET /` - Root endpoint with app info
- `GET /api/v1/health` - Overall system health
- `GET /api/v1/llm/status` - LLM provider and database status

### Example Response

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "app_name": "Multi-Agent Marketplace",
  "components": {
    "llm": {
      "available": true,
      "provider": "lm_studio"
    },
    "database": {
      "available": true
    }
  }
}
```

## Architecture

### Directory Structure

```
backend/
├── app/
│   ├── llm/                   # LLM provider layer
│   │   ├── types.py          # Type definitions and exceptions
│   │   ├── provider.py       # Provider protocol
│   │   ├── provider_factory.py  # Factory with singleton
│   │   ├── lm_studio.py      # LM Studio implementation
│   │   ├── openrouter.py     # OpenRouter stub
│   │   └── streaming_handler.py  # Streaming utilities
│   ├── core/
│   │   ├── config.py         # Pydantic settings
│   │   └── database.py       # SQLAlchemy setup
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   └── status.py     # Health endpoints
│   │   └── router.py         # Route aggregation
│   ├── middleware/
│   │   └── error_handler.py  # Exception handlers
│   ├── utils/
│   │   └── logger.py         # Logging setup
│   └── main.py               # FastAPI app entry
└── tests/
    ├── unit/                  # Unit tests
    └── integration/           # Integration tests
```

### Error Codes

| Exception | HTTP Status | Error Code | Description |
|-----------|------------|------------|-------------|
| `ProviderDisabledError` | 400 | `LLM_PROVIDER_DISABLED` | Provider not enabled in config |
| `ProviderTimeoutError` | 503 | `LLM_TIMEOUT` | Request timed out |
| `ProviderUnavailableError` | 503 | `LLM_UNAVAILABLE` | Provider not reachable |
| `ProviderResponseError` | 502 | `LLM_BAD_GATEWAY` | Invalid provider response |

## Windows ARM Notes

**WHAT:** Special considerations for Windows ARM laptops  
**WHY:** Avoid native dependency build failures  
**HOW:** Pinned dependencies, no uvloop

- Using `httpx` with `http2=False` for compatibility
- No uvloop (uses default asyncio selector)
- Pinned versions: httpx, pydantic, sse-starlette
- Tested on Python 3.11+

## Next Steps (Phase 2+)

- [ ] Agent implementations (buyer, seller)
- [ ] LangGraph workflow orchestration
- [ ] Negotiation session management
- [ ] SSE streaming endpoints for real-time updates
- [ ] Message routing and visibility filtering

## Troubleshooting

### LM Studio Connection Issues

**Problem:** `LLM_UNAVAILABLE` error  
**Solution:** 
1. Ensure LM Studio is running
2. Check model is loaded in LM Studio
3. Verify port 1234 is not blocked
4. Test: `curl http://localhost:1234/v1/models`

### Import Errors

**Problem:** Module not found  
**Solution:**
```bash
# Ensure you're in poetry shell
poetry shell

# Or prefix commands with poetry run
poetry run python -m app.main
```

### Test Failures

**Problem:** Tests fail with connection errors  
**Solution:** Tests use mocked HTTP - no LM Studio needed. Check:
```bash
poetry install --with dev
poetry run pytest -v
```

## Contributing

Follow the WHAT < WHY < HOW documentation pattern in all code comments.

---

**Phase 1 Status:** ✅ Complete  
**Last Updated:** 2024-11-16

