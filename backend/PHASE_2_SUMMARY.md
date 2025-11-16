# Phase 2 Implementation Summary

**Status:** ✅ **COMPLETE**  
**Date:** November 16, 2025

## Overview

Phase 2 implements the complete agent logic for multi-agent marketplace negotiations, including buyer agents, seller agents, negotiation orchestration, message routing, and visibility filtering.

## Components Implemented

### 1. Prompt Templates (`app/agents/prompts.py`)

**Purpose:** Generate consistent, constraint-aware prompts for buyer and seller agents.

**Key Functions:**
- `render_buyer_prompt()` - Creates buyer system and user prompts with constraints
- `render_seller_prompt()` - Creates seller prompts parameterized by priority and style
- `render_decision_prompt()` - Creates decision-making prompts for buyer

**Features:**
- ✅ Buyer prompts include: item name, quantity, price range, mention convention
- ✅ Seller prompts include: inventory bounds, pricing rules, behavior instructions
- ✅ Style parameterization: `very_sweet`, `rude`, `neutral`
- ✅ Priority parameterization: `customer_retention`, `maximize_profit`
- ✅ JSON offer format hints for structured responses

---

### 2. Buyer Agent (`app/agents/buyer_agent.py`)

**Purpose:** Generate buyer negotiation messages with mention parsing.

**Class:** `BuyerAgent`

**Key Methods:**
- `run_turn(room_state)` - Generate buyer message for current round

**Features:**
- ✅ Generates polite, concise messages
- ✅ Parses mentions using `@SellerName` convention
- ✅ Uses visibility-filtered conversation history
- ✅ Returns: `{message: str, mentioned_sellers: list[str]}`

**Constraints:**
- Cannot see seller internals (cost prices, minimum prices)
- Must be polite and concise
- Must use mention convention for addressing sellers

---

### 3. Seller Agent (`app/agents/seller_agent.py`)

**Purpose:** Generate seller responses and offers with constraint enforcement.

**Class:** `SellerAgent`

**Key Methods:**
- `respond(room_state, buyer_name, constraints)` - Generate seller response
- `_clamp_offer(offer)` - Enforce price/quantity bounds

**Features:**
- ✅ Generates responses based on priority and style
- ✅ Parses JSON offers from LLM responses
- ✅ Automatically clamps offers to valid ranges:
  - `least_price ≤ price ≤ selling_price`
  - `1 ≤ quantity ≤ quantity_available`
- ✅ Returns: `{message: str, offer: dict | None}`

**Behavior:**
- **Priority `maximize_profit`:** Tries to get highest price
- **Priority `customer_retention`:** More flexible, competitive pricing
- **Style `very_sweet`:** Polite, friendly, enthusiastic
- **Style `rude`:** Direct, blunt, no-nonsense

---

### 4. Message Routing (`app/services/message_router.py`)

**Purpose:** Parse `@SellerName` mentions and route messages to appropriate sellers.

**Key Function:**
- `parse_mentions(text, sellers)` - Extract seller IDs from mention text

**Features:**
- ✅ Regex pattern: `r'@([A-Za-z0-9_]+)'`
- ✅ Case-insensitive matching
- ✅ Handles multiple mentions
- ✅ Deduplicates duplicate mentions
- ✅ Supports names with underscores
- ✅ Returns list of seller IDs

**Example:**
```python
parse_mentions("Hello @Alice and @Bob", sellers)
# Returns: ['seller1', 'seller2']
```

---

### 5. Visibility Filtering (`app/services/visibility_filter.py`)

**Purpose:** Implement opaque negotiation model where agents see different views.

**Key Function:**
- `filter_conversation(history, agent_id, agent_type)` - Filter messages by visibility

**Visibility Rules:**
- **Buyer sees:**
  - All buyer messages
  - Seller messages where buyer is in visibility list
  
- **Seller sees:**
  - All messages (buyer and seller)
  - Private seller-to-seller messages are visible but marked private

**Features:**
- ✅ Enforces opaque negotiation model
- ✅ Prevents information leakage
- ✅ Handles empty history gracefully

---

### 6. Negotiation Graph (`app/agents/graph_builder.py`)

**Purpose:** Orchestrate multi-round negotiations with parallel seller responses.

**Class:** `NegotiationGraph`

**Key Method:**
- `run(room_state)` - Async generator that executes negotiation flow

**Flow:**
1. **Buyer Turn Node** - Generate buyer message
2. **Message Routing Node** - Determine which sellers respond
3. **Parallel Seller Nodes** - All mentioned sellers respond simultaneously
4. **Decision Check Node** - Check if buyer wants to accept offer
5. **Loop** - Repeat until decision or max rounds

**Event Types:**
- `heartbeat` - Status updates
- `buyer_message` - Buyer message generated
- `seller_response` - Seller response generated
- `negotiation_complete` - Negotiation finished
- `error` - Error occurred (non-fatal)

