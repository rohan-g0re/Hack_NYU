# Multi-Agent Marketplace API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api/v1`  
**Last Updated:** 2025-11-16  
**Status:** Production Ready (95.1% test coverage)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Error Handling](#error-handling)
4. [Simulation Endpoints](#simulation-endpoints)
5. [Negotiation Endpoints](#negotiation-endpoints)
6. [Streaming (SSE) Endpoint](#streaming-sse-endpoint)
7. [Status & Health Endpoints](#status--health-endpoints)
8. [Logs Endpoint](#logs-endpoint)
9. [Data Models](#data-models)
10. [Event Types (SSE)](#event-types-sse)

---

## Overview

The Multi-Agent Marketplace API provides endpoints for managing AI-powered buyer-seller negotiations. The system supports:

- **Session Management:** Create and manage negotiation sessions
- **Real-time Negotiations:** Stream live negotiations via Server-Sent Events (SSE)
- **Multi-seller Support:** Handle up to 10 sellers per session
- **Decision Engine:** AI-powered buyer decision making
- **Comprehensive Logging:** Full audit trail of all negotiations

### Key Features

- ✅ Real-time streaming via SSE
- ✅ Concurrent negotiation support
- ✅ Automatic seller selection based on inventory
- ✅ Configurable buyer constraints and seller profiles
- ✅ Comprehensive error handling with detailed error codes
- ✅ Session persistence and summary generation

---

## Authentication

**Current Version:** No authentication required

All endpoints are currently open. Future versions may implement API key or OAuth2 authentication.

---

## Error Handling

All API errors follow a standardized format:

### Error Response Schema

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context (optional)"
    },
    "timestamp": "2025-11-16T12:00:00.000000"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Request validation failed |
| 400 | `MAX_SELLERS_EXCEEDED` | Too many sellers (max 10) |
| 400 | `LLM_PROVIDER_DISABLED` | LLM provider is disabled |
| 404 | `SESSION_NOT_FOUND` | Session ID does not exist |
| 404 | `ROOM_NOT_FOUND` | Negotiation room not found |
| 404 | `LOG_NOT_FOUND` | Log file not found |
| 409 | `NEGOTIATION_ALREADY_ACTIVE` | Negotiation already in progress |
| 422 | `INSUFFICIENT_INVENTORY` | Seller lacks required inventory |
| 503 | `LLM_TIMEOUT` | LLM provider timeout |
| 503 | `LLM_PROVIDER_UNAVAILABLE` | LLM provider is down |

### Validation Error Details

Validation errors include field-level details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "buyer.shopping_list[0].max_price_per_unit",
      "reason": "must be greater than min_price_per_unit"
    },
    "timestamp": "2025-11-16T12:00:00.000000"
  }
}
```

---

## Simulation Endpoints

### 1. Initialize Session

Create a new negotiation session with buyer, sellers, and negotiation rooms.

**Endpoint:** `POST /api/v1/simulation/initialize`

**Request Body:**

```json
{
  "buyer": {
    "name": "TechCorp Procurement",
    "shopping_list": [
      {
        "item_id": "laptop_hp_15",
        "item_name": "HP 15 Laptop",
        "quantity_needed": 50,
        "min_price_per_unit": 400.0,
        "max_price_per_unit": 600.0
      },
      {
        "item_id": "mouse_logitech_mx",
        "item_name": "Logitech MX Mouse",
        "quantity_needed": 100,
        "min_price_per_unit": 20.0,
        "max_price_per_unit": 35.0
      }
    ]
  },
  "sellers": [
    {
      "name": "ElectroMart",
      "profile": {
        "priority": "maximize_profit",
        "speaking_style": "rude"
      },
      "inventory": [
        {
          "item_id": "laptop_hp_15",
          "item_name": "HP 15 Laptop",
          "quantity_available": 100,
          "cost_price": 400.0,
          "selling_price": 650.0,
          "least_price": 550.0
        }
      ]
    },
    {
      "name": "GadgetHub",
      "profile": {
        "priority": "customer_retention",
        "speaking_style": "very_sweet"
      },
      "inventory": [
        {
          "item_id": "laptop_hp_15",
          "item_name": "HP 15 Laptop",
          "quantity_available": 75,
          "cost_price": 380.0,
          "selling_price": 620.0,
          "least_price": 500.0
        },
        {
          "item_id": "mouse_logitech_mx",
          "item_name": "Logitech MX Mouse",
          "quantity_available": 200,
          "cost_price": 15.0,
          "selling_price": 40.0,
          "least_price": 25.0
        }
      ]
    }
  ],
  "llm_config": {
    "model": "llama-3-8b-instruct",
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

**Request Schema Details:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `buyer.name` | string | Yes | 1-50 chars | Buyer organization name |
| `buyer.shopping_list` | array | Yes | 1-10 items | Items to negotiate |
| `buyer.shopping_list[].item_id` | string | Yes | 1-50 chars | Unique item identifier |
| `buyer.shopping_list[].item_name` | string | Yes | 1-100 chars | Item display name |
| `buyer.shopping_list[].quantity_needed` | integer | Yes | ≥ 1 | Quantity required |
| `buyer.shopping_list[].min_price_per_unit` | float | Yes | ≥ 0 | Minimum acceptable price |
| `buyer.shopping_list[].max_price_per_unit` | float | Yes | > min_price | Maximum willing to pay |
| `sellers` | array | Yes | 1-10 sellers | Seller configurations |
| `sellers[].name` | string | Yes | 1-50 chars | Seller name |
| `sellers[].profile` | object | Yes | - | Seller behavioral profile |
| `sellers[].profile.priority` | string | Yes | See values | `maximize_profit` or `customer_retention` |
| `sellers[].profile.speaking_style` | string | Yes | See values | `rude` or `very_sweet` |
| `sellers[].inventory` | array | Yes | ≥ 1 item | Available inventory |
| `sellers[].inventory[].item_id` | string | Yes | 1-50 chars | Item identifier |
| `sellers[].inventory[].item_name` | string | Yes | 1-100 chars | Item display name |
| `sellers[].inventory[].quantity_available` | integer | Yes | ≥ 1 | Available stock |
| `sellers[].inventory[].cost_price` | float | Yes | ≥ 0 | Seller's cost |
| `sellers[].inventory[].selling_price` | float | Yes | > cost_price | Target selling price |
| `sellers[].inventory[].least_price` | float | Yes | cost < least < selling | Minimum acceptable price |
| `llm_config` | object | Yes | - | LLM provider configuration |
| `llm_config.model` | string | Yes | ≥ 1 char | LLM model name |
| `llm_config.temperature` | float | No | 0.0-1.0, Default: 0.7 | Sampling temperature |
| `llm_config.max_tokens` | integer | No | > 0, Default: 500 | Maximum tokens to generate |

**Success Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-16T12:00:00.000000",
  "buyer_id": "b7c8d9e0-1234-5678-9abc-def012345678",
  "seller_ids": [
    "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "f9e8d7c6-5432-10ab-cdef-0987654321ba"
  ],
  "negotiation_rooms": [
    {
      "room_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
      "item_id": "laptop_hp_15",
      "item_name": "HP 15 Laptop",
      "quantity_needed": 50,
      "buyer_constraints": {
        "min_price_per_unit": 400.0,
        "max_price_per_unit": 600.0
      },
      "participating_sellers": [
        {
          "seller_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
          "seller_name": "ElectroMart",
          "initial_price": null,
          "current_offer": null
        },
        {
          "seller_id": "f9e8d7c6-5432-10ab-cdef-0987654321ba",
          "seller_name": "GadgetHub",
          "initial_price": null,
          "current_offer": null
        }
      ],
      "status": "pending",
      "reason": null
    }
  ],
  "total_rooms": 1,
  "skipped_items": []
}
```

**Error Responses:**

- `400 VALIDATION_ERROR` - Invalid request format or constraints
- `400 MAX_SELLERS_EXCEEDED` - More than 10 sellers provided
- `422 INSUFFICIENT_INVENTORY` - Seller inventory doesn't match buyer items

---

### 2. Get Session Details

Retrieve complete session information including buyer, sellers, and rooms.

**Endpoint:** `GET /api/v1/simulation/{session_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID | Session identifier |

**Success Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "created_at": "2025-11-16T12:00:00.000000",
  "buyer_name": "TechCorp Procurement",
  "total_runs": 2,
  "llm_model": "llama-3-8b-instruct"
}
```

**Error Responses:**

- `404 SESSION_NOT_FOUND` - Session does not exist

---

### 3. Delete Session

Delete a session and all associated data (buyer, sellers, rooms, messages, offers).

**Endpoint:** `DELETE /api/v1/simulation/{session_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID | Session identifier |

**Success Response (200 OK):**

```json
{
  "deleted": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs_saved": true
}
```

**Error Responses:**

- `404 SESSION_NOT_FOUND` - Session does not exist

---

### 4. Get Session Summary

Retrieve aggregated metrics and outcomes for all negotiations in a session.

**Endpoint:** `GET /api/v1/simulation/{session_id}/summary`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID | Session identifier |

**Success Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "buyer_name": "TechCorp Procurement",
  "total_items_requested": 2,
  "completed_purchases": 2,
  "failed_purchases": 0,
  "purchases": [
    {
      "item_name": "HP 15 Laptop",
      "quantity": 50,
      "selected_seller": "ElectroMart",
      "final_price_per_unit": 550.0,
      "total_cost": 27500.0,
      "negotiation_rounds": 5,
      "duration_seconds": 42.5
    }
  ],
  "failed_items": [],
  "total_cost_summary": {
    "total_spent": 32000.0,
    "items_purchased": 2,
    "average_savings_per_item": 25.0
  },
  "negotiation_metrics": {
    "average_rounds": 5.5,
    "average_duration_seconds": 45.2,
    "total_messages_exchanged": 28
  }
}
```

**Error Responses:**

- `404 SESSION_NOT_FOUND` - Session does not exist

---

## Negotiation Endpoints

### 5. Start Negotiation

Start an AI-driven negotiation for a specific room. Returns a stream URL for real-time updates.

**Endpoint:** `POST /api/v1/negotiation/{room_id}/start`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `room_id` | UUID | Negotiation room identifier |

**Success Response (200 OK):**

```json
{
  "status": "active",
  "stream_url": "/api/v1/negotiation/da74688a-9ae7-44ba-85d5-9bbdccb66a51/stream",
  "run_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
  "started_at": "2025-11-16T12:00:00.000000"
}
```

**Error Responses:**

- `404 ROOM_NOT_FOUND` - Room does not exist
- `409 NEGOTIATION_ALREADY_ACTIVE` - Negotiation already in progress for this room

**Usage Notes:**

- After starting, connect to the `stream_url` to receive real-time updates via SSE
- Negotiation runs automatically with AI buyer and seller agents
- Maximum rounds defined in session configuration (default: 10)

---

### 6. Send Message (Manual Buyer Input)

Send a manual message on behalf of the buyer during an active negotiation.

**Endpoint:** `POST /api/v1/negotiation/{room_id}/message`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `room_id` | UUID | Negotiation room identifier |

**Request Body:**

```json
{
  "message": "@ElectroMart Can you do $520 per unit for 50 laptops?"
}
```

**Request Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `message` | string | Yes | 1-1000 chars | Message content |

**Success Response (202 Accepted):**

```json
{
  "message_id": "msg_abc123def456",
  "timestamp": "2025-11-16T12:00:00.000000",
  "mentioned_sellers": ["ElectroMart"],
  "processing": true
}
```

**Error Responses:**

- `404 ROOM_NOT_FOUND` - Room does not exist
- `400 VALIDATION_ERROR` - Invalid message format or length

**Usage Notes:**

- Use `@SellerName` to mention specific sellers
- Message will be processed by seller agents
- Responses will be streamed via SSE connection

---

### 7. Force Decision

Force the buyer agent to make a final decision (accept/reject) on current offers.

**Endpoint:** `POST /api/v1/negotiation/{room_id}/decide`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `room_id` | UUID | Negotiation room identifier |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `decision_type` | string | Yes | `deal` or `no_deal` |
| `selected_seller_id` | UUID | No | Seller ID if `decision_type=deal` |
| `final_price_per_unit` | float | No | Final price if `decision_type=deal` |
| `quantity` | integer | No | Quantity if `decision_type=deal` |
| `decision_reason` | string | No | Reason for decision |

**Example Request:**

```
POST /api/v1/negotiation/{room_id}/decide?decision_type=deal&selected_seller_id=a1b2c3d4-5678-90ab-cdef-1234567890ab&final_price_per_unit=550.0&quantity=50&decision_reason=Manual%20selection%20by%20procurement%20manager
```

**Success Response (200 OK):**

```json
{
  "outcome_id": "outcome_abc123",
  "decision_type": "deal",
  "selected_seller_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "final_price": 550.0,
  "quantity": 50,
  "total_cost": 27500.0
}
```

**Error Responses:**

- `404 ROOM_NOT_FOUND` - Room does not exist
- `400 VALIDATION_ERROR` - Invalid decision parameters

---

### 8. Get Negotiation State

Retrieve current state of a negotiation including messages, offers, and participants.

**Endpoint:** `GET /api/v1/negotiation/{room_id}/state`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `room_id` | UUID | Negotiation room identifier |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | UUID | No | Filter messages visible to specific agent |
| `agent_type` | string | No | `buyer` or `seller` (required if agent_id provided) |

**Success Response (200 OK):**

```json
{
  "room_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
  "item_name": "HP 15 Laptop",
  "status": "in_progress",
  "current_round": 3,
  "max_rounds": 10,
  "conversation_history": [
    {
      "message_id": "msg_001",
      "turn_number": 1,
      "timestamp": "2025-11-16T12:00:10.000000",
      "sender_type": "buyer",
      "sender_id": null,
      "sender_name": "TechCorp Procurement",
      "content": "I need 50 HP 15 Laptop units. My budget is $400-$600 per unit.",
      "mentioned_agents": []
    },
    {
      "message_id": "msg_002",
      "turn_number": 1,
      "timestamp": "2025-11-16T12:00:15.000000",
      "sender_type": "seller",
      "sender_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
      "sender_name": "ElectroMart",
      "content": "We can offer $580 per unit for 50 units.",
      "mentioned_agents": []
    }
  ],
  "current_offers": {
    "a1b2c3d4-5678-90ab-cdef-1234567890ab": {
      "price": 550.0,
      "quantity": 50
    }
  },
  "buyer_constraints": {
    "min_price_per_unit": 400.0,
    "max_price_per_unit": 600.0
  }
}
```

**Error Responses:**

- `404 ROOM_NOT_FOUND` - Room does not exist

**Usage Notes:**

- Use `agent_id` and `agent_type` to filter messages based on visibility rules
- Without filters, returns complete conversation (admin view)
- Sellers only see messages mentioning them or broadcast messages

---

## Streaming (SSE) Endpoint

### 9. Negotiate Stream (Server-Sent Events)

Real-time stream of negotiation events using Server-Sent Events (SSE).

**Endpoint:** `GET /api/v1/negotiation/{room_id}/stream`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `room_id` | UUID | Negotiation room identifier |

**Connection:**

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/negotiation/da74688a-9ae7-44ba-85d5-9bbdccb66a51/stream'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

**Event Format:**

All events follow this structure:

```
event: message
data: {"type": "connected", "room_id": "...", "timestamp": "..."}

event: message
data: {"type": "buyer_message", "message": "...", "timestamp": "..."}
```

**Event Types:**

See [Event Types (SSE)](#event-types-sse) section for detailed event schemas.

**Connection Properties:**

- **Protocol:** Server-Sent Events (SSE)
- **Content-Type:** `text/event-stream`
- **Reconnection:** Automatic (browser handles reconnection)
- **Heartbeat:** Every 15 seconds (configurable via `SSE_HEARTBEAT_INTERVAL`)
- **Timeout:** 30 minutes (configurable via `NEGOTIATION_TIMEOUT_MINUTES`)

**Error Responses:**

- `404 ROOM_NOT_FOUND` - Room does not exist

**Usage Notes:**

- Connect to stream **after** calling `/start` endpoint
- Stream automatically closes after negotiation completes
- Heartbeat events maintain connection during LLM processing
- First event is always `connected` confirming connection establishment

---

## Status & Health Endpoints

### 10. Health Check

Check overall system health including database and LLM provider status.

**Endpoint:** `GET /api/v1/health`

**Success Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
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

**Note:** Status will be `"degraded"` if either LLM or database is unavailable.

**Error Responses:**

- `503 SERVICE_UNAVAILABLE` - Critical service (DB or LLM) is down

---

### 11. LLM Provider Status

Check detailed status of configured LLM provider(s).

**Endpoint:** `GET /api/v1/llm/status`

**Success Response (200 OK):**

```json
{
  "llm": {
    "available": true,
    "base_url": "http://localhost:1234/v1",
    "models": [
      "llama-3-8b-instruct",
      "mistral-7b-instruct"
    ],
    "error": null
  },
  "database": {
    "available": true,
    "url": "sqlite:///data/marketplace.db",
    "error": null
  }
}
```

**Usage Notes:**

- `llm` shows status of the currently configured provider
- `models` array populated only if provider is available
- `database` shows SQLite connection status

---

## Logs Endpoint

### 12. Get Negotiation Log

Retrieve stored JSON log file for a completed negotiation.

**Endpoint:** `GET /api/v1/logs/{session_id}/{room_id}`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID | Session identifier |
| `room_id` | UUID | Room identifier |

**Success Response (200 OK):**

```json
{
  "metadata": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "room_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
    "item_id": "laptop_hp_15",
    "started_at": "2025-11-16T12:00:00.000000",
    "completed_at": "2025-11-16T12:05:00.000000",
    "duration_seconds": 300.5
  },
  "buyer": {
    "buyer_id": "b7c8d9e0-1234-5678-9abc-def012345678",
    "name": "TechCorp Procurement",
    "constraints": {...}
  },
  "sellers": [...],
  "conversation_history": [...],
  "offers_over_time": [
    {
      "round": 1,
      "seller_id": "...",
      "price_per_unit": 580.0,
      "quantity": 50
    }
  ],
  "decision": {
    "decision": "accept",
    "chosen_seller_id": "...",
    "final_price": 550.0,
    "reason": "..."
  },
  "rounds_completed": 5
}
```

**Error Responses:**

- `404 LOG_NOT_FOUND` - Log file does not exist

**Usage Notes:**

- Logs generated automatically after negotiation completion
- Stored in `data/logs/sessions/{session_id}/{room_id}.json`
- Retention: 7 days (configurable via `LOG_RETENTION_DAYS`)

---

## Data Models

### BuyerConfig

```typescript
interface BuyerConfig {
  name: string;                    // 1-50 characters
  shopping_list: ShoppingItem[];   // 1-10 items
}

interface ShoppingItem {
  item_id: string;                 // 1-50 characters
  item_name: string;               // 1-100 characters
  quantity_needed: number;         // >= 1
  min_price_per_unit: number;      // >= 0
  max_price_per_unit: number;      // > min_price_per_unit
}
```

### SellerConfig

```typescript
interface SellerConfig {
  name: string;                    // 1-50 characters
  profile: SellerProfile;
  inventory: InventoryItem[];      // >= 1 item
}

interface SellerProfile {
  priority: 'maximize_profit' | 'customer_retention';
  speaking_style: 'rude' | 'very_sweet';
}

interface InventoryItem {
  item_id: string;                 // 1-50 characters
  item_name: string;               // 1-100 characters
  quantity_available: number;      // >= 1
  cost_price: number;              // >= 0
  selling_price: number;           // > cost_price
  least_price: number;             // cost_price < least_price < selling_price
}
```

### LLMConfig

```typescript
interface LLMConfig {
  model: string;                         // Required, e.g. 'llama-3-8b-instruct'
  temperature?: number;                  // 0.0-1.0, Default: 0.7
  max_tokens?: number;                   // Default: 500
}
```

**Note:** Provider is selected via environment variable `LLM_PROVIDER`, not in request.

### NegotiationRoomInfo

```typescript
interface NegotiationRoomInfo {
  room_id: string;                 // UUID
  item_id: string;
  item_name: string;
  quantity_needed: number;
  buyer_constraints: BuyerConstraints;
  participating_sellers: SellerParticipant[];
  status: string;                  // 'pending', 'in_progress', 'completed'
  reason?: string;                 // Optional reason for status
}

interface SellerParticipant {
  seller_id: string;              // UUID
  seller_name: string;
  initial_price?: number;          // Optional
  current_offer?: object;          // Optional
}

interface BuyerConstraints {
  min_price_per_unit: number;
  max_price_per_unit: number;
}
```

### NegotiationOutcome

```typescript
interface NegotiationOutcome {
  outcome_id: string;              // UUID
  decision_type: 'deal' | 'no_deal';
  selected_seller_id?: string;      // UUID (if deal)
  final_price?: number;            // final_price_per_unit (if deal)
  quantity?: number;                // (if deal)
  total_cost?: number;              // (if deal)
}
```

### Message

```typescript
interface Message {
  message_id: string;
  turn_number: number;
  timestamp: string;               // ISO 8601
  sender_type: 'buyer' | 'seller';
  sender_id?: string;              // UUID (for sellers, null for buyer)
  sender_name: string;
  content: string;                 // 1-1000 characters
  mentioned_agents: string[];      // Array of agent IDs mentioned
}
```

### Offer

```typescript
interface Offer {
  price: number;                  // price_per_unit
  quantity: number;
}

// In NegotiationStateResponse, offers are keyed by seller_id:
interface CurrentOffers {
  [seller_id: string]: Offer;
}
```

---

## Event Types (SSE)

All SSE events follow standardized format with `type` field.

### Connected Event

Sent immediately upon SSE connection establishment.

```json
{
  "type": "connected",
  "room_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
  "timestamp": "2025-11-16T12:00:00.000000"
}
```

### Buyer Message Event

Buyer agent sends a message to sellers.

```json
{
  "type": "message",
  "sender_type": "buyer",
  "sender_name": "TechCorp Procurement",
  "content": "@ElectroMart Can you offer $520 per unit for 50 laptops?",
  "turn_number": 2,
  "timestamp": "2025-11-16T12:00:15.000000"
}
```

### Seller Response Event

Seller agent responds to buyer.

```json
{
  "type": "message",
  "sender_type": "seller",
  "sender_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "sender_name": "ElectroMart",
  "content": "We can meet your price of $520 per unit for 50 units.",
  "turn_number": 2,
  "timestamp": "2025-11-16T12:00:18.000000"
}
```

### Offer Event

Seller makes a price offer.

```json
{
  "type": "offer",
  "seller_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "seller_name": "ElectroMart",
  "price_per_unit": 520.0,
  "quantity": 50,
  "total_price": 26000.0,
  "timestamp": "2025-11-16T12:00:18.000000"
}
```

### Decision Event

Buyer makes final decision.

```json
{
  "type": "decision",
  "decision": "accept",
  "chosen_seller_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "chosen_seller_name": "ElectroMart",
  "final_price": 520.0,
  "final_quantity": 50,
  "total_cost": 26000.0,
  "reason": "Best price within budget constraints",
  "timestamp": "2025-11-16T12:05:00.000000"
}
```

### Round Start Event

New negotiation round begins.

```json
{
  "type": "round_start",
  "round_number": 3,
  "max_rounds": 10,
  "timestamp": "2025-11-16T12:01:00.000000"
}
```

### Negotiation Complete Event

Negotiation has finished (accept/reject/timeout).

```json
{
  "type": "negotiation_complete",
  "room_id": "da74688a-9ae7-44ba-85d5-9bbdccb66a51",
  "outcome": "accepted",
  "rounds_completed": 5,
  "duration_seconds": 300.5,
  "timestamp": "2025-11-16T12:05:00.000000"
}
```

### Heartbeat Event

Keep-alive event sent every 15 seconds during LLM processing.

```json
{
  "type": "heartbeat",
  "timestamp": "2025-11-16T12:00:30.000000"
}
```

### Error Event

Error occurred during negotiation.

```json
{
  "type": "error",
  "error_code": "LLM_TIMEOUT",
  "message": "LLM provider timeout after 30 seconds",
  "retry_count": 2,
  "timestamp": "2025-11-16T12:00:45.000000"
}
```

---

## Usage Examples

### Complete Workflow Example (JavaScript)

```javascript
// 1. Initialize session
const initResponse = await fetch('http://localhost:8000/api/v1/simulation/initialize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    buyer: {
      name: "TechCorp",
      shopping_list: [{
        item_id: "laptop_hp_15",
        item_name: "HP 15 Laptop",
        quantity_needed: 50,
        min_price_per_unit: 400,
        max_price_per_unit: 600
      }]
    },
    sellers: [
      {
        name: "ElectroMart",
        profile: {
          priority: "maximize_profit",
          speaking_style: "rude"
        },
        inventory: [{
          item_id: "laptop_hp_15",
          item_name: "HP 15 Laptop",
          quantity_available: 100,
          cost_price: 400,
          selling_price: 650,
          least_price: 550
        }]
      }
    ],
    llm_config: {
      model: "llama-3-8b-instruct",
      temperature: 0.7,
      max_tokens: 500
    }
  })
});

