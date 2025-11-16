# Multi-Agent Ecommerce Marketplace - Backend Architecture Design

**Version:** 1.0  
**Date:** November 15, 2025  
**Project Type:** Hackathon - Multi-agent simulation platform

---

## 1. Executive Summary

A multi-agent ecommerce marketplace simulation where a single buyer negotiates with multiple sellers (up to 10) for various items. The system uses LangGraph for orchestration and supports both on-device inference (LM Studio) and cloud-based inference (OpenRouter API) with streaming responses.

### Key Features
- **Per-item negotiation rooms** with @mention-based message routing
- **Dynamic agent strategies** - agents autonomously decide behavior based on context
- **Asymmetric information** - buyer sees all, sellers see only buyer messages directed at them
- **Flexible LLM backend** - switch between on-device and API-based inference
- **Real-time streaming** responses for interactive experience

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│  - Seller Configuration Form (max 10 sellers)                   │
│  - Buyer Configuration Form                                      │
│  - Negotiation UI with streaming chat display                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Orchestration                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph Workflow Engine                    │  │
│  │  - State Management                                        │  │
│  │  - Agent Coordination                                      │  │
│  │  - Message Routing (@mentions)                            │  │
│  │  - Negotiation Lifecycle Management                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Seller Selection Algorithm Module                 │  │
│  │  - Item-based seller matching                             │  │
│  │  - Availability & inventory check                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Agent Management Layer                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │ Buyer Agent │  │Seller Agent1│  │Seller Agent2│ ...  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Inference Layer                           │
│                                                                   │
│  ┌─────────────────────┐          ┌────────────────────────┐   │
│  │  LM Studio Adapter  │    OR    │ OpenRouter API Adapter │   │
│  │  (On-device)        │          │ (Cloud-based)          │   │
│  │  - Sequential runs  │          │ - Batch processing     │   │
│  └─────────────────────┘          └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Persistence Layer                              │
│  - In-memory state during simulation                            │
│  - Completed negotiation logs (saved post-decision)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Agent Configuration Schema

#### **Seller Agent Configuration**
```
Seller {
    id: UUID
    name: String
    
    inventory: [
        {
            item_id: String
            item_name: String
            cost_price: Float
            selling_price: Float
            least_price: Float  // selling_price > least_price > cost_price
            quantity_available: Int
        }
    ]
    
    profile: {
        priority: Enum["customer_retention", "maximize_profit"]
        speaking_style: Enum["rude", "very_sweet"]
    }
    
    // Runtime state
    current_negotiations: Map<item_id, conversation_context>
}
```

#### **Buyer Agent Configuration**
```
Buyer {
    id: UUID
    name: String
    
    shopping_list: [
        {
            item_id: String
            item_name: String
            quantity_needed: Int
        }
    ]
    
    budget_range: {
        min: Float
        max: Float
    }
    
    // Runtime state
    active_negotiations: Map<item_id, negotiation_room_id>
    purchase_decisions: []
}
```

---

### 3.2 Seller Selection Algorithm

**Purpose:** For each item in buyer's shopping list, algorithmically select which sellers can participate in negotiation.

**Selection Criteria:**
1. **Availability Check:** Seller must have the item in inventory
2. **Quantity Match:** `seller.quantity_available >= buyer.quantity_needed`
3. **Price Range Feasibility:** `seller.least_price <= buyer.budget_range.max`

**Algorithm Flow:**
```
For each item in buyer.shopping_list:
    eligible_sellers = []
    
    For each seller in marketplace:
        IF seller has item in inventory:
            IF seller.quantity_available >= item.quantity_needed:
                IF seller.least_price <= buyer.budget_range.max:
                    eligible_sellers.append(seller)
    
    IF eligible_sellers.count > 0:
        create_negotiation_room(item, eligible_sellers)
    ELSE:
        log_no_sellers_available(item)
```

**Edge Cases:**
- If 0 sellers match: Notify buyer, skip item
- If all sellers match (up to 10): Include all in negotiation
- If > 10 sellers match: Apply secondary ranking (e.g., closest to selling_price, or random selection)

---

### 3.3 LangGraph State Schema

