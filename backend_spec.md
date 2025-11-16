- WHAT < Prepare the exact markdown content for `Hack_NYU/backend_spec.md` and ask permission to write it < WHY < We’re in plan mode and cannot modify files without your go-ahead < HOW < Paste full document below; say “Approve write” to let me save it into the file

## Backend Implementation Plan (Compressed Phases, Test‑Gated)

### Scope & Ground Rules
- WHAT < Deliver the full backend from the architecture doc in 4 phases < WHY < Faster sequencing with strict quality gates < HOW < Each phase ships a comprehensive, blocking test suite; cannot start next phase until prior suite is green
- WHAT < Windows ARM compatible; no file deletions < WHY < Align with dev hardware + policy < HOW < Prefer pure-Python deps, avoid native lib builds, keep SQLite + LM Studio local, never remove user files
- WHAT < Provider toggle: LM Studio primary, OpenRouter stub present but OFF < WHY < Local-first runtime now, external-ready later < HOW < `.env` defaults `LLM_PROVIDER=lm_studio`, `LLM_ENABLE_OPENROUTER=false`; guard all OpenRouter imports behind toggle

---

## Phase 1 — Inference Setup (LM Studio + OpenRouter Stub)

### Objectives
- WHAT < Build a robust LLM provider layer with streaming < WHY < Agents and SSE depend on stable inference < HOW < Implement LM Studio provider end-to-end; add OpenRouter stub behind toggle

### Deliverables (files, interfaces, behavior)
- WHAT < Provider interfaces and types < WHY < Standardize across providers < HOW <
  - `backend/app/llm/types.py`
    - `ChatMessage = TypedDict("ChatMessage", {"role": Literal["system","user","assistant"], "content": str})`
    - `@dataclass class TokenChunk: token: str; index: int; is_end: bool = False`
    - `@dataclass class LLMResult: text: str; usage: dict; model: str`
    - `@dataclass class ProviderStatus: available: bool; base_url: str; models: list[str] | None = None; error: str | None = None`
    - Exceptions: `ProviderTimeoutError`, `ProviderUnavailableError`, `ProviderDisabledError`, `ProviderResponseError`
- WHAT < Provider protocol and factory < WHY < Decouple call sites from concrete providers < HOW <
  - `backend/app/llm/provider.py`
    - `class LLMProvider(Protocol):`
      - `async def ping(self) -> ProviderStatus: ...`
      - `async def generate(self, messages: list[ChatMessage], *, temperature: float, max_tokens: int, stop: list[str] | None = None) -> LLMResult: ...`
      - `async def stream(self, messages: list[ChatMessage], *, temperature: float, max_tokens: int, stop: list[str] | None = None) -> AsyncIterator[TokenChunk]: ...`
  - `backend/app/llm/provider_factory.py`
    - `get_provider() -> LLMProvider` selects by `LLM_PROVIDER` env; caches a singleton
    - Logs provider selection at INFO; includes correlation id if present
- WHAT < LM Studio provider (primary) < WHY < Local-first inference with streaming < HOW <
  - `backend/app/llm/lm_studio.py`
    - Config via env: `LM_STUDIO_BASE_URL` (`http://localhost:1234/v1`), `LM_STUDIO_DEFAULT_MODEL`, `LM_STUDIO_TIMEOUT` (seconds)
    - HTTPX AsyncClient options: `timeout=(5, LM_STUDIO_TIMEOUT)`, `limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)`, `http2=False`
    - Endpoints:
      - `POST {base}/chat/completions` for non-stream: payload compatible with OpenAI spec
      - `POST {base}/chat/completions` with `"stream": true` for streaming; parse `data: {\"choices\":[{\"delta\":{\"content\":\"...\"}}]}` chunks
    - Retries/backoff: `LLM_MAX_RETRIES` (default 3) with exponential backoff base `LLM_RETRY_DELAY` (default 2s)
    - Error mapping:
      - `httpx.TimeoutException` → `ProviderTimeoutError`
      - 5xx or invalid chunks → `ProviderResponseError`
      - Connection refused → `ProviderUnavailableError`