const session = await initResponse.json();
const roomId = session.negotiation_rooms[0].room_id; // Use room_id from response

// 2. Start negotiation
await fetch(`http://localhost:8000/api/v1/negotiation/${roomId}/start`, {
  method: 'POST'
});

// 3. Connect to SSE stream
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/negotiation/${roomId}/stream`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'connected':
      console.log('✅ Connected to negotiation stream');
      break;
      
    case 'message':
      console.log(`💬 ${data.sender_name}: ${data.content}`);
      break;
      
    case 'offer':
      console.log(`💰 ${data.seller_name} offers $${data.price_per_unit}/unit`);
      break;
      
    case 'decision':
      console.log(`✅ Decision: ${data.decision} - ${data.reason}`);
      break;
      
    case 'negotiation_complete':
      console.log('🏁 Negotiation completed');
      eventSource.close();
      break;
      
    case 'heartbeat':
      console.log('💓 Heartbeat');
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('❌ SSE Error:', error);
};

// 4. Get final summary
setTimeout(async () => {
  const summaryResponse = await fetch(
    `http://localhost:8000/api/v1/simulation/${session.session_id}/summary`
  );
  const summary = await summaryResponse.json();
  console.log('📊 Summary:', summary);
}, 60000); // Wait for negotiation to complete
```

### Python Example

```python
import requests
import json
from sseclient import SSEClient