**Features:**
- ✅ Async generator pattern for streaming events
- ✅ Parallel seller responses using `asyncio.gather()`
- ✅ Graceful error handling (errors don't crash graph)
- ✅ Configurable max rounds
- ✅ Seed support for determinism

---

## Architecture

### Component Relationships

```
NegotiationGraph
├── BuyerAgent
│   ├── Uses: render_buyer_prompt()
│   ├── Uses: filter_conversation()
│   └── Uses: parse_mentions()
│
├── SellerAgent (multiple instances)
│   ├── Uses: render_seller_prompt()
│   └── Uses: filter_conversation()
│
└── Decision Engine
    └── Uses: render_decision_prompt()
```

### Data Flow

1. **Initialization:**
   - Create `NegotiationRoomState` with buyer constraints, sellers, inventory
   - Initialize `NegotiationGraph` with LLM provider

2. **Round Execution:**
   - Buyer agent generates message → Parse mentions → Route to sellers
   - Sellers respond in parallel → Filter visibility → Update history
   - Decision check → Continue or complete

3. **Completion:**
   - Buyer accepts offer OR max rounds reached
   - Final state updated with selected seller, final offer, reason

---

## Key Design Decisions

### 1. Opaque Negotiation Model
- **Why:** Realistic marketplace where sellers don't share internal costs
- **How:** Visibility filtering ensures buyers only see public messages
- **Benefit:** More realistic negotiation dynamics

### 2. Parallel Seller Responses
- **Why:** Sellers respond simultaneously, not sequentially
- **How:** `asyncio.gather()` for concurrent LLM calls
- **Benefit:** Faster negotiations, more realistic behavior

### 3. Offer Clamping
- **Why:** LLMs may generate invalid offers outside constraints
- **How:** Automatic clamping in `SellerAgent._clamp_offer()`
- **Benefit:** Guarantees valid offers, prevents errors

### 4. Mention-Based Routing
- **Why:** Buyers explicitly choose which sellers to address
- **How:** `@SellerName` convention with regex parsing
- **Benefit:** Clear communication, explicit routing

### 5. Event-Driven Architecture
- **Why:** Real-time updates, streaming support
- **How:** Async generator pattern with event emission
- **Benefit:** Can stream events to frontend via SSE

---

## Testing

### Test Coverage

- **Unit Tests:** 23 tests (prompts, routing, visibility)
- **Integration Tests:** 11 tests (agents, graph flow)
- **Manual Tests:** End-to-end negotiation verification

**All tests passing:** ✅ 100%

See `PHASE_2_TESTING_REPORT.md` for detailed test results.

---

## Configuration

### Environment Variables

```bash
# LLM Provider
LLM_PROVIDER=openrouter  # or lm_studio
LLM_ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=your_key_here

# Negotiation Settings
MAX_NEGOTIATION_ROUNDS=10
PARALLEL_SELLER_LIMIT=10
LLM_DEFAULT_TEMPERATURE=0.0
LLM_DEFAULT_MAX_TOKENS=256
```

---

## Usage Example

```python
from app.llm.provider_factory import get_provider
from app.agents.graph_builder import NegotiationGraph
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from app.models.negotiation import NegotiationRoomState

# Get provider
provider = get_provider()

# Create room state
room_state = NegotiationRoomState(
    room_id="room1",
    buyer_id="buyer1",
    buyer_name="Alice",
    buyer_constraints=BuyerConstraints(
        item_id="laptop",
        item_name="Gaming Laptop",
        quantity_needed=2,
        min_price_per_unit=800.0,
        max_price_per_unit=1200.0
    ),
    sellers=[...],  # List of Seller objects
    conversation_history=[],
    current_round=0,
    max_rounds=3
)

# Run negotiation
graph = NegotiationGraph(provider)
async for event in graph.run(room_state):
    print(f"[{event['type']}] {event['data']}")
    
    if event['type'] == 'negotiation_complete':
        break

# Check final state
print(f"Selected: {room_state.selected_seller_id}")
print(f"Final Offer: {room_state.final_offer}")
```

---

## Files Structure

```
app/
├── agents/
│   ├── buyer_agent.py      # Buyer agent implementation
│   ├── seller_agent.py     # Seller agent implementation
│   ├── graph_builder.py    # Negotiation graph orchestrator
│   └── prompts.py          # Prompt templates
│
├── services/
│   ├── message_router.py   # Mention parsing and routing
│   └── visibility_filter.py # Conversation visibility filtering
│
└── models/
    ├── agent.py            # BuyerConstraints, Seller, SellerProfile, InventoryItem
    ├── negotiation.py      # NegotiationRoomState, NegotiationEvent
    └── message.py          # Message, Offer types
```

---

## Next Steps (Phase 3)

Phase 2 provides the core negotiation logic. Phase 3 will add:

1. **Database Integration:**
   - Persist negotiation sessions
   - Store conversation history
   - Track offers and decisions

2. **Session Management:**
   - Create/manage negotiation sessions
   - Resume interrupted negotiations
   - Session lifecycle management

3. **State Persistence:**
   - Save/load negotiation state
   - Handle crashes gracefully
   - Support long-running negotiations

---

## References

- **Testing Report:** `PHASE_2_TESTING_REPORT.md`
- **Architecture:** `multi-agent-marketplace-architecture.md`
- **Backend Spec:** `backend_spec.md`
- **Test Plan:** `.cursor/plans/phase-1d8e51-76185d52.plan.md`

---

**Status:** ✅ Phase 2 Complete - Ready for Phase 3 Development