**Global State (Shared across all negotiations)**
```python
GlobalState = {
    "buyer": BuyerConfig,
    "sellers": List[SellerConfig],
    "marketplace_metadata": {
        "simulation_start_time": DateTime,
        "llm_provider": Enum["lm_studio", "openrouter"],
        "streaming_enabled": Boolean
    }
}
```

**Per-Item Negotiation State**
```python
NegotiationRoomState = {
    "room_id": UUID,
    "item_id": String,
    "item_name": String,
    "buyer_id": UUID,
    "participating_sellers": List[UUID],
    
    "conversation_history": [
        {
            "timestamp": DateTime,
            "sender_id": UUID,
            "sender_type": Enum["buyer", "seller"],
            "message": String,
            "mentioned_agents": List[UUID],  // for @mentions
            "visibility": List[UUID]  // who can see this message
        }
    ],
    
    "current_offers": Map<seller_id, {
        "price": Float,
        "quantity": Int,
        "conditions": String
    }>,
    
    "negotiation_status": Enum["active", "completed", "abandoned"],
    "final_decision": {
        "selected_seller_id": UUID or None,
        "final_price": Float,
        "reason": String
    }
}
```

---

## 4. LangGraph Workflow Design

### 4.1 High-Level Workflow

The system uses a **per-item negotiation workflow** with decentralized agent communication.

```
[START] 
   ↓
[Initialize Marketplace] - Load buyer & seller configs
   ↓
[For Each Item in Shopping List]
   ↓
   [Run Seller Selection Algorithm]
   ↓
   [Create Negotiation Room]
   ↓
   [Spawn Negotiation Subgraph] ←──┐
   ↓                                 │
   [Buyer Initiates Conversation]   │
   ↓                                 │
   [Agent Decision Loop] ───────────┘
      ↓
      • Buyer sends message (with @mentions)
      • Route to mentioned sellers
      • Sellers respond (if mentioned)
      • Update offers
      • Check termination conditions
   ↓
   [Buyer Makes Final Decision]
   ↓
   [Save Negotiation Log]
   ↓
[Next Item]
   ↓
[END - Generate Shopping Summary]
```

### 4.2 Negotiation Subgraph (Per Item)

**Node Types:**

1. **BuyerTurnNode**
   - Input: Current negotiation state
   - Action: 
     - LLM generates buyer's message based on offers, budget, conversation history
     - Parse @mentions to identify target sellers
     - Update conversation history
   - Output: Message + mentioned_sellers[]

2. **MessageRoutingNode**
   - Input: Buyer's message with @mentions
   - Action: 
     - Create seller-specific message contexts (filtered view)
     - Queue messages for mentioned sellers only
   - Output: Routed messages per seller

3. **SellerResponseNode** (Parallel execution for mentioned sellers)
   - Input: Filtered conversation view (only buyer messages to them)
   - Action:
     - LLM generates seller response based on:
       - Profile (priority, speaking_style)
       - Current offer vs least_price
       - Buyer's negotiation tactics
     - Update current_offer if price changes
   - Output: Seller message + updated offer

4. **DecisionCheckNode**
   - Input: Updated conversation + offers
   - Action:
     - Check if buyer is ready to make decision (LLM-based or rule-based)
     - Check if max rounds reached (e.g., 10 turns)
   - Output: Decision {"continue", "buyer_decides", "timeout"}

5. **BuyerDecisionNode**
   - Input: All offers + conversation history
   - Action:
     - LLM evaluates offers against budget and preferences
     - Select best seller OR reject all
   - Output: Final decision

**Graph Structure:**
```
BuyerTurnNode 
    ↓
MessageRoutingNode
    ↓
[Parallel] SellerResponseNode (for each mentioned seller)
    ↓
DecisionCheckNode
    ↓ (if continue)
    ↑───── (loop back to BuyerTurnNode)
    ↓ (if buyer_decides)
BuyerDecisionNode
    ↓
[Save & Exit]
```

---

## 5. Message Routing & @Mentions System

### 5.1 @Mention Parsing

**Buyer Message Format:**
```
"Hey @Seller1 and @Seller3, can you match the price of $50 for 10 units?"
```

**Parsing Logic:**
```python
def parse_mentions(message: str, available_sellers: List[Seller]) -> List[UUID]:
    mentioned = []
    for seller in available_sellers:
        if f"@{seller.name}" in message:
            mentioned.append(seller.id)
    return mentioned
```

### 5.2 Visibility Rules