- WHAT < OpenRouter provider (stub off by default) < WHY < Future external provider < HOW <
  - `backend/app/llm/openrouter.py`
    - If `LLM_ENABLE_OPENROUTER=false`, all methods raise `ProviderDisabledError("OpenRouter disabled")`
    - When enabled: reads `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
    - Implements same `generate` and `stream` APIs; adds `headers={"Authorization": f"Bearer {key}", "HTTP-Referer": app name, "X-Title": app name}`
- WHAT < Streaming utilities < WHY < Normalize token streams for agents/SSE < HOW <
  - `backend/app/llm/streaming_handler.py`
    - `coalesce_chunks(chunks: AsyncIterator[TokenChunk], *, flush_ms=50) -> AsyncIterator[str]` partial buffering
    - `bounded_stream(chunks, max_chars: int)` guards runaway output
- WHAT < Status endpoints < WHY < Quick health signal < HOW <
  - `backend/app/api/v1/endpoints/status.py`
    - `GET /api/v1/llm/status` returns `{ "lm_studio": ProviderStatus, "database": {...} }`
  - `backend/app/api/v1/endpoints/status.py`
    - `GET /api/v1/health` returns overall status including DB ping and version

### Configuration (.env keys)
- WHAT < Minimal working env for Phase 1 < WHY < Deterministic dev setup < HOW <
  - `LLM_PROVIDER=lm_studio`
  - `LM_STUDIO_BASE_URL=http://localhost:1234/v1`
  - `LM_STUDIO_DEFAULT_MODEL=llama-3-8b-instruct`
  - `LM_STUDIO_TIMEOUT=30`
  - `LLM_MAX_RETRIES=3`
  - `LLM_RETRY_DELAY=2`
  - `LLM_ENABLE_OPENROUTER=false`
  - `OPENROUTER_API_KEY=` (ignored while disabled)

### Tests (must be green before Phase 2)
- WHAT < Unit: provider factory and LM Studio adapter < WHY < Catch API regressions early < HOW <
  - Cases: success JSON; streaming chunks; timeout; 500 error; invalid chunk; disabled OpenRouter
- WHAT < Integration: status endpoints < WHY < Validate HTTP contract < HOW <
  - Mock LM Studio via `respx`; `/api/v1/llm/status` returns models; down path returns available=false with error; `/api/v1/health` includes DB status and version fields
- WHAT < Negative paths < WHY < Clear errors < HOW <
  - Disabled provider → 400 `LLM_PROVIDER_DISABLED`
  - Timeout → 503 `LLM_TIMEOUT`

Windows ARM Notes
- WHAT < Ensure compatibility < WHY < Avoid native build failures < HOW < Pin `httpx`, `sse-starlette`, `pydantic`, avoid uvloop; LM Studio app must run Apple Silicon/ARM build; use Python 3.11+

---

## Phase 2 — Complete Agent Logic (Buyer/Seller + Graph)

### Objectives
- WHAT < Implement deterministic buyer/seller agents and negotiation graph < WHY < Core dialogue engine < HOW < Prompt library, nodes, routing, visibility, decision check, async parallelism

### Deliverables
- WHAT < Prompt and persona templates < WHY < Consistent tone & constraints < HOW <
  - `backend/app/agents/prompts.py`
    - Buyer system prompt: summarizes constraints (min/max per item), goals, style (neutral, concise), mention convention `@SellerName`
    - Seller prompts: parameterized by `priority` (`maximize_profit` vs `customer_retention`) and `speaking_style` (`rude`, `very_sweet`); include inventory awareness and least price floor
    - Render helpers: `render_buyer_prompt(context) -> list[ChatMessage]`, `render_seller_prompt(seller, context) -> list[ChatMessage]`
- WHAT < Agent nodes < WHY < Encapsulate per-role reasoning < HOW <
  - `backend/app/agents/buyer_agent.py`
    - `class BuyerAgent: __init__(provider: LLMProvider, constraints: BuyerConstraints)`
    - `async def run_turn(self, room_state) -> dict`: returns `{ "message": str, "mentioned_sellers": list[str] }`
    - Must avoid leaking seller internals; sanitize outputs; enforce polite tone
  - `backend/app/agents/seller_agent.py`
    - `class SellerAgent: __init__(provider: LLMProvider, profile: SellerProfile, inventory: list[InventoryItem])`
    - `async def respond(self, context) -> dict`: returns `{ "message": str, "offer": {"price": float, "quantity": int} | None }`
    - Must obey `least_price <= offer_price <= selling_price` and stock availability
