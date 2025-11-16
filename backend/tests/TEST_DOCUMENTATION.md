# Test Documentation

This document provides a comprehensive overview of all existing tests in the codebase. Use this as a reference to understand what is already tested and avoid duplicating test coverage.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Manual Tests](#manual-tests)
5. [Test Fixtures and Utilities](#test-fixtures-and-utilities)
6. [Test Coverage Summary](#test-coverage-summary)
7. [Test Markers and Phases](#test-markers-and-phases)

---

## Test Structure

The test suite is organized into three main directories:

- **`tests/unit/`** - Unit tests for isolated components
- **`tests/integration/`** - Integration tests for multiple components working together
- **`tests/manual/`** - Manual tests requiring live providers or special setup

### Test Configuration

- **`conftest.py`** - Shared pytest fixtures and configuration
- **`pytest.ini`** - Pytest configuration file
- **`fixtures/`** - Reusable test fixtures

---

## Unit Tests

### `test_agents.py`
**Status:** Empty file (needs implementation)

**What should be tested:**
- BuyerAgent and SellerAgent initialization
- Agent message generation
- Agent decision making
- Offer parsing and validation

---

### `test_decision_engine.py`
**Coverage:** Decision validation and tie-breaking logic

**Test Classes:**
- `TestValidateDecision` - Validates buyer decisions
  - Valid offers within constraints
  - Offers below/above price bounds
  - Offers exceeding quantity needed
  - Missing price/quantity fields
  - Edge cases (exact min/max prices)
  
- `TestSelectBestOffer` - Tie-breaking logic
  - Single valid offer selection
  - Lowest price selection
  - Filtering invalid offers
  - Tie-breaking by responsiveness
  - Tie-breaking by rounds
  - Price grouping (within $0.01)
  
- `TestComputeTotalCost` - Cost calculations
  - Normal calculations
  - Single item
  - Large quantities
  - Zero price handling

**Key Functions Tested:**
- `validate_decision()`
- `select_best_offer()`
- `compute_total_cost()`

---

### `test_llm_provider.py`
**Coverage:** LLM provider factory and implementations

**Test Classes:**
- `TestProviderFactory` - Provider selection
  - LM Studio provider selection
  - OpenRouter provider selection
  - Unknown provider error
  - Singleton pattern
  
- `TestLMStudioProvider` - LM Studio implementation
  - Ping success/timeout/connection errors
  - Generation success/timeout/connection errors
  - Retry logic on 500 errors
  - Invalid JSON handling
  - Streaming success
  - Edge cases (stop sequences, missing fields, empty models)
  
- `TestOpenRouterProvider` - OpenRouter stub
  - Disabled provider errors
  
- `TestLMStudioProviderEdgeCases` - Additional edge cases
  - Stop sequences
  - 400 errors (no retry)
  - Exhausted retries
  - Streaming edge cases ([DONE] signal, invalid chunks, empty content)
  - Timeout and HTTP error handling

**Key Functions Tested:**
- `get_provider()`
- `reset_provider()`
- `LMStudioProvider.ping()`
- `LMStudioProvider.generate()`
- `LMStudioProvider.stream()`

---

### `test_message_routing.py`
**Coverage:** Message routing and mention parsing

**Test Functions:**
- Single mention parsing
- Multiple mentions parsing
- Case-insensitive matching
- No mentions handling
- Invalid mention handling
- Empty text handling
- Empty sellers list
- Duplicate mentions (unique IDs)
- Mentions with underscores

**Key Functions Tested:**
- `parse_mentions()`

---

### `test_prompts.py`
**Coverage:** Prompt template rendering

**Test Functions:**
- Buyer prompt structure and constraints
- Buyer prompt mention convention
- Seller prompt structure
- Seller prompt inventory bounds
- Seller prompt style and priority
- Seller prompt offer format hints

**Key Functions Tested:**
- `render_buyer_prompt()`
- `render_seller_prompt()`

---

### `test_schema_constraints.py`
**Coverage:** Database schema constraints

**Test Classes:**
- `TestCheckConstraints` - CHECK constraints
  - Buyer item quantity > 0
  - Max price > min price
  - Seller inventory price constraints (selling_price > cost_price, least_price > cost_price, least_price < selling_price)
  
- `TestUniqueConstraints` - UNIQUE constraints
  - Seller inventory (seller_id, item_id) uniqueness
  - Negotiation participant (negotiation_run_id, seller_id) uniqueness
  
- `TestForeignKeyCascades` - Foreign key cascades
  - Session deletion cascades to buyer
  - Buyer deletion cascades to buyer items
  - Seller deletion cascades to inventory
  
- `TestIndexes` - Database indexes
  - Session status index
  - Buyer session index
  - Negotiation run indexes
  - Message indexes

**Key Models Tested:**
- `Session`, `Buyer`, `BuyerItem`, `Seller`, `SellerInventory`
- `NegotiationRun`, `NegotiationParticipant`, `Message`, `Offer`, `NegotiationOutcome`

---

### `test_seller_selection.py`
**Coverage:** Seller selection logic (Phase 3)

**Test Class:**
- `TestSellerSelection` - Seller filtering
  - Selecting sellers with matching inventory
  - Skipping sellers with no inventory
  - Skipping sellers with insufficient quantity
  - Skipping sellers with price mismatch
  - Mixed scenarios with multiple sellers

**Key Functions Tested:**
- `select_sellers_for_item()`

---

### `test_seller_selection_phase3.py`
**Coverage:** Seller selection with database (Phase 3)

**Note:** Similar to `test_seller_selection.py` but uses database fixtures

---

### `test_streaming_handler.py`
**Coverage:** Streaming utilities

**Test Classes:**
- `TestCoalesceChunks` - Token chunk coalescing
  - Basic coalescing
  - Empty stream
  - Single token
  - Many tokens
  - Content preservation
  
- `TestBoundedStream` - Character limit bounding
  - Within limit
  - Exceeds limit
  - Exact limit
  - Zero limit
  - Long token truncation
  
- `TestCoalesceAndBound` - Combined utilities
  - Basic combined operation
  - Exceeds limit
  - Large stream
  - Empty stream
  
- `TestStreamingEdgeCases` - Edge cases
  - Empty tokens
  - Unicode characters
  - Immediate end signal

**Key Functions Tested:**
- `coalesce_chunks()`
- `bounded_stream()`
- `coalesce_and_bound()`

---

### `test_summary_service_phase3.py`
**Coverage:** Summary service for metrics computation

**Test Class:**
- `TestSummaryService` - Summary computation
  - Empty session summary
  - Session summary with multiple runs
  - Run summary computation
  - Purchase summaries
  - Failed items retrieval

**Key Functions Tested:**
- `compute_session_summary()`
- `compute_run_summary()`
- `get_purchase_summaries()`
- `get_failed_items()`

---

### `test_visibility_filter.py`
**Coverage:** Conversation visibility filtering

**Test Functions:**
- Buyer sees all buyer messages
- Buyer sees visible seller messages
- Buyer hides private seller messages
- Seller sees all messages
- Empty history handling
- Mention-based visibility

**Key Functions Tested:**
- `filter_conversation()`

---

## Integration Tests

### `test_api_endpoints.py`
**Coverage:** Phase 4 API endpoints (mocked providers)

**Test Classes:**
- `TestSimulationEndpoints` - Simulation endpoints
  - Session initialization success (validates response structure: session_id, created_at, buyer_id, seller_ids, negotiation_rooms, total_rooms)
  - Session initialization validation errors (missing buyer, invalid data)
  - Session initialization with too many sellers (>10 sellers)
  - Get session success (validates session details structure)
  - Get session not found (404 error handling)
  - Delete session success (validates deletion response)
  - Delete session not found (404 error handling)
  - Get session summary (validates summary structure: session_id, buyer_name, total_items_requested, completed_purchases, failed_purchases, purchases, failed_items, total_cost_summary, negotiation_metrics)
  
- `TestNegotiationEndpoints` - Negotiation control endpoints
  - Start negotiation success (validates status="active", stream_url presence)
  - Start negotiation not found (404 error handling)
  - Start negotiation already active (409 conflict error)
  - Send message (validates message_id, timestamp, mentioned_sellers, processing flag)
  - Get negotiation state (validates room_id, item_name, status, current_round, max_rounds, conversation_history, current_offers, buyer_constraints)
  - Force decision (validates decision_type, selected_seller_id in response)
  
- `TestStreamingEndpoint` - SSE streaming endpoint
  - Stream not found (404 error handling)
  - Connected event (validates text/event-stream content-type, mocked graph completion)
  
- `TestLogsEndpoint` - Logs retrieval endpoint
  - Log not found (404 error handling for LOG_NOT_FOUND or ROOM_NOT_FOUND)
  
- `TestValidationErrors` - Request validation
  - Invalid price range (min_price_per_unit > max_price_per_unit)
  - Invalid inventory prices (selling_price < cost_price, violates price constraints)

**Endpoints Tested:**
- `POST /api/v1/simulation/initialize`
- `GET /api/v1/simulation/{session_id}`
- `DELETE /api/v1/simulation/{session_id}`
- `GET /api/v1/simulation/{session_id}/summary`
- `POST /api/v1/negotiation/{room_id}/start`
- `POST /api/v1/negotiation/{room_id}/message`
- `GET /api/v1/negotiation/{room_id}/state`
- `POST /api/v1/negotiation/{room_id}/decide`
- `GET /api/v1/negotiation/{room_id}/stream`
- `GET /api/v1/logs/{session_id}/{room_id}`

**Note:** Uses mocked LLM providers via `unittest.mock`. For live provider tests, see `live_openrouter/` and `live_lmstudio/` directories.

---

### `test_negotiation_flow.py`
**Status:** Empty file (needs implementation)

**What should be tested:**
- Full negotiation flow with mocked providers
- Message exchange between buyer and sellers
- Offer generation and validation
- Decision making

---

### `test_session_manager_phase3.py`
**Coverage:** Session manager lifecycle

**Test Class:**
- `TestSessionManager` - Session lifecycle
  - Create session
  - Get session
  - Delete session
  - Start negotiation
  - Record message
  - Record offer
  - Finalize run
  - Complete negotiation flow

**Key Functions Tested:**
- `SessionManager.create_session()`
- `SessionManager.get_session()`
- `SessionManager.delete_session()`
- `SessionManager.start_negotiation()`
- `SessionManager.record_message()`
- `SessionManager.record_offer()`
- `SessionManager.finalize_run()`

---

### `test_error_handling.py`
**Coverage:** Error handling and HTTP status codes

**Test Classes:**
- `TestProviderErrorMapping` - Provider error mapping
  - Provider timeout → 503
  - Provider unavailable → error status
  - Disabled provider → error status
  
- `TestHealthEndpointErrorStates` - Health endpoint errors
  - LLM timeout
  - Both systems down
  
- `TestEndpointResponseStructure` - Response structure validation
  - LLM status response structure
  - Health response structure
  
- `TestCORSAndMiddleware` - CORS and middleware
  - CORS headers presence
  - Root endpoint structure

---

### `test_status_endpoints.py`
**Coverage:** Status and health endpoints

**Test Classes:**
- `TestLLMStatusEndpoint` - LLM status
  - LLM available
  - LLM unavailable
  - Database down
  
- `TestHealthEndpoint` - Health checks
  - All systems up
  - Degraded LLM down
  - Degraded DB down
  - All systems down
  
- `TestRootEndpoint` - Root endpoint
  - App info response

**Endpoints Tested:**
- `GET /api/v1/llm/status`
- `GET /api/v1/health`
- `GET /`

---

### `test_cache_ttl.py`
**Coverage:** Cache and TTL behavior

**Test Classes:**
- `TestCacheStorage` - Cache storage
  - Room stored on start
  - Multiple rooms storage
  
- `TestCacheInvalidation` - Cache invalidation
  - Cache removed on finalize
  - Cache removed on session delete
  
- `TestCacheTTL` - TTL and expiration
  - Expired rooms cleanup
  - Recent rooms retention
  - Multiple expired cleanup
  - Exact boundary handling
  
- `TestCacheHitMiss` - Cache hit/miss scenarios
  - Cache hit after start
  - Cache miss after finalize
  - Cache miss after delete

**Key Components Tested:**
- `active_rooms` cache
- `SessionManager._cleanup_expired_rooms()`

---

### `test_json_logging.py`
**Coverage:** JSON log generation and schema

**Test Class:**
- `TestJSONLogging` - Log generation
  - Log generated on finalize
  - Log schema structure validation
  - Log persists after session deletion
  - Multiple runs generate separate logs
  - Log includes all messages
  - Log includes all offers
  - Log no_deal decision structure
  - Log duration calculation

**Key Components Tested:**
- Log file generation
- Log schema validation
- Log persistence

---

### `test_log_retention.py`
**Coverage:** Log retention and cleanup

**Test Class:**
- `TestLogRetention` - Log cleanup
  - Old logs deleted
  - Recent logs retained
  - Mixed old and recent cleanup
  - Empty logs directory
  - Missing session folders handling
  - Exact retention boundary
  - Nested run directories cleanup
  - Entire session deletion when all runs old
  - Cleanup with real session manager

**Key Functions Tested:**
- `SessionManager.cleanup_old_logs()`

---

### `test_agents_live_provider.py`
**Coverage:** Agents with live LLM provider (Phase 2)

**Test Functions:**
- Buyer agent generates message
- Buyer agent mentions sellers
- Seller agent generates response
- Seller agent offer within constraints
- Seller agent no offer is valid

**Note:** Requires live LLM provider, skips if unavailable

---

### `test_lm_studio_real.py`
**Coverage:** Real LM Studio instance tests

**Test Classes:**
- `TestRealLMStudio` - Real LM Studio connection
  - Ping real LM Studio
  - Generate with real LM Studio
  - Stream with real LM Studio
  - Generate with system prompt
  
- `TestLMStudioErrorHandling` - Error handling
  - Ping wrong port
  - Generate wrong endpoint

**Note:** Requires LM Studio running on localhost:1234, skips if unavailable

---

### `test_negotiation_flow_live.py`
**Coverage:** Negotiation graph with live provider (Phase 2)

**Test Functions:**
- Negotiation graph emits events
- Buyer message events
- Seller response events
- Negotiation completes
- Parallel sellers handling
- Error handling gracefully

**Note:** Requires live LLM provider, skips if unavailable

---

### Live Provider Test Suites (Phase 4)

Live provider tests validate Phase 4 API endpoints and SSE streaming with real inference providers. These tests are skipped by default unless explicitly enabled via environment variables.

#### OpenRouter Live Tests (`tests/integration/live_openrouter/`)

**Coverage:** Phase 4 endpoints and SSE with real OpenRouter provider

**Test Files:**

- `test_phase4_openrouter_endpoints.py` - API endpoint tests with OpenRouter
  - `TestOpenRouterSimulationEndpoints` - Simulation endpoints
    - Initialize session success (validates response structure)
    - Initialize session validation error (invalid price range)
    - Get session success
    - Get session not found
    - Delete session success
    - Delete session not found (idempotent)
    - Get session summary (validates structure, content may be empty)
  - `TestOpenRouterNegotiationEndpoints` - Negotiation control endpoints
    - Start negotiation success (validates status="active", stream_url)
    - Start negotiation not found
    - Start negotiation already active (409 conflict)
    - Send message (validates message_id, timestamp, mentioned_sellers, processing)
    - Get negotiation state (validates full state structure)
    - Force decision (validates decision_type, selected_seller_id)
  - `TestOpenRouterLogsEndpoint` - Logs retrieval
    - Get log not found (404 error handling)
  
- `test_phase4_openrouter_streaming.py` - SSE streaming tests with OpenRouter
  - `TestOpenRouterStreaming` - SSE streaming validation
    - Stream connected event (validates first event is "connected", text/event-stream content-type)
    - Stream event ordering (validates connected event first, at least one negotiation event, event schema)
    - Stream heartbeat interval (validates heartbeat events within 15s ± 5s tolerance)
    - Stream clean close (validates stream closes after negotiation_complete)
  
- `test_phase4_openrouter_perf.py` - Performance smoke tests
  - `TestOpenRouterPerformance` - Performance metrics
    - API latency median (measures initialize, start, total latencies, warns if >5s)
    - Concurrent sessions (2-3 parallel sessions, validates completion, warns if >30s)
    - SSE connect time (measures connection establishment, warns if >2s)
    - SSE first event time (measures time to first event, warns if >5s)

**Environment Setup:**
```bash
# Required environment variables
RUN_LIVE_PROVIDER_TESTS=true
LLM_PROVIDER=openrouter
LLM_ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_TEST_MODEL=google/gemini-2.5-flash-lite  # Optional, defaults to config
```

**Running Tests:**
```bash
# Run all OpenRouter Phase 4 tests (excluding perf)
pytest tests/integration/live_openrouter -m "phase4 and integration and requires_openrouter and not perf" -v

# Run performance tests explicitly
pytest tests/integration/live_openrouter/test_phase4_openrouter_perf.py -m "perf and requires_openrouter" -v

# Run all OpenRouter tests
pytest tests/integration/live_openrouter -m "phase4 and requires_openrouter" -v

# Run specific test file
pytest tests/integration/live_openrouter/test_phase4_openrouter_endpoints.py -m "requires_openrouter" -v
pytest tests/integration/live_openrouter/test_phase4_openrouter_streaming.py -m "requires_openrouter" -v
```

**Note:** 
- Tests automatically skip if OpenRouter is not configured or `RUN_LIVE_PROVIDER_TESTS` is not set to `true`
- All tests are marked with `@pytest.mark.slow` due to live provider latency
- Performance tests use non-fatal assertions (warnings) for latency thresholds

---

#### LM Studio Live Tests (`tests/integration/live_lmstudio/`)

**Coverage:** Phase 4 endpoints and SSE with real LM Studio provider

**Test Files:**

- `test_phase4_lmstudio_endpoints.py` - API endpoint tests with LM Studio
  - `TestLMStudioSimulationEndpoints` - Simulation endpoints (async)
    - Initialize session success (validates response structure)
    - Initialize session validation error (invalid price range)
    - Get session success
    - Get session not found
    - Delete session success
    - Delete session not found (idempotent)
    - Get session summary (validates structure, content may be empty)
  - `TestLMStudioNegotiationEndpoints` - Negotiation control endpoints (async)
    - Start negotiation success (validates status="active", stream_url)
    - Start negotiation not found
    - Start negotiation already active (409 conflict)
    - Send message (validates message_id, timestamp, mentioned_sellers, processing)
    - Get negotiation state (validates full state structure)
    - Force decision (validates decision_type, selected_seller_id)
  - `TestLMStudioLogsEndpoint` - Logs retrieval (async)
    - Get log not found (404 error handling)
  
- `test_phase4_lmstudio_streaming.py` - SSE streaming tests with LM Studio
  - `TestLMStudioStreaming` - SSE streaming validation (async)
    - Stream connected event (validates first event is "connected", text/event-stream content-type)
    - Stream event ordering (validates connected event first, at least one negotiation event, event schema)
    - Stream heartbeat interval (validates heartbeat events within 15s ± 5s tolerance)
    - Stream clean close (validates stream closes after negotiation_complete)

**Environment Setup:**
```bash
# Required environment variables
RUN_LIVE_PROVIDER_TESTS=true
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_DEFAULT_MODEL=qwen/qwen3-1.7b  # Optional, defaults to config

# Ensure LM Studio server is running on localhost:1234
```

**Running Tests:**
```bash
# Run all LM Studio Phase 4 tests
pytest tests/integration/live_lmstudio -m "phase4 and integration and requires_lm_studio" -v

# Run specific test file
pytest tests/integration/live_lmstudio/test_phase4_lmstudio_endpoints.py -m "requires_lm_studio" -v
pytest tests/integration/live_lmstudio/test_phase4_lmstudio_streaming.py -m "requires_lm_studio" -v
```

**Note:** 
- Tests automatically skip if LM Studio server is not reachable or `RUN_LIVE_PROVIDER_TESTS` is not set to `true`
- All tests are marked with `@pytest.mark.slow` due to live provider latency
- Tests use `@pytest.mark.asyncio` for async test execution
- Default model: `qwen/qwen3-1.7b` (configurable via `LM_STUDIO_DEFAULT_MODEL` env var)

---

## Manual Tests

Manual tests are located in `tests/manual/` and require special setup or live providers:

- `test_both_providers.py` - Tests both LM Studio and OpenRouter
- `test_database_stress.py` - Database stress testing
- `test_lm_studio_inference.py` - LM Studio inference testing
- `test_openrouter_inference.py` - OpenRouter inference testing
- `test_openrouter_negotiation.py` - OpenRouter negotiation testing
- `test_phase3_workflow.py` - Phase 3 workflow testing
- `verify_setup.py` - Setup verification

---

## Test Fixtures and Utilities

### `conftest.py`
**Shared Fixtures:**
- `reset_provider_singleton` - Resets provider between tests
- `mock_settings` - Mock application settings
- `event_loop` - Event loop for async tests
- `mock_token_chunks` - Mock token chunks for streaming

**Test Constants:**
- `MOCK_LLM_RESPONSE` - Mock LLM response structure
- `MOCK_STREAMING_CHUNKS` - Mock streaming chunks
- `MOCK_MODELS_RESPONSE` - Mock models response

**Pytest Markers:**
- `phase1` - Phase 1 tests (Inference Setup)
- `phase2` - Phase 2 tests (Complete Agent Logic)
- `phase3` - Phase 3 tests (Database & Orchestration)
- `phase4` - Phase 4 tests (FastAPI Endpoints & SSE)
- `unit` - Unit tests
- `integration` - Integration tests
- `e2e` - End-to-end tests
- `slow` - Slow tests
- `requires_lm_studio` - Requires LM Studio instance
- `requires_openrouter` - Requires OpenRouter API key and enabled provider
- `perf` - Performance tests that measure latency and throughput

### `fixtures/mock_llm.py`
**Status:** Placeholder (not implemented)

### `fixtures/sample_configs.py`
**Status:** Empty file

---

## Test Coverage Summary

### Components with Comprehensive Coverage

1. **LLM Providers** ✅
   - Provider factory
   - LM Studio provider (all methods, edge cases)
   - OpenRouter provider stub
   - Error handling

2. **Decision Engine** ✅
   - Decision validation
   - Best offer selection
   - Cost computation

3. **Message Routing** ✅
   - Mention parsing
   - Edge cases

4. **Prompts** ✅
   - Buyer prompt rendering
   - Seller prompt rendering

5. **Database Schema** ✅
   - CHECK constraints
   - UNIQUE constraints
   - Foreign key cascades
   - Indexes

6. **Seller Selection** ✅
   - Inventory matching
   - Quantity validation
   - Price matching

7. **Streaming** ✅
   - Chunk coalescing
   - Bounded streaming
   - Edge cases

8. **Summary Service** ✅
   - Session summaries
   - Run summaries
   - Purchase summaries
   - Failed items

9. **Visibility Filter** ✅
   - Buyer visibility
   - Seller visibility
   - Mention-based visibility

10. **Session Manager** ✅
    - Session lifecycle
    - Message recording
    - Offer recording
    - Run finalization

11. **API Endpoints** ✅
    - Simulation endpoints (initialize, get, delete, summary)
    - Negotiation endpoints (start, message, state, decide)
    - Streaming endpoint (SSE)
    - Status endpoints (health, LLM status, root)
    - Logs endpoint
    - Request validation
    - Error handling (404, 409, 400, 503)
    - Live provider endpoint tests (OpenRouter, LM Studio)
    - Live provider SSE streaming tests (OpenRouter, LM Studio)
    - Performance smoke tests (OpenRouter)

12. **Caching** ✅
    - Cache storage
    - Cache invalidation
    - TTL expiration

13. **Logging** ✅
    - JSON log generation
    - Log schema validation
    - Log retention

### Components Needing More Coverage

1. **Agents** ⚠️
   - `test_agents.py` is empty
   - Needs unit tests for BuyerAgent and SellerAgent
   - Needs tests for agent decision logic

2. **Negotiation Flow** ⚠️
   - `test_negotiation_flow.py` is empty
   - Needs integration tests for full negotiation flow

3. **Graph Builder** ⚠️
   - Only tested with live provider
   - Needs mocked provider tests

4. **Error Handling** ⚠️
   - Some error scenarios covered
   - Could use more edge case coverage

---

## Test Markers and Phases

### Phase Markers

- **`@pytest.mark.phase1`** - Inference Setup (LM Studio + OpenRouter Stub)
- **`@pytest.mark.phase2`** - Complete Agent Logic (Buyer/Seller + Graph)
- **`@pytest.mark.phase3`** - Database & Orchestration (Sessions, Runs, State)
- **`@pytest.mark.phase4`** - FastAPI Endpoints & SSE

### Test Type Markers

- **`@pytest.mark.unit`** - Unit tests (isolated components)
- **`@pytest.mark.integration`** - Integration tests (multiple components)
- **`@pytest.mark.e2e`** - End-to-end tests (full system)
- **`@pytest.mark.slow`** - Tests that take significant time
- **`@pytest.mark.requires_lm_studio`** - Requires running LM Studio instance

### Running Tests by Marker

```bash
# Run only Phase 1 tests
pytest -m phase1

# Run only unit tests
pytest -m unit

# Run integration tests excluding slow ones
pytest -m integration -m "not slow"

# Run Phase 3 tests
pytest -m phase3

# Run Phase 4 live provider tests (OpenRouter)
pytest tests/integration/live_openrouter -m "phase4 and requires_openrouter and not perf" -v

# Run Phase 4 live provider tests (LM Studio)
pytest tests/integration/live_lmstudio -m "phase4 and requires_lm_studio" -v

# Run performance tests
pytest -m perf
```

---

## Best Practices for Adding New Tests

1. **Check this document first** - Avoid duplicating existing test coverage
2. **Use appropriate markers** - Mark tests with phase and type
3. **Follow naming conventions** - Use descriptive test names
4. **Use fixtures** - Leverage `conftest.py` fixtures
5. **Test edge cases** - Include boundary conditions and error cases
6. **Mock external dependencies** - Use mocks for LLM providers in unit tests
7. **Document test purpose** - Add docstrings explaining WHAT, WHY, HOW
8. **Keep tests isolated** - Each test should be independent
9. **Use database fixtures** - Use `db_session` fixture for database tests
10. **Skip when needed** - Use `pytest.skip()` for tests requiring unavailable resources

---

## Notes for AI Agents

When creating new tests:

1. **Review existing tests** - Check if similar functionality is already tested
2. **Fill gaps** - Focus on components marked as needing more coverage
3. **Don't duplicate** - Avoid creating tests that cover the same scenarios
4. **Extend coverage** - Add tests for edge cases not yet covered
5. **Follow patterns** - Match the structure and style of existing tests
6. **Update this doc** - When adding significant new test coverage, update this document

---

## Last Updated

This document was generated by analyzing all test files in the codebase. Last updated: 2024