**For Buyer:**
- Sees ALL messages in the conversation (full history)

**For Seller (e.g., Seller1):**
- Sees only messages where:
  - `sender_type == "buyer"` AND `seller.id in mentioned_agents`
  - OR `sender_id == seller.id` (their own messages)

**Implementation:**
```python
def get_conversation_view(negotiation_state, agent_id, agent_type):
    if agent_type == "buyer":
        return negotiation_state.conversation_history  // full view
    
    elif agent_type == "seller":
        filtered_history = []
        for message in negotiation_state.conversation_history:
            if message.sender_id == agent_id:
                filtered_history.append(message)
            elif message.sender_type == "buyer" and agent_id in message.mentioned_agents:
                filtered_history.append(message)
        return filtered_history
```

---

## 6. LLM Integration Architecture

### 6.1 Adapter Pattern

Create an abstract `LLMProvider` interface with two implementations:

```
LLMProvider (Abstract)
    ├── LMStudioAdapter (On-device)
    └── OpenRouterAdapter (Cloud API)
```

**Interface Methods:**
```python
class LLMProvider:
    def generate_streaming(
        self, 
        system_prompt: str, 
        user_message: str, 
        conversation_history: List[Dict],
        agent_config: Dict
    ) -> Iterator[str]:
        """Yields tokens as they're generated"""
        pass
    
    def generate_batch(
        self,
        requests: List[GenerationRequest]
    ) -> List[str]:
        """For batch processing multiple requests"""
        pass
```

### 6.2 LM Studio Adapter

**Configuration:**
```python
LMStudioConfig = {
    "base_url": "http://localhost:1234/v1",
    "model": "user_selected_model",  // e.g., "llama-3-8b"
    "temperature": 0.7,
    "max_tokens": 500,
    "stream": True
}
```

**Execution Mode:** Sequential
- Process one agent at a time
- Wait for completion before next agent

**Benefits:** No API costs, privacy, offline capability  
**Tradeoffs:** Slower, sequential processing

### 6.3 OpenRouter Adapter

**Configuration:**
```python
OpenRouterConfig = {
    "api_key": "user_api_key",
    "base_url": "https://openrouter.ai/api/v1",
    "model": "meta-llama/llama-3-70b-instruct",  // or user choice
    "temperature": 0.7,
    "max_tokens": 500,
    "stream": True
}
```

**Execution Mode:** Batch (parallel API calls)
- Send requests for all mentioned sellers concurrently
- Use asyncio for parallel processing

**Benefits:** Faster, can parallelize seller responses  
**Tradeoffs:** API costs, requires internet

### 6.4 Streaming Response Handling

**Backend → Frontend Flow:**
```
LLM Stream → LangGraph Node → WebSocket/SSE → Frontend UI
```

**Implementation Considerations:**
- Use Server-Sent Events (SSE) or WebSockets for real-time streaming
- Buffer partial responses in negotiation state
- Handle connection drops gracefully

---

## 7. Agent Prompting Strategy

### 7.1 Buyer Agent Prompt Template

```python
BUYER_SYSTEM_PROMPT = """
You are a buyer in an ecommerce marketplace negotiating for {item_name}.

Your Budget: ${budget_min} - ${budget_max}
Quantity Needed: {quantity}

Available Sellers: {seller_names}

NEGOTIATION RULES:
1. Use @mentions to direct messages to specific sellers (e.g., "@SellerName")
2. You can see all seller responses, but sellers cannot see each other's offers
3. Negotiate to get the best price within your budget
4. Consider quantity, price, and seller reliability
5. You can mention multiple sellers in one message

Current Offers:
{current_offers_summary}

Previous Conversation:
{conversation_history}

Your goal: Get the best deal. Be strategic and leverage competition between sellers.
"""
```

### 7.2 Seller Agent Prompt Template