# 1. Initialize session
response = requests.post(
    'http://localhost:8000/api/v1/simulation/initialize',
    json={
        'buyer': {
            'name': 'TechCorp',
            'shopping_list': [{
                'item_id': 'laptop_hp_15',
                'item_name': 'HP 15 Laptop',
                'quantity_needed': 50,
                'min_price_per_unit': 400,
                'max_price_per_unit': 600
            }]
        },
        'sellers': [{
            'name': 'ElectroMart',
            'profile': {
                'priority': 'maximize_profit',
                'speaking_style': 'rude'
            },
            'inventory': [{
                'item_id': 'laptop_hp_15',
                'item_name': 'HP 15 Laptop',
                'quantity_available': 100,
                'cost_price': 400,
                'selling_price': 650,
                'least_price': 550
            }]
        }],
        'llm_config': {
            'model': 'llama-3-8b-instruct',
            'temperature': 0.7,
            'max_tokens': 500
        }
    }
)

session = response.json()
room_id = session['negotiation_rooms'][0]['room_id']

# 2. Start negotiation
requests.post(f'http://localhost:8000/api/v1/negotiation/{room_id}/start')

# 3. Connect to SSE stream
stream_url = f'http://localhost:8000/api/v1/negotiation/{room_id}/stream'
client = SSEClient(stream_url)