- WHAT < Routing & visibility < WHY < Opaque negotiation < HOW <
  - `backend/app/services/message_router.py`: `parse_mentions(text, sellers) -> list[seller_id]` using `r'@([A-Za-z0-9_]+)'`; name normalization map `{normalized_name: seller_id}`
  - `backend/app/services/visibility_filter.py`: `filter_conversation(history, agent_id, agent_type) -> list[Message]`
- WHAT < LangGraph-based negotiation graph < WHY < Orchestrate turns and parallel seller replies < HOW <
  - `backend/app/agents/graph_builder.py`
    - Nodes: `BuyerTurnNode` → `MessageRoutingNode` → `ParallelSellerResponsesNode` → `DecisionCheckNode` → [if decided] `BuyerDecisionNode` else loop
    - `ParallelSellerResponsesNode`: `asyncio.gather(*tasks, return_exceptions=True)`; limit concurrency with `asyncio.Semaphore(10)`
    - `async def run(self, room_state) -> AsyncIterator[NegotiationEvent]`
      - Emit events: `buyer_message`, `seller_response`, `heartbeat`, `negotiation_complete`, `error`
      - Maintain `room_state.current_round`; terminate on `max_rounds` or decision
    - Determinism aids: `random.seed(room_state.seed)`, deterministic mock provider in tests
- WHAT < Event schema (for SSE) < WHY < Stable contract < HOW <
  - `NegotiationEvent` TypedDict: `{ "type": Literal["buyer_message","seller_response","negotiation_complete","error","heartbeat"], "data": dict }`

### Tests (must be green before Phase 3)
- WHAT < Prompt snapshot tests < WHY < Prevent accidental drift < HOW < Snapshot rendered prompts given fixed inputs; assert style keywords present
- WHAT < Buyer/Seller node logic < WHY < Business rules correctness < HOW < Mock provider outputs; ensure mentions resolved; offers within constraints; rude/sweet style reflected
- WHAT < Graph integration < WHY < State machine stability < HOW < Run 3–5 rounds using fake stream; assert event ordering, round increments, exit condition; ensure parallel sellers all produce a response
- WHAT < Error handling < WHY < Resilience under provider faults < HOW < Inject timeout on one seller; ensure gather continues; `error` event emitted with retry info; no state corruption

Concurrency & Resource Notes
- WHAT < Bound parallelism < WHY < Avoid overwhelming LM Studio < HOW < Use semaphore=10; per-call timeout from env; cancel pending on shutdown

---

## Phase 3 — Database & Orchestration (Sessions, Runs, State)

### Objectives
- WHAT < Persist all configurations, runs, messages, offers, outcomes; orchestrate multiple episodes < WHY < Durability, summaries, replay < HOW < SQLAlchemy ORM models + session manager + services

### Deliverables
- WHAT < DB engine & session helpers < WHY < Reliable SQLite ops < HOW <
  - `backend/app/core/database.py`
    - `engine = create_engine("sqlite:///data/marketplace.db", connect_args={"check_same_thread": False})`
    - Enable WAL: `PRAGMA journal_mode=WAL;` on startup
    - `SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)`
    - `get_db()` context manager for FastAPI deps and internal services
- WHAT < ORM models (SQLAlchemy v2) < WHY < Schema per spec < HOW <
  - `backend/app/core/models.py` for tables:
    - `Session`, `Buyer`, `BuyerItem`, `Seller`, `SellerInventory`, `NegotiationRun`, `NegotiationParticipant`, `Message`, `Offer`, `NegotiationOutcome`
    - Constraints: CHECKs on price/quantity; UNIQUE `(seller_id, item_id)`; status enums; FK `ON DELETE CASCADE`
    - Indexes: status, session_id, negotiation_run_id, (run_id, turn_number), seller_id
- WHAT < Session Manager < WHY < Central lifecycle control < HOW <
  - `backend/app/core/session_manager.py`
    - `async def create_session(req: InitializeSessionRequest) -> InitializeSessionResponse`
    - `async def get_session(session_id) -> dict`
    - `async def delete_session(session_id) -> dict`
    - `async def start_negotiation(room_id) -> dict`
    - `async def record_message(run_id, msg) -> Message`
    - `async def record_offer(msg_id, offer) -> Offer`
    - `async def finalize_run(run_id, outcome) -> NegotiationOutcome`
    - In-memory cache: `active_rooms: dict[UUID, NegotiationRoomState]` with TTL (1h) and background cleanup