```python
SELLER_SYSTEM_PROMPT = """
You are {seller_name}, a seller in an ecommerce marketplace.

Item: {item_name}
Your Costs:
- Cost Price: ${cost_price} (you lose money below this)
- Selling Price: ${selling_price} (your ideal price)
- Least Price: ${least_price} (minimum you'll accept)

Your Profile:
- Priority: {priority}  // "customer_retention" or "maximize_profit"
- Speaking Style: {speaking_style}  // "rude" or "very_sweet"

NEGOTIATION RULES:
1. You only see messages from the buyer that mention you (@{seller_name})
2. You cannot see other sellers' offers or conversations
3. Stay in character based on your speaking style
4. Balance your priority with profitability

Conversation (messages to you):
{filtered_conversation_history}

Current Offer from You: ${current_offer_price}

IMPORTANT:
- If priority is "customer_retention": Be willing to go closer to least_price, focus on long-term relationship
- If priority is "maximize_profit": Hold firm on price, only reduce if necessary
- If speaking_style is "rude": Be curt, direct, no-nonsense
- If speaking_style is "very_sweet": Be friendly, accommodating, use warm language

Respond to the buyer strategically. You can adjust your price, hold firm, or add value propositions.
"""
```

### 7.3 Dynamic Strategy Implementation

**Key Principle:** Agents decide strategy via LLM reasoning, not hardcoded rules.

**Approach:**
- Provide context-rich prompts with all relevant information
- Let LLM "think" about:
  - Current negotiation position
  - Buyer's negotiation tactics
  - Own constraints (budget, costs)
  - Personality traits
- LLM generates both the message AND updates the offer

**Example Seller Response:**
```json
{
    "message": "Hi buyer! I appreciate your interest. While $45 is below my usual price, I value long-term customers. I can do $47 for you - that's a special deal!",
    "updated_offer": {
        "price": 47.0,
        "quantity": 10
    },
    "reasoning": "Customer retention priority, so moving closer to least_price of $45. Sweet speaking style evident."
}
```

---

## 8. Data Flow Diagrams

### 8.1 Initialization Flow

```
User Input (Frontend)
    ↓
Configure Buyer:
  - Shopping list (items + quantities)
  - Budget range
    ↓
Configure Sellers (up to 10):
  - Inventory (items, prices, quantities)
  - Profile (priority, style)
    ↓
Submit to Backend
    ↓
Initialize LangGraph Global State
    ↓
For each item:
  Run Seller Selection Algorithm
    ↓
Create Negotiation Room(s)
    ↓
Return session_id to Frontend
```

### 8.2 Negotiation Flow (Per Item)

```
Negotiation Room Created
    ↓
Buyer Agent → Generate opening message
    ↓
Parse @mentions → Identify target sellers
    ↓
Route message to mentioned sellers
    ↓
[PARALLEL if OpenRouter / SEQUENTIAL if LM Studio]
    ↓
Each mentioned Seller:
  - Receive filtered conversation view
  - Generate response via LLM
  - Update offer if price changes
    ↓
All seller responses collected
    ↓
Update conversation history
    ↓
Decision Check:
  - Buyer satisfied with offer? → Go to Decision
  - Max rounds reached? → Go to Decision
  - Else → Loop back to Buyer Agent
    ↓
Buyer Decision Node:
  - Evaluate all offers
  - Select best seller OR reject all
    ↓
Save completed negotiation log
    ↓
Update buyer's purchase history
    ↓
Move to next item
```

### 8.3 Message Visibility Flow

```
Buyer sends message: "Hey @Seller1 and @Seller3, can you match $50?"
    ↓
Message stored in conversation_history:
{
  sender_id: buyer.id,
  message: "...",
  mentioned_agents: [seller1.id, seller3.id],
  visibility: [buyer.id, seller1.id, seller3.id]
}
    ↓
When Seller1 requests conversation view:
  → Sees: messages where visibility includes seller1.id
    ↓
When Seller2 requests conversation view:
  → Sees: ONLY their own messages (buyer didn't mention them)
    ↓
When Buyer requests conversation view:
  → Sees: ALL messages (full conversation)
```

---

## 9. API Design

### 9.1 Backend API Endpoints

**1. Initialize Simulation**
```
POST /api/simulation/initialize
Request Body:
{
  "buyer": BuyerConfig,
  "sellers": [SellerConfig],
  "llm_config": {
    "provider": "lm_studio" | "openrouter",
    "model": "string",
    "api_key": "string" (if openrouter)
  }
}

Response:
{
  "session_id": "uuid",
  "negotiation_rooms": [
    {
      "room_id": "uuid",
      "item_name": "string",
      "participating_sellers": ["seller1", "seller2"]
    }
  ]
}
```