for event in client.events():
    data = json.loads(event.data)
    
    if data['type'] == 'connected':
        print('✅ Connected to negotiation stream')
    elif data['type'] == 'message':
        print(f"💬 {data['sender_name']}: {data['content']}")
    elif data['type'] == 'offer':
        print(f"💰 {data['seller_name']} offers ${data['price_per_unit']}/unit")
    elif data['type'] == 'decision':
        print(f"✅ Decision: {data['decision']} - {data['reason']}")
    elif data['type'] == 'negotiation_complete':
        print('🏁 Negotiation completed')
        break

# 4. Get summary
summary = requests.get(
    f'http://localhost:8000/api/v1/simulation/{session["session_id"]}/summary'
).json()
print('📊 Summary:', json.dumps(summary, indent=2))
```

---

## Rate Limits and Quotas

**Current Version:** No rate limits enforced

Future versions may implement:
- Per-IP rate limiting
- Concurrent session limits per user
- Maximum message length restrictions

---

## Versioning

**Current Version:** 1.0.0  
**API Prefix:** `/api/v1`

### Version History

- **1.0.0** (2025-11-16) - Initial production release
  - Complete REST API implementation
  - SSE streaming support
  - Full CRUD operations for sessions and negotiations

### Breaking Changes Policy

- Major version changes (`v2`, `v3`) may introduce breaking changes
- Minor/patch versions maintain backward compatibility
- Deprecated endpoints will be supported for at least 6 months

---

## Support and Contact

**Backend Repository:** [Link to repository]  
**API Base URL:** `http://localhost:8000` (development)  
**Documentation:** This file  
**Testing Report:** `PHASE_4_TESTING_REPORT.md`

### Common Issues

1. **SSE Connection Drops:** Expected after negotiation completes. Reconnect for new negotiations.
2. **LLM Timeout:** Increase `LM_STUDIO_TIMEOUT` env variable (default: 30s)
3. **Session Not Found:** Ensure session wasn't deleted or expired (1 hour TTL)

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-11-16  
**Status:** Production Ready ✅