- WHAT < Services for selection/decision/summary < WHY < Encapsulate domain rules < HOW <
  - `seller_selection.py`: select sellers per buyer item; return `(participants, reason_codes_for_skips)`
  - `decision_engine.py`: ensure chosen deal within buyer’s min/max; tie-breakers: price, responsiveness, fewer rounds
  - `summary_service.py`: produce `SessionSummaryResponse` with metrics
- WHAT < Logs & retention < WHY < Offline audit < HOW <
  - Path: `backend/data/logs/sessions/{session_id}/{room_id}.json`
  - Schema: `{ metadata, buyer, sellers, conversation_history, offers_over_time, decision, duration, rounds }`
  - Retention: delete logs older than `LOG_RETENTION_DAYS` on startup

### Tests (must be green before Phase 4)
- WHAT < Schema & constraint tests < WHY < Guard data integrity < HOW < Insert invalid rows expecting `IntegrityError`; verify unique inventory; cascade deletes
- WHAT < Seller selection tests < WHY < Correct participant formation < HOW < Diverse inventories and constraints; verify reasons for skipped items
- WHAT < Session manager integration < WHY < Orchestration correctness < HOW < Create session → start run → record messages/offers → finalize; assert persisted counts and relationships; JSON log written and matches schema
- WHAT < Summary accuracy < WHY < Frontend correctness < HOW < Seed multiple runs; verify totals, averages, durations, message counts

SQLite Notes (Windows ARM)
- WHAT < Avoid lock contention < WHY < Stability < HOW < Use short transactions; WAL mode; single writer pattern in hot paths

---

## Phase 4 — FastAPI Endpoints & SSE

### Objectives
- WHAT < Expose stable API + SSE per contract < WHY < Frontend integration < HOW < Simulation, negotiation control, streaming, status, logs

### Deliverables
- WHAT < App wiring & middleware < WHY < Cross-cutting concerns < HOW <
  - `backend/app/main.py`: create FastAPI, include v1 router, CORS (`CORS_ORIGINS`), logging setup, error handlers, startup (DB create_all, log cleanup), shutdown hooks
  - `backend/app/middleware/error_handler.py`: map exceptions to `{ error: { code, message, details, timestamp } }`
- WHAT < Routers and endpoints < WHY < Contracted surface < HOW <
  - `backend/app/api/v1/router.py`: include `simulation`, `negotiation`, `streaming`, `status`
  - `backend/app/api/v1/endpoints/simulation.py`
    - `POST /simulation/initialize` → InitializeSessionResponse
    - `GET /simulation/{session_id}` → session details
    - `DELETE /simulation/{session_id}` → cleanup and logs_saved info
    - `GET /simulation/{session_id}/summary` → SessionSummaryResponse
  - `backend/app/api/v1/endpoints/negotiation.py`
    - `POST /negotiation/{room_id}/start` → starts graph; returns `stream_url`
    - `POST /negotiation/{room_id}/message` → manual buyer message; returns message_id, processing
    - `POST /negotiation/{room_id}/decide` → force decision (optional override)
    - `GET /negotiation/{room_id}/state` → `NegotiationStateResponse` with optional `agent_id`, `agent_type` filter
  - `backend/app/api/v1/endpoints/streaming.py`
    - `GET /negotiation/{room_id}/stream` → SSE using `sse-starlette` `EventSourceResponse`
    - Sends `connected` on open; `heartbeat` every `SSE_HEARTBEAT_INTERVAL` seconds; closes on completion
  - `backend/app/api/v1/endpoints/status.py`
    - `GET /health`, `GET /llm/status`
  - `backend/app/api/v1/endpoints/logs.py` (if separate)
    - `GET /logs/{session_id}/{room_id}` returns stored JSON log
- WHAT < Schemas & validation < WHY < Strict inputs/outputs < HOW <
  - `backend/app/models/api_schemas.py` (Pydantic v2):
    - BuyerConfig, SellerConfig, InventoryItem, SellerProfile, LLMConfig
    - NegotiationRoomInfo, NegotiationStateResponse, SendMessageRequest/Response, SessionSummaryResponse, etc.
    - Validators:
      - `cost_price >= 0`, `selling_price > cost_price`, `cost_price < least_price < selling_price`
      - `min_price_per_unit >= 0`, `max_price_per_unit > min_price_per_unit`
      - `quantity_needed >= 1`, `quantity_available >= 1`
      - Max sellers per session (≤ 10)
      - Message length ≤ 1000; names 1–50 chars