**2. Start Negotiation (for specific item)**
```
POST /api/negotiation/{room_id}/start
Response:
{
  "status": "started",
  "buyer_opening_message": "string"
}
```

**3. Stream Negotiation Events**
```
GET /api/negotiation/{room_id}/stream
Response: SSE stream

Event types:
- buyer_message: { message, mentioned_sellers }
- seller_response: { seller_id, message, updated_offer }
- negotiation_complete: { final_decision }
```

**4. Get Negotiation State**
```
GET /api/negotiation/{room_id}/state
Query Params:
  - agent_id: UUID
  - agent_type: "buyer" | "seller"

Response:
{
  "conversation_history": [...],  // filtered by visibility
  "current_offers": {...},
  "status": "active" | "completed"
}
```

**5. Get Final Summary**
```
GET /api/simulation/{session_id}/summary
Response:
{
  "total_items": int,
  "completed_purchases": [
    {
      "item_name": "string",
      "selected_seller": "string",
      "final_price": float,
      "negotiation_rounds": int
    }
  ],
  "total_spent": float,
  "budget_utilization": float
}
```

---

## 10. Persistence Strategy

### 10.1 In-Memory During Simulation

**Data Structures:**
```python
# Global in-memory store
active_sessions = {
    "session_id": {
        "global_state": GlobalState,
        "negotiation_rooms": {
            "room_id": NegotiationRoomState
        }
    }
}
```

**Justification:**
- Fast access for real-time negotiation
- No database overhead
- Suitable for hackathon scope
- Sessions are short-lived (< 1 hour)

### 10.2 Post-Completion Persistence

**When:** After buyer makes final decision for an item

**What to Save:**
```json
{
  "session_id": "uuid",
  "room_id": "uuid",
  "item_name": "string",
  "timestamp": "ISO8601",
  "buyer_id": "uuid",
  "participating_sellers": ["seller1", "seller2"],
  "conversation_log": [
    {
      "turn": 1,
      "sender": "buyer",
      "message": "...",
      "mentioned_agents": [...]
    }
  ],
  "final_offers": {
    "seller1": {"price": 50, "quantity": 10},
    "seller2": {"price": 52, "quantity": 10}
  },
  "decision": {
    "selected_seller": "seller1",
    "final_price": 50,
    "reason": "Best price within budget"
  },
  "negotiation_metrics": {
    "total_rounds": 5,
    "duration_seconds": 120
  }
}
```

**Storage Options:**
- JSON files (simple, good for demo)
- SQLite (lightweight, queryable)
- MongoDB (if need flexible schema)

**File Structure:**
```
/logs
  /session_<session_id>
    /negotiation_<item1_name>.json
    /negotiation_<item2_name>.json
    /summary.json
```

---

## 11. Error Handling & Edge Cases

### 11.1 Seller Selection Errors

| Error Case | Handling |
|------------|----------|
| No sellers have item | Skip item, notify buyer in summary |
| All sellers out of stock | Skip item, log reason |
| Seller prices exceed budget | Include anyway, let buyer negotiate |
| >10 sellers eligible | Randomly select 10 OR rank by price proximity |

### 11.2 Negotiation Errors

| Error Case | Handling |
|------------|----------|
| LLM timeout | Retry 3x, then use fallback (auto-reject) |
| Invalid @mention | Ignore mention, log warning |
| Seller offers below cost_price | Override offer, set to least_price |
| Max rounds reached (e.g., 10) | Force buyer decision |
| Buyer mentions non-existent seller | Ignore, continue |

### 11.3 LLM Provider Errors

| Error Case | Handling |
|------------|----------|
| LM Studio not running | Show clear error to user, suggest start |
| OpenRouter API key invalid | Validate on init, fail fast |
| Rate limit hit | Queue requests, implement backoff |
| Model not found | List available models, let user re-select |

### 11.4 Streaming Errors

| Error Case | Handling |
|------------|----------|
| Connection dropped mid-stream | Buffer partial response, reconnect, resume |
| Client disconnects | Continue negotiation, cache result |
| Incomplete response | Use partial + append "..." |

---

## 12. Performance Considerations

### 12.1 Latency Breakdown (Estimated)

**LM Studio (Sequential):**
- Buyer turn: 3-5s
- Each seller turn: 3-5s
- Total per round: ~15-30s (for 3 sellers)
- Full negotiation (5 rounds): 75-150s

**OpenRouter (Parallel):**
- Buyer turn: 2-3s
- All sellers (parallel): 2-3s
- Total per round: ~4-6s
- Full negotiation (5 rounds): 20-30s

### 12.2 Optimization Strategies

1. **Caching:**
   - Cache seller profiles in memory
   - Reuse LLM embeddings for similar items

2. **Parallel Processing:**
   - If OpenRouter: Use asyncio for seller responses
   - Process multiple negotiation rooms in parallel (different items)

3. **Early Termination:**
   - If buyer gets offer within budget early, allow early decision
   - Implement confidence scoring for buyer decisions

4. **Prompt Optimization:**
   - Keep prompts concise but context-rich
   - Use few-shot examples for consistent outputs

---

## 13. Technology Stack

### 13.1 Core Dependencies

```yaml
Backend Framework:
  - FastAPI (for REST API + SSE support)
  - Python 3.11+

Orchestration:
  - LangGraph >= 0.2.0
  - LangChain >= 0.1.0

LLM Integration:
  - openai Python SDK (for OpenRouter compatibility)
  - requests (for LM Studio REST API)

Async/Streaming:
  - asyncio
  - sse-starlette (for Server-Sent Events)

Data Handling:
  - pydantic (for data validation)
  - python-json-logger (for structured logs)

Testing:
  - pytest
  - pytest-asyncio
```

### 13.2 Frontend Integration (For Context)

```yaml
Frontend:
  - React/Next.js
  - WebSocket/EventSource for streaming
  - Form libraries for seller/buyer config
```

---

## 14. Implementation Phases

### Phase 1: Core Foundation (Days 1-2)
- [ ] Define Pydantic schemas for Buyer, Seller, NegotiationRoom
- [ ] Implement Seller Selection Algorithm
- [ ] Setup LangGraph basic state structure
- [ ] Create LLMProvider abstract class + LM Studio adapter

### Phase 2: Negotiation Logic (Days 3-4)
- [ ] Build LangGraph negotiation subgraph
- [ ] Implement @mention parsing and message routing
- [ ] Create buyer/seller prompt templates
- [ ] Add conversation history filtering logic

### Phase 3: LLM Integration (Days 5-6)
- [ ] Complete LM Studio adapter with streaming
- [ ] Implement OpenRouter adapter with batch processing
- [ ] Add error handling and retries
- [ ] Test with real LLM models

### Phase 4: API & Streaming (Day 7)
- [ ] Build FastAPI endpoints
- [ ] Implement SSE for real-time streaming
- [ ] Add negotiation state management
- [ ] Create session cleanup logic

### Phase 5: Persistence & Polish (Day 8)
- [ ] Implement JSON log saving
- [ ] Create summary generation
- [ ] Add comprehensive error handling
- [ ] Write integration tests

---

## 15. Testing Strategy

### 15.1 Unit Tests

- **Seller Selection Algorithm:**
  - Test with 0, 1, 5, 10, 15 sellers
  - Test budget constraints
  - Test inventory availability

- **Message Routing:**
  - Test @mention parsing (single, multiple, invalid)
  - Test visibility filtering per agent
  - Test conversation history retrieval

- **Offer Validation:**
  - Test seller price bounds (cost_price < least_price < selling_price)
  - Test buyer budget adherence

### 15.2 Integration Tests

- **End-to-End Negotiation:**
  - Buyer + 3 sellers, complete negotiation
  - Test with LM Studio (mocked)
  - Test with OpenRouter (mocked)

- **Streaming:**
  - Test SSE connection lifecycle
  - Test reconnection handling
  - Test partial response buffering

### 15.3 LLM Behavior Tests

- **Prompt Effectiveness:**
  - Test if sellers respect pricing bounds
  - Test if buyer correctly uses @mentions
  - Test if speaking styles are evident

- **Strategy Adherence:**
  - Test customer_retention vs maximize_profit behavior
  - Test negotiation tactics diversity

---

## 16. Monitoring & Debugging

### 16.1 Logging Strategy

```python
# Structured logging format
{
  "timestamp": "2025-11-15T10:30:00Z",
  "session_id": "uuid",
  "room_id": "uuid",
  "event_type": "seller_response",
  "agent_id": "seller_1",
  "message_length": 145,
  "updated_offer": 48.50,
  "llm_latency_ms": 3400
}
```