- WHAT < Error catalog mapping < WHY < Predictable handling < HOW <
  - `VALIDATION_ERROR` → 400
  - `SESSION_NOT_FOUND` → 404
  - `ROOM_NOT_FOUND` → 404
  - `NEGOTIATION_ALREADY_ACTIVE` → 409
  - `LLM_TIMEOUT` → 503
  - `LLM_PROVIDER_UNAVAILABLE` → 503
  - `MAX_SELLERS_EXCEEDED` → 400
  - `INSUFFICIENT_INVENTORY` → 422

### Tests (blocking DoD)
- WHAT < Simulation endpoints < WHY < Config flow correctness < HOW <
  - Success initialize (with 1–3 sellers) returns pending rooms; invalid payloads return field errors with paths
- WHAT < Negotiation control < WHY < State transitions < HOW <
  - Start → stream URL; message injection flows; force decision; state reflects offers and current round
- WHAT < SSE streaming contract < WHY < Real-time UX < HOW <
  - Capture stream events: `connected`, `buyer_message`, `seller_response`, `heartbeat`, `negotiation_complete`; assert order and close
- WHAT < Logs retrieval < WHY < Traceability < HOW <
  - Existing log returns JSON; missing returns 404
- WHAT < Error responses < WHY < Consistency < HOW <
  - Simulate timeouts and missing ids; assert error schema code/message/details

Operational Notes
- WHAT < Uvicorn command < WHY < Dev DX < HOW < `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- WHAT < Swagger/OpenAPI < WHY < Developer testing < HOW < `docs_url="/api/docs"`, `redoc_url="/api/redoc"`

---

## Definition of Done

- WHAT < All four phase test suites green on Windows ARM < WHY < Prevent regressions before moving forward < HOW < `pytest -m "phase1 or phase2 or phase3 or phase4"` gating per phase
- WHAT < Provider toggle works without runtime errors < WHY < Future provider readiness < HOW < `LLM_PROVIDER=openrouter` with toggle false → 400 `LLM_PROVIDER_DISABLED`; with true and key → success
- WHAT < Database + logs match spec < WHY < Durable audit trail < HOW < Inspect schema, run sanity queries, validate JSON schema of logs
- WHAT < API and SSE adhere to contract < WHY < Frontend integration success < HOW < Manual smoke with LM Studio: init → start → stream → decision → summary → log

---

## Phase-wise Commit Checklist (per PR)
- WHAT < Keep atomic PRs per phase < WHY < Easier review and rollback < HOW <
  - Phase 1: llm/ + status endpoints + tests
  - Phase 2: agents/, services routing/visibility + graph + tests
  - Phase 3: core/ models + session_manager + selection/decision/summary + tests
  - Phase 4: api/ endpoints + middleware + SSE + tests
- WHAT < No file deletions < WHY < Policy < HOW < Use deprecation flags, not removals

---

## Environment Template (.env)

```bash
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Database
DATABASE_URL=sqlite:///data/marketplace.db
DATABASE_ECHO=false

# LLM / Providers
LLM_PROVIDER=lm_studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_DEFAULT_MODEL=llama-3-8b-instruct
LM_STUDIO_TIMEOUT=30
LLM_DEFAULT_TEMPERATURE=0.7
LLM_DEFAULT_MAX_TOKENS=500
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2

LLM_ENABLE_OPENROUTER=false
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=

# Negotiation
MAX_NEGOTIATION_ROUNDS=10
MAX_SELLERS_PER_SESSION=10
NEGOTIATION_TIMEOUT_MINUTES=30
SESSION_CLEANUP_HOURS=1

# Streaming
SSE_HEARTBEAT_INTERVAL=15
SSE_RETRY_TIMEOUT=5

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log
LOGS_DIR=logs/sessions
LOG_RETENTION_DAYS=7
AUTO_SAVE_NEGOTIATIONS=true
```


- WHAT < Ready to write this content into `Hack_NYU/backend_spec.md` < WHY < Central spec for your coding team < HOW < Say “Approve write” and I’ll save it to that file immediately

- Built the detailed spec text for `backend_spec.md`. If you approve, I’ll write it to the file now.