**Key Metrics to Log:**
- LLM latency per request
- Negotiation round count
- Price convergence over time
- Buyer decision reasons
- Error rates by type

### 16.2 Debug Mode Features

- Toggle to show full prompts sent to LLM
- Display LLM raw responses before parsing
- Conversation replay with step-through
- State inspection at each graph node

---

## 17. Security Considerations

### 17.1 Input Validation

- Sanitize seller/buyer names (no XSS)
- Validate price ranges (no negative values)
- Limit conversation history size (prevent DoS)
- Rate limit API requests

### 17.2 API Key Protection

- Store OpenRouter API key in environment variables
- Never log API keys
- Validate key on initialization

### 17.3 LLM Safety

- Set max_tokens limits
- Monitor for prompt injection attempts
- Implement content filtering if needed

---

## 18. Deployment Architecture (Optional - Post-Hackathon)

```
┌─────────────────────────────────────────┐
│          Load Balancer                   │
└────────────────┬────────────────────────┘
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
┌──────────┐            ┌──────────┐
│ Backend  │            │ Backend  │
│ Instance │            │ Instance │
└──────────┘            └──────────┘
     │                       │
     └───────────┬───────────┘
                 ▼
         ┌──────────────┐
         │   Redis      │
         │ (State Cache)│
         └──────────────┘
                 │
                 ▼
         ┌──────────────┐
         │  PostgreSQL  │
         │ (Logs & Data)│
         └──────────────┘
```

---

## 19. Future Enhancements (Out of Scope)

- Multi-buyer support (competitive bidding)
- Real-time analytics dashboard
- Agent learning from past negotiations
- Complex negotiation tactics (bundles, discounts)
- Seller reputation system
- WebSocket instead of SSE for bidirectional streaming
- GraphQL API for flexible data fetching

---

## 20. Open Questions & Design Decisions

**Need to Decide:**

1. **Max Negotiation Rounds:** 
   - Proposed: 10 rounds per item
   - Alternative: Time-based (e.g., 5 minutes)

2. **Seller Selection Ranking (if >10 eligible):**
   - Option A: Random selection
   - Option B: Closest to budget
   - Option C: Highest rated (if reputation system added)

3. **Buyer Decision Trigger:**
   - Option A: Explicit command ("I'll take Seller1's offer")
   - Option B: LLM infers readiness from conversation tone
   - Recommended: Hybrid (LLM suggests, user confirms)

4. **Partial Purchase Handling:**
   - If buyer wants 100 units but sellers only offer 50 each
   - Split purchase across multiple sellers?
   - Currently: Out of scope, buyer selects one seller

5. **Conversation Context Window:**
   - Full history or sliding window (last N messages)?
   - Recommended: Full history for short hackathon demos

---

## 21. Success Metrics

**For Hackathon Demo:**

1. **Functional:**
   - ✅ Successfully complete 1 negotiation with 3+ sellers
   - ✅ @mention system works correctly
   - ✅ Streaming responses visible in real-time
   - ✅ Both LM Studio and OpenRouter work

2. **Quality:**
   - ✅ Sellers exhibit distinct personalities (rude vs sweet)
   - ✅ Prices respect constraints (cost < least < selling)
   - ✅ Buyer makes reasonable decisions

3. **Performance:**
   - ✅ <30s per negotiation round (LM Studio)
   - ✅ <10s per negotiation round (OpenRouter)

4. **UX:**
   - ✅ Configuration form is intuitive
   - ✅ Chat interface shows clear agent identities
   - ✅ Summary is informative and concise

---

## 22. Conclusion

This architecture provides a solid foundation for a multi-agent ecommerce marketplace simulation. The design prioritizes:

- **Flexibility:** Swap between LM Studio and OpenRouter seamlessly
- **Scalability:** Modular design allows easy extension
- **Realism:** Agent-driven strategies, asymmetric information
- **Demo-friendly:** Streaming UI, clear visualizations

**Next Steps:**
1. Review and approve this design doc
2. Set up project repository and dependencies
3. Begin Phase 1 implementation
4. Iterate based on LLM behavior testing

---

**Document Version:** 1.0  
**Last Updated:** November 15, 2025  
**Status:** Ready for Implementation
