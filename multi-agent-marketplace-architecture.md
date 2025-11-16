# Multi-Agent Ecommerce Marketplace - Final Backend Architecture
## FastAPI Implementation Plan & Frontend Integration Guide

**Version:** 2.0 (Final)  
**Date:** November 15, 2025  
**Purpose:** Complete backend specification for frontend integration

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Structure](#2-project-structure)
3. [FastAPI Endpoints Specification](#3-fastapi-endpoints-specification)
4. [Request/Response Schemas](#4-requestresponse-schemas)
5. [WebSocket & SSE Architecture](#5-websocket--sse-architecture)
6. [Frontend Integration Guide](#6-frontend-integration-guide)
7. [State Management Flow](#7-state-management-flow)
8. [Error Handling & Status Codes](#8-error-handling--status-codes)
9. [Environment Configuration](#9-environment-configuration)
10. [Implementation Checklist](#10-implementation-checklist)

---

## 1. Executive Summary

### System Overview
A FastAPI-based backend that orchestrates opaque multi-agent negotiations between one buyer and up to 10 sellers using LangGraph. The buyer has NO knowledge of seller internal costs, strategies, or profiles - only sees what sellers choose to reveal in chat. All state is persisted in SQLite database to support multiple negotiation runs per configuration session.

### Key Capabilities for Frontend
- **Configuration APIs:** Create buyer, sellers, and initialize marketplace sessions
- **Real-time Streaming:** SSE endpoints for live negotiation updates
- **State Inspection:** Query current negotiation status, offers, and history
- **Session Management:** Create, monitor, and retrieve completed sessions with multiple negotiation runs
- **LLM Backend:** LM Studio integration for on-device inference
- **Database Persistence:** SQLite storage for all configurations and negotiation logs

### Technology Stack
- **Framework:** FastAPI 0.104+
- **Database:** SQLite 3 with SQLAlchemy ORM
- **Orchestration:** LangGraph + LangChain
- **LLM Provider:** LM Studio (local inference)
- **Async:** asyncio, sse-starlette
- **Validation:** Pydantic v2
- **Streaming:** Server-Sent Events (SSE)

---

## 2. Project Structure

At the repository root, the codebase is split for two teams:

- `backend/`: Python backend (FastAPI + LangGraph + LM Studio integration)
- `frontend/`: Next.js frontend (configuration wizard, negotiation UI, summary views)

```text
backend/
│
├── pyproject.toml or requirements.txt   # Backend dependencies only
├── data/                                # Database and logs (backend-local)
│   ├── marketplace.db                   # SQLite database
│   └── logs/
│       └── app.log
│
├── app/                                 # Backend Python package
│   ├── __init__.py
│   │
│   ├── main.py                          # FastAPI application entry point
│   │                                    # - Initializes app
│   │                                    # - Registers middleware
│   │                                    # - Includes API routers
│   │                                    # - Startup/shutdown hooks
│   │
│   ├── api/                             # API route handlers (frontend contract)
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py                # API router aggregation for v1
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── simulation.py        # Session initialization
│   │   │       ├── negotiation.py       # Negotiation control
│   │   │       ├── streaming.py         # SSE streaming endpoints
│   │   │       └── status.py            # Health & status checks
│   │
│   ├── core/                            # Core infrastructure & configuration
│   │   ├── __init__.py
│   │   ├── config.py                    # App configuration (Pydantic settings)
│   │   ├── database.py                  # SQLite/SQLAlchemy engine & session
│   │   ├── models.py                    # SQLAlchemy ORM models (DB tables)
│   │   └── session_manager.py           # Session & negotiation-run lifecycle
│   │
│   ├── models/                          # Pydantic / API schemas (domain layer)
│   │   ├── __init__.py
│   │   ├── agent.py                     # Buyer & Seller config models
│   │   ├── negotiation.py               # NegotiationRoom, BuyerDecision, etc.
│   │   ├── message.py                   # Message & Offer shapes for API
│   │   └── api_schemas.py               # Request/response models for endpoints
│   │
│   ├── services/                        # Business logic services
│   │   ├── __init__.py
│   │   ├── seller_selection.py          # Seller matching per buyer item
│   │   ├── message_router.py            # @mention parsing & routing
│   │   ├── visibility_filter.py         # Conversation visibility per agent
│   │   ├── decision_engine.py           # Buyer decision prompts & reasoning
│   │   └── summary_service.py           # Session summary builder
│   │
│   ├── agents/                          # LangGraph agent implementations
│   │   ├── __init__.py
│   │   ├── buyer_agent.py               # Buyer agent node logic
│   │   ├── seller_agent.py              # Seller agent node logic
│   │   ├── prompts.py                   # Shared prompt templates
│   │   └── graph_builder.py             # LangGraph workflow construction
│   │
│   ├── llm/                             # LLM integration layer (LM Studio only)
│   │   ├── __init__.py
│   │   ├── lm_studio.py                 # LM Studio adapter (sync/async, errors)
│   │   └── streaming_handler.py         # Utilities to stream LLM output to SSE
│   │
│   ├── utils/                           # Cross-cutting utilities
│   │   ├── __init__.py
│   │   ├── logger.py                    # Structured logging
│   │   ├── validators.py                # Custom validators
│   │   └── exceptions.py                # Custom exception types
│   │
│   └── middleware/                      # FastAPI middleware
│       ├── __init__.py
│       ├── cors.py                      # CORS configuration
│       └── error_handler.py             # Global error handling
│
└── tests/                               # Backend test suite
    ├── __init__.py
    ├── unit/
    │   ├── test_seller_selection.py
    │   ├── test_message_routing.py
    │   ├── test_visibility_filter.py
    │   └── test_agents.py              # Buyer/seller agents in isolation
    ├── integration/
    │   ├── test_api_endpoints.py       # REST/SSE contract tests
    │   └── test_negotiation_flow.py    # End-to-end negotiation flow
    └── fixtures/
        ├── sample_configs.py           # Example buyer/seller configs
        └── mock_llm.py                 # Fake LM Studio adapter for tests
```

The **frontend** folder uses a modular Next.js (App Router) structure that mirrors backend concepts:

```text
frontend/
│
├── package.json
├── next.config.js
├── tsconfig.json
├── public/                             # Static assets (logos, icons)
└── src/
    ├── app/                            # Next.js App Router entrypoints
    │   ├── layout.tsx                  # Global layout, providers, theme
    │   ├── page.tsx                    # Landing / home (start new episode)
    │   ├── config/                     # Episode configuration wizard
    │   │   └── page.tsx
    │   ├── negotiations/               # Negotiation dashboard & rooms
    │   │   ├── page.tsx                # List of negotiation rooms
    │   │   └── [roomId]/               # Per-item negotiation room
    │   │       └── page.tsx
    │   └── summary/                    # Final receipt / session summary
    │       └── page.tsx
    │
    ├── features/                       # Feature modules aligned to backend domains
    │   ├── episode-config/             # Buyer + sellers + LLM config wizard
    │   │   ├── components/             # Forms, steppers, seller cards
    │   │   ├── hooks/                  # useEpisodeConfig, useSellerForm, etc.
    │   │   └── state.ts                # Local feature state helpers
    │   ├── negotiation-room/           # Per-item chat UI & SSE handling
    │   │   ├── components/             # Chat window, offers panel, toolbar
    │   │   ├── hooks/                  # useNegotiationStream, useNegotiationRoom
    │   │   └── state.ts
    │   ├── summary-receipt/            # Final receipt & metrics
    │   │   ├── components/             # Summary cards, tables, metrics
    │   │   └── hooks/                  # useSessionSummary
    │   └── shared/                     # Feature-level shared pieces (breadcrumbs, badges)
    │
    ├── lib/                            # API clients & shared logic
    │   ├── api/                        # Mirrors backend endpoints
    │   │   ├── client.ts               # Fetch wrapper + error handling
    │   │   ├── simulation.ts           # /simulation endpoints (init, summary)
    │   │   ├── negotiation.ts          # /negotiation endpoints + SSE helpers
    │   │   └── status.ts               # /health, /llm/status
    │   ├── forms/                      # Zod schemas mirroring backend Pydantic models
    │   ├── router.ts                   # Route helpers (config, negotiations, summary)
    │   └── constants.ts                # Enums: seller priorities, speaking styles, etc.
    │
    ├── store/                          # Global state (e.g., Zustand slices)
    │   ├── sessionStore.ts             # Active session/episode metadata
    │   ├── configStore.ts              # Draft configuration during wizard
    │   └── negotiationStore.ts         # Per-room messages, offers, active room
    │
    ├── components/                     # Shared UI primitives (buttons, inputs, modals)
    ├── styles/                         # Global styles, Tailwind config or CSS modules
    └── utils/                          # Helpers (formatting, @mention highlighting, etc.)
```

---

## 3. FastAPI Endpoints Specification

### 3.1 Base URL
```
Development: http://localhost:8000
Production: https://your-domain.com
```

### 3.2 API Versioning
All endpoints prefixed with `/api/v1`

---

### 3.3 Endpoint Catalog

#### **A. Simulation Management**

##### 1. Initialize Marketplace Session
```http
POST /api/v1/simulation/initialize
```

**Purpose:** Create a new marketplace session with buyer, sellers, and LLM configuration

**Request Body:**
```json
{
  "buyer": {
    "name": "John Doe",
    "shopping_list": [
      {
        "item_id": "item_001",
        "item_name": "Laptop",
        "quantity_needed": 2,
        "min_price_per_unit": 900,
        "max_price_per_unit": 1500
      },
      {
        "item_id": "item_002", 
        "item_name": "Mouse",
        "quantity_needed": 5,
        "min_price_per_unit": 10,
        "max_price_per_unit": 25
      }
    ]
  },
  "sellers": [
    {
      "name": "TechStore",
      "inventory": [
        {
          "item_id": "item_001",
          "item_name": "Laptop",
          "cost_price": 800,
          "selling_price": 1200,
          "least_price": 1000,
          "quantity_available": 10
        }
      ],
      "profile": {
        "priority": "customer_retention",
        "speaking_style": "very_sweet"
      }
    },
    {
      "name": "GadgetHub",
      "inventory": [
        {
          "item_id": "item_001",
          "item_name": "Laptop",
          "cost_price": 750,
          "selling_price": 1150,
          "least_price": 950,
          "quantity_available": 5
        }
      ],
      "profile": {
        "priority": "maximize_profit",
        "speaking_style": "rude"
      }
    }
  ],
  "llm_config": {
    "model": "llama-3-8b-instruct",
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-15T10:30:00Z",
  "buyer_id": "buyer_123",
  "seller_ids": ["seller_001", "seller_002"],
  "negotiation_rooms": [
    {
      "room_id": "room_laptop_001",
      "item_id": "item_001",
      "item_name": "Laptop",
      "quantity_needed": 2,
      "buyer_constraints": {
        "min_price_per_unit": 900,
        "max_price_per_unit": 1500
      },
      "participating_sellers": [
        {
          "seller_id": "seller_001",
          "seller_name": "TechStore"
        },
        {
          "seller_id": "seller_002",
          "seller_name": "GadgetHub"
        }
      ],
      "status": "pending"
    },
    {
      "room_id": "room_mouse_002",
      "item_id": "item_002",
      "item_name": "Mouse",
      "quantity_needed": 5,
      "participating_sellers": [],
      "status": "no_sellers_available",
      "reason": "No sellers have this item in inventory"
    }
  ],
  "total_rooms": 1,
  "skipped_items": ["Mouse"]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid configuration (e.g., negative prices, invalid enum values)
- `500 Internal Server Error`: LLM provider initialization failed

---

##### 2. Get Session Details
```http
GET /api/v1/simulation/{session_id}
```

**Purpose:** Retrieve complete session information

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "created_at": "2025-11-15T10:30:00Z",
  "buyer": {
    "id": "buyer_123",
    "name": "John Doe"
  },
  "sellers": [
    {"id": "seller_001", "name": "TechStore"},
    {"id": "seller_002", "name": "GadgetHub"}
  ],
  "negotiation_rooms": [
    {
      "room_id": "room_laptop_001",
      "item_name": "Laptop",
      "status": "active",
      "current_round": 3,
      "participating_sellers_count": 2
    }
  ],
  "llm_provider": "lm_studio"
}
```

---

##### 3. Delete Session
```http
DELETE /api/v1/simulation/{session_id}
```

**Purpose:** Cleanup session and free resources

**Response (200 OK):**
```json
{
  "message": "Session deleted successfully",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "logs_saved": true,
  "log_path": "/logs/sessions/session_550e8400/"
}
```

---

#### **B. Negotiation Control**

##### 4. Start Negotiation for Item
```http
POST /api/v1/negotiation/{room_id}/start
```

**Purpose:** Begin negotiation for a specific item

**Response (200 OK):**
```json
{
  "room_id": "room_laptop_001",
  "status": "started",
  "item_name": "Laptop",
  "participating_sellers": ["TechStore", "GadgetHub"],
  "buyer_opening_message": "Hello everyone! I'm looking for 2 laptops. What are your best offers?",
  "stream_url": "/api/v1/negotiation/room_laptop_001/stream"
}
```

**Error Responses:**
- `404 Not Found`: Room ID doesn't exist
- `409 Conflict`: Negotiation already started

---

##### 5. Send Buyer Message (Manual Override)
```http
POST /api/v1/negotiation/{room_id}/message
```

**Purpose:** Allow frontend to manually send buyer messages (optional, for testing)

**Request Body:**
```json
{
  "message": "Hey @TechStore and @GadgetHub, can you both do $1000 per laptop?"
}
```

**Response (200 OK):**
```json
{
  "message_id": "msg_001",
  "timestamp": "2025-11-15T10:35:00Z",
  "mentioned_sellers": ["seller_001", "seller_002"],
  "processing": true
}
```

---

##### 6. Force Buyer Decision
```http
POST /api/v1/negotiation/{room_id}/decide
```

**Purpose:** Trigger buyer to make final decision (if LLM isn't auto-deciding)

**Request Body (Optional):**
```json
{
  "force_select_seller": "seller_001"  // Optional: override LLM decision
}
```

**Response (200 OK):**
```json
{
  "room_id": "room_laptop_001",
  "decision_made": true,
  "selected_seller": {
    "seller_id": "seller_001",
    "seller_name": "TechStore",
    "final_price": 1050,
    "quantity": 2
  },
  "decision_reason": "TechStore offered the best price within budget and was very responsive",
  "total_rounds": 5,
  "negotiation_duration_seconds": 145
}
```

---

#### **C. Real-time Streaming**

##### 7. Stream Negotiation Events (SSE)
```http
GET /api/v1/negotiation/{room_id}/stream
```

**Purpose:** Server-Sent Events endpoint for real-time negotiation updates

**Headers:**
```
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

**Event Stream Format:**

```
event: buyer_message
data: {"sender": "buyer", "message": "Hello @TechStore...", "timestamp": "2025-11-15T10:30:01Z", "mentioned_sellers": ["TechStore"]}

event: seller_response
data: {"sender": "seller_001", "seller_name": "TechStore", "message": "Hi! I can offer $1150 for...", "timestamp": "2025-11-15T10:30:15Z", "updated_offer": {"price": 1150, "quantity": 2}}

event: seller_response
data: {"sender": "seller_002", "seller_name": "GadgetHub", "message": "Best I can do is $1100", "timestamp": "2025-11-15T10:30:18Z", "updated_offer": {"price": 1100, "quantity": 2}}

event: buyer_message
data: {"sender": "buyer", "message": "Thanks! @GadgetHub that's close...", "timestamp": "2025-11-15T10:30:45Z", "mentioned_sellers": ["GadgetHub"]}

event: negotiation_complete
data: {"status": "completed", "selected_seller": "seller_002", "final_price": 1080, "reason": "Best price offer"}

event: error
data: {"error": "LLM timeout", "retry_in_seconds": 3}

event: heartbeat
data: {"status": "active", "current_round": 3}
```

**Event Types:**
- `buyer_message`: Buyer sends message
- `seller_response`: Seller responds (includes updated offer)
- `negotiation_complete`: Buyer made final decision
- `error`: Error occurred (with retry info)
- `heartbeat`: Keep-alive ping (every 15s)

**Frontend Implementation Example (JavaScript):**
```javascript
const eventSource = new EventSource('/api/v1/negotiation/room_laptop_001/stream');

eventSource.addEventListener('buyer_message', (e) => {
  const data = JSON.parse(e.data);
  displayMessage('buyer', data.message, data.timestamp);
});

eventSource.addEventListener('seller_response', (e) => {
  const data = JSON.parse(e.data);
  displayMessage(data.seller_name, data.message, data.timestamp);
  updateOffer(data.seller_name, data.updated_offer);
});

eventSource.addEventListener('negotiation_complete', (e) => {
  const data = JSON.parse(e.data);
  showDecision(data.selected_seller, data.final_price);
  eventSource.close();
});
```

---

#### **D. State & History**

##### 8. Get Negotiation State
```http
GET /api/v1/negotiation/{room_id}/state
```

**Query Parameters:**
- `agent_id` (optional): Filter conversation by agent perspective
- `agent_type` (optional): "buyer" or "seller"

**Response (200 OK):**
```json
{
  "room_id": "room_laptop_001",
  "item_name": "Laptop",
  "status": "active",
  "current_round": 3,
  "max_rounds": 10,
  "conversation_history": [
    {
      "turn": 1,
      "timestamp": "2025-11-15T10:30:01Z",
      "sender_type": "buyer",
      "sender_name": "John Doe",
      "message": "Hello @TechStore and @GadgetHub! Looking for 2 laptops.",
      "mentioned_agents": ["seller_001", "seller_002"]
    },
    {
      "turn": 2,
      "timestamp": "2025-11-15T10:30:15Z",
      "sender_type": "seller",
      "sender_id": "seller_001",
      "sender_name": "TechStore",
      "message": "Hi there! I can offer $1150 per laptop...",
      "offer": {"price": 1150, "quantity": 2}
    }
  ],
  "current_offers": {
    "seller_001": {
      "seller_name": "TechStore",
      "price": 1100,
      "quantity": 2,
      "last_updated": "2025-11-15T10:32:00Z"
    },
    "seller_002": {
      "seller_name": "GadgetHub",
      "price": 1080,
      "quantity": 2,
      "last_updated": "2025-11-15T10:32:05Z"
    }
  },
  "buyer_constraints": {
    "min_price_per_unit": 900,
    "max_price_per_unit": 1500
  }
}
```

**With Agent Filtering (Seller Perspective):**
```http
GET /api/v1/negotiation/{room_id}/state?agent_id=seller_001&agent_type=seller
```

**Response:** Only messages visible to that seller (buyer messages mentioning them + their own)

---

##### 9. Get Session Summary
```http
GET /api/v1/simulation/{session_id}/summary
```

**Purpose:** Get final summary of all negotiations in session

**Response (200 OK):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "buyer_name": "John Doe",
  "total_items_requested": 2,
  "completed_purchases": 1,
  "failed_purchases": 1,
  "purchases": [
    {
      "item_name": "Laptop",
      "quantity": 2,
      "selected_seller": "GadgetHub",
      "final_price_per_unit": 1080,
      "total_cost": 2160,
      "negotiation_rounds": 5,
      "duration_seconds": 145
    }
  ],
  "failed_items": [
    {
      "item_name": "Mouse",
      "reason": "No sellers available"
    }
  ],
  "total_cost_summary": {
    "total_spent": 2160,
    "items_purchased": 1,
    "average_savings_per_item": 420
  },
  "negotiation_metrics": {
    "average_rounds": 5,
    "average_duration_seconds": 145,
    "total_messages_exchanged": 18
  }
}
```

---

##### 10. Get Saved Negotiation Log
```http
GET /api/v1/logs/{session_id}/{room_id}
```

**Purpose:** Retrieve saved negotiation log (after completion)

**Response (200 OK):**
Returns the complete JSON log file (see Persistence section for schema)

---

#### **E. Health & Status**

##### 11. Health Check
```http
GET /api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T10:30:00Z",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "url": "sqlite:///data/marketplace.db"
  },
  "llm_provider": {
    "lm_studio": "available"
  }
}
```

---

##### 12. LLM Provider Status
```http
GET /api/v1/llm/status
```

**Purpose:** Check if LLM providers are reachable

**Response (200 OK):**
```json
{
  "lm_studio": {
    "available": true,
    "base_url": "http://localhost:1234/v1",
    "models": ["llama-3-8b-instruct", "mistral-7b"]
  },
  "database": {
    "connected": true,
    "total_sessions": 15,
    "total_negotiations": 47
  }
}
```

---

## 4. SQLite Database Schema

### 4.1 Database Design Principles

**Key Design Decisions:**
- **Per-item pricing constraints:** No global budget, only min/max per item
- **Opaque seller information:** Buyer cannot access seller costs, least prices, or profiles
- **Session-based configurations:** Support multiple negotiation runs per session
- **Complete conversation logs:** All messages stored for replay and analysis

### 4.2 Database Tables

#### Sessions Table

Conceptually, a **Session** here corresponds to a single negotiation **Episode** in the product and UX documents (one configured world of buyer + sellers + per-item negotiations).
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('draft', 'active', 'completed')) DEFAULT 'draft',
    llm_model VARCHAR(100) NOT NULL,
    llm_temperature REAL DEFAULT 0.7,
    llm_max_tokens INTEGER DEFAULT 500
);
```

#### Buyers Table
```sql
CREATE TABLE buyers (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Buyer Items Table (Shopping List)
```sql
CREATE TABLE buyer_items (
    id UUID PRIMARY KEY,
    buyer_id UUID NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,
    item_id VARCHAR(50) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    quantity_needed INTEGER NOT NULL CHECK (quantity_needed > 0),
    min_price_per_unit REAL NOT NULL CHECK (min_price_per_unit >= 0),
    max_price_per_unit REAL NOT NULL CHECK (max_price_per_unit > min_price_per_unit),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Sellers Table
```sql
CREATE TABLE sellers (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    priority VARCHAR(20) CHECK (priority IN ('customer_retention', 'maximize_profit')) NOT NULL,
    speaking_style VARCHAR(20) CHECK (speaking_style IN ('rude', 'very_sweet')) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Seller Inventory Table
```sql
CREATE TABLE seller_inventory (
    id UUID PRIMARY KEY,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    item_id VARCHAR(50) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    cost_price REAL NOT NULL CHECK (cost_price >= 0),
    selling_price REAL NOT NULL CHECK (selling_price > cost_price),
    least_price REAL NOT NULL CHECK (least_price > cost_price AND least_price < selling_price),
    quantity_available INTEGER NOT NULL CHECK (quantity_available >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(seller_id, item_id)
);
```

#### Negotiation Runs Table
```sql
CREATE TABLE negotiation_runs (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    buyer_item_id UUID NOT NULL REFERENCES buyer_items(id) ON DELETE CASCADE,
    status VARCHAR(20) CHECK (status IN ('pending', 'active', 'completed', 'no_sellers_available', 'aborted')) DEFAULT 'pending',
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    current_round INTEGER DEFAULT 0,
    max_rounds INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Negotiation Participants Table
```sql
CREATE TABLE negotiation_participants (
    id UUID PRIMARY KEY,
    negotiation_run_id UUID NOT NULL REFERENCES negotiation_runs(id) ON DELETE CASCADE,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(negotiation_run_id, seller_id)
);
```

#### Messages Table
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    negotiation_run_id UUID NOT NULL REFERENCES negotiation_runs(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    sender_type VARCHAR(10) CHECK (sender_type IN ('buyer', 'seller')) NOT NULL,
    sender_id UUID NOT NULL, -- References buyers.id or sellers.id
    sender_name VARCHAR(100) NOT NULL,
    message_text TEXT NOT NULL,
    mentioned_agents TEXT, -- JSON array of mentioned seller IDs
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Offers Table
```sql
CREATE TABLE offers (
    id UUID PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    price_per_unit REAL NOT NULL CHECK (price_per_unit > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    conditions TEXT, -- Optional conditions or terms
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Negotiation Outcomes Table
```sql
CREATE TABLE negotiation_outcomes (
    id UUID PRIMARY KEY,
    negotiation_run_id UUID NOT NULL REFERENCES negotiation_runs(id) ON DELETE CASCADE,
    decision_type VARCHAR(20) CHECK (decision_type IN ('deal', 'no_deal')) NOT NULL,
    selected_seller_id UUID REFERENCES sellers(id),
    final_price_per_unit REAL,
    quantity INTEGER,
    total_cost REAL,
    decision_reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 Database Indexes

```sql
-- Performance indexes
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_buyers_session ON buyers(session_id);
CREATE INDEX idx_buyer_items_buyer ON buyer_items(buyer_id);
CREATE INDEX idx_sellers_session ON sellers(session_id);
CREATE INDEX idx_seller_inventory_seller ON seller_inventory(seller_id);
CREATE INDEX idx_seller_inventory_item ON seller_inventory(item_id);
CREATE INDEX idx_negotiation_runs_session ON negotiation_runs(session_id);
CREATE INDEX idx_negotiation_runs_status ON negotiation_runs(status);
CREATE INDEX idx_messages_negotiation ON messages(negotiation_run_id);
CREATE INDEX idx_messages_turn ON messages(negotiation_run_id, turn_number);
CREATE INDEX idx_offers_message ON offers(message_id);
CREATE INDEX idx_offers_seller ON offers(seller_id);
CREATE INDEX idx_outcomes_negotiation ON negotiation_outcomes(negotiation_run_id);
```

### 4.4 Key Constraints & Rules

**Opaque Information Model:**
- Buyer queries CANNOT join directly to seller_inventory cost/least_price fields
- API endpoints must filter seller internal data before returning to frontend
- Only sellers see their own cost_price, selling_price, least_price

**Per-Item Pricing:**
- No global budget table - constraints are per buyer_items row
- min_price_per_unit < max_price_per_unit enforced at DB level
- Final deals must be within [min_price_per_unit, max_price_per_unit] range

**Session Lifecycle:**
- One session can have multiple negotiation_runs for same or different items
- Seller inventory quantities can be decremented after successful deals
- All negotiation history preserved even after session completion

---

## 5. Request/Response Schemas

### 5.1 Core Data Models (Pydantic)

#### Agent Configuration Models

```python
# Buyer Configuration
BuyerConfig:
  - name: str
  - shopping_list: List[ShoppingItem]

ShoppingItem:
  - item_id: str
  - item_name: str
  - quantity_needed: int (>= 1)
  - min_price_per_unit: float (>= 0)
  - max_price_per_unit: float (> min_price_per_unit)

# Seller Configuration
SellerConfig:
  - name: str
  - inventory: List[InventoryItem]
  - profile: SellerProfile

InventoryItem:
  - item_id: str
  - item_name: str
  - cost_price: float (>= 0)
  - selling_price: float (> cost_price)
  - least_price: float (cost_price < least_price < selling_price)
  - quantity_available: int (>= 1)

SellerProfile:
  - priority: Enum["customer_retention", "maximize_profit"]
  - speaking_style: Enum["rude", "very_sweet"]

# LLM Configuration
LLMConfig:
  - model: str
  - temperature: float (0.0 - 1.0, default: 0.7)
  - max_tokens: int (default: 500)
```

#### Negotiation Models

```python
# Negotiation Room
NegotiationRoom:
  - room_id: UUID
  - session_id: UUID
  - item_id: str
  - item_name: str
  - quantity_needed: int
  - buyer_id: UUID
  - participating_sellers: List[SellerParticipant]
  - status: Enum["pending", "active", "completed", "no_sellers_available"]
  - created_at: datetime

SellerParticipant:
  - seller_id: UUID
  - seller_name: str
  - initial_price: float
  - current_offer: Optional[Offer]

Offer:
  - price: float
  - quantity: int
  - conditions: Optional[str]
  - timestamp: datetime

# Message
Message:
  - message_id: UUID
  - room_id: UUID
  - turn: int
  - timestamp: datetime
  - sender_id: UUID
  - sender_type: Enum["buyer", "seller"]
  - sender_name: str
  - message: str
  - mentioned_agents: List[UUID]
  - visibility: List[UUID]

# Decision
BuyerDecision:
  - selected_seller_id: Optional[UUID]
  - seller_name: Optional[str]
  - final_price: Optional[float]
  - quantity: int
  - decision_reason: str
  - timestamp: datetime
```

#### API Request/Response Models

```python
# Initialize Session Request
InitializeSessionRequest:
  - buyer: BuyerConfig
  - sellers: List[SellerConfig]  # Max 10
  - llm_config: LLMConfig

# Initialize Session Response
InitializeSessionResponse:
  - session_id: UUID
  - created_at: datetime
  - buyer_id: UUID
  - seller_ids: List[UUID]
  - negotiation_rooms: List[NegotiationRoomInfo]
  - total_rooms: int
  - skipped_items: List[str]

NegotiationRoomInfo:
  - room_id: UUID
  - item_id: str
  - item_name: str
  - quantity_needed: int
  - buyer_constraints: BuyerConstraints
  - participating_sellers: List[SellerParticipant]
  - status: str
  - reason: Optional[str]

BuyerConstraints:
  - min_price_per_unit: float
  - max_price_per_unit: float

# Send Message Request
SendMessageRequest:
  - message: str

# Send Message Response
SendMessageResponse:
  - message_id: UUID
  - timestamp: datetime
  - mentioned_sellers: List[UUID]
  - processing: bool

# Negotiation State Response
NegotiationStateResponse:
  - room_id: UUID
  - item_name: str
  - status: str
  - current_round: int
  - max_rounds: int
  - conversation_history: List[Message]
  - current_offers: Dict[str, Offer]
  - buyer_constraints: BuyerConstraints

# Summary Response
SessionSummaryResponse:
  - session_id: UUID
  - buyer_name: str
  - total_items_requested: int
  - completed_purchases: int
  - failed_purchases: int
  - purchases: List[PurchaseSummary]
  - failed_items: List[FailedItem]
  - total_cost_summary: TotalCostSummary
  - negotiation_metrics: NegotiationMetrics

PurchaseSummary:
  - item_name: str
  - quantity: int
  - selected_seller: str
  - final_price_per_unit: float
  - total_cost: float
  - negotiation_rounds: int
  - duration_seconds: int

FailedItem:
  - item_name: str
  - reason: str

TotalCostSummary:
  - total_spent: float
  - items_purchased: int
  - average_savings_per_item: float

NegotiationMetrics:
  - average_rounds: float
  - average_duration_seconds: float
  - total_messages_exchanged: int
```

### 5.2 Validation Rules

**Enforced by Pydantic Validators:**

1. **Pricing Constraints:**
   - `cost_price >= 0`
   - `selling_price > cost_price`
   - `cost_price < least_price < selling_price`

2. **Per-Item Price Constraints:**
   - `min_price_per_unit >= 0`
   - `max_price_per_unit > min_price_per_unit`

3. **Quantity Constraints:**
   - `quantity_needed >= 1`
   - `quantity_available >= 1`

4. **Seller Limit:**
   - Max 10 sellers per session

5. **String Validation:**
   - Names: 1-50 characters, no special characters
   - Item IDs: 1-100 characters
   - Messages: 1-1000 characters

6. **Enum Validation:**
   - Priority: Only "customer_retention" or "maximize_profit"
   - Speaking Style: Only "rude" or "very_sweet"

7. **Opaque Information Model:**
   - Buyer requests MUST NOT include seller cost/least price data
   - Seller internal profiles hidden from buyer-visible responses

---

## 6. WebSocket & SSE Architecture

### 6.1 Why SSE (Server-Sent Events)?

**Chosen over WebSockets because:**
- Unidirectional (server → client) is sufficient
- Simpler implementation
- Automatic reconnection handling
- Works over HTTP/HTTPS (no protocol upgrade needed)
- Built-in event typing

### 6.2 SSE Event Flow

```
Frontend                     Backend (FastAPI)                LangGraph
   |                              |                                |
   |-- GET /stream ------------>  |                                |
   |                              |                                |
   |<-- Connection: keep-alive --|                                |
   |                              |                                |
   |                              |-- Start Negotiation -------->  |
   |                              |                                |
   |                              |<-- Buyer Message Generated -- |
   |<-- event: buyer_message ----| (Stream tokens)                |
   |                              |                                |
   |                              |-- Route to Sellers --------->  |
   |                              |                                |
   |                              |<-- Seller1 Response --------- |
   |<-- event: seller_response --| (Stream tokens)                |
   |                              |                                |
   |                              |<-- Seller2 Response --------- |
   |<-- event: seller_response --| (Stream tokens)                |
   |                              |                                |
   |                              |-- Check Decision ----------->  |
   |                              |                                |
   |                              |<-- Buyer Decides ------------ |
   |<-- event: negotiation_complete|                               |
   |                              |                                |
   |-- Close Connection ------->  |                                |
```

### 6.3 SSE Connection Management

**Connection Lifecycle:**

1. **Establish:**
   - Frontend opens EventSource connection
   - Backend creates async generator
   - Send initial `connected` event

2. **Heartbeat:**
   - Send `heartbeat` event every 15 seconds
   - Frontend monitors for timeouts
   - Reconnect if no events for 30 seconds

3. **Error Handling:**
   - Send `error` event with details
   - Include `retry_in_seconds` field
   - Frontend auto-retries with exponential backoff

4. **Close:**
   - Send `negotiation_complete` or `error` (fatal)
   - Backend closes generator
   - Frontend closes EventSource

**Backend Implementation Pattern:**

```python
# Async generator for SSE
async def negotiation_stream(room_id: str):
    try:
        yield {
            "event": "connected",
            "data": {"room_id": room_id, "status": "ready"}
        }
        
        async for event in langgraph_executor(room_id):
            yield {
                "event": event.type,
                "data": event.data
            }
            
            # Send heartbeat every 15s
            if time_since_last_event > 15:
                yield {
                    "event": "heartbeat",
                    "data": {"status": "active"}
                }
                
    except Exception as e:
        yield {
            "event": "error",
            "data": {"error": str(e), "fatal": True}
        }
```

### 6.4 Frontend SSE Handling Best Practices

**Recommended Frontend Implementation:**

```javascript
class NegotiationStream {
  constructor(roomId) {
    this.roomId = roomId;
    this.eventSource = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    this.eventSource = new EventSource(
      `/api/v1/negotiation/${this.roomId}/stream`
    );

    this.eventSource.addEventListener('connected', (e) => {
      console.log('Connected to negotiation stream');
      this.reconnectAttempts = 0;
    });

    this.eventSource.addEventListener('buyer_message', (e) => {
      const data = JSON.parse(e.data);
      this.handleBuyerMessage(data);
    });

    this.eventSource.addEventListener('seller_response', (e) => {
      const data = JSON.parse(e.data);
      this.handleSellerResponse(data);
    });

    this.eventSource.addEventListener('negotiation_complete', (e) => {
      const data = JSON.parse(e.data);
      this.handleComplete(data);
      this.disconnect();
    });

    this.eventSource.addEventListener('error', (e) => {
      if (e.data) {
        const errorData = JSON.parse(e.data);
        if (errorData.fatal) {
          this.handleError(errorData);
          this.disconnect();
        } else {
          this.attemptReconnect();
        }
      }
    });

    this.eventSource.onerror = () => {
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.attemptReconnect();
      } else {
        this.handleFatalError('Max reconnection attempts reached');
      }
    };
  }

  attemptReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    setTimeout(() => this.connect(), delay);
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  // Handler methods
  handleBuyerMessage(data) { /* Update UI */ }
  handleSellerResponse(data) { /* Update UI */ }
  handleComplete(data) { /* Show final decision */ }
  handleError(error) { /* Show error message */ }
}
```

---

## 7. Frontend Integration Guide

### 7.1 Complete Workflow from Frontend Perspective

#### **Phase 1: Configuration**

**Step 1.1: User Fills Configuration Form**

Form should collect:
- Buyer name, shopping list (items + quantities and per-item price ranges)
- Sellers (up to 10): name, inventory, profile

**Step 1.2: Submit Configuration**

```javascript
async function initializeMarketplace(buyerData, sellersData, llmConfig) {
  const response = await fetch('/api/v1/simulation/initialize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      buyer: buyerData,
      sellers: sellersData,
      llm_config: llmConfig
    })
  });

  if (!response.ok) {
    throw new Error('Failed to initialize marketplace');
  }

  const result = await response.json();
  return {
    sessionId: result.session_id,
    negotiationRooms: result.negotiation_rooms
  };
}
```

**Step 1.3: Display Available Negotiations**

Show user which items have sellers available:
```javascript
function displayNegotiationRooms(rooms) {
  rooms.forEach(room => {
    if (room.status === 'pending') {
      // Show "Start Negotiation" button for this item
      createRoomCard(room);
    } else if (room.status === 'no_sellers_available') {
      // Show "No sellers" message
      showNoSellersMessage(room.item_name, room.reason);
    }
  });
}
```

---

#### **Phase 2: Run Negotiation**

**Step 2.1: Start Negotiation**

```javascript
async function startNegotiation(roomId) {
  const response = await fetch(`/api/v1/negotiation/${roomId}/start`, {
    method: 'POST'
  });

  const result = await response.json();
  
  // Open SSE stream
  const stream = new NegotiationStream(roomId);
  stream.connect();
  
  return result.stream_url;
}
```

**Step 2.2: Display Real-time Messages**

```javascript
class NegotiationUI {
  constructor(roomId) {
    this.roomId = roomId;
    this.chatContainer = document.getElementById('chat-container');
    this.offersContainer = document.getElementById('offers-container');
  }

  handleBuyerMessage(data) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message buyer-message';
    messageDiv.innerHTML = `
      <div class="sender">Buyer</div>
      <div class="content">${this.highlightMentions(data.message)}</div>
      <div class="timestamp">${new Date(data.timestamp).toLocaleTimeString()}</div>
    `;
    this.chatContainer.appendChild(messageDiv);
    this.scrollToBottom();
  }

  handleSellerResponse(data) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message seller-message seller-${data.sender_id}`;
    messageDiv.innerHTML = `
      <div class="sender">${data.seller_name}</div>
      <div class="content">${data.message}</div>
      <div class="timestamp">${new Date(data.timestamp).toLocaleTimeString()}</div>
    `;
    this.chatContainer.appendChild(messageDiv);

    // Update offers panel
    if (data.updated_offer) {
      this.updateOffer(data.sender_id, data.seller_name, data.updated_offer);
    }
    
    this.scrollToBottom();
  }

  updateOffer(sellerId, sellerName, offer) {
    const offerCard = document.getElementById(`offer-${sellerId}`) || 
                      this.createOfferCard(sellerId, sellerName);
    
    offerCard.querySelector('.price').textContent = `$${offer.price}`;
    offerCard.querySelector('.quantity').textContent = offer.quantity;
    offerCard.querySelector('.last-updated').textContent = 
      `Updated: ${new Date(offer.timestamp).toLocaleTimeString()}`;
  }

  highlightMentions(message) {
    return message.replace(/@(\w+)/g, '<span class="mention">@$1</span>');
  }

  handleComplete(data) {
    const decisionDiv = document.createElement('div');
    decisionDiv.className = 'negotiation-complete';
    decisionDiv.innerHTML = `
      <h3>🎉 Negotiation Complete!</h3>
      <p><strong>Selected Seller:</strong> ${data.selected_seller}</p>
      <p><strong>Final Price:</strong> $${data.final_price}</p>
      <p><strong>Reason:</strong> ${data.reason}</p>
      <button onclick="viewSummary('${this.roomId}')">View Details</button>
    `;
    this.chatContainer.appendChild(decisionDiv);
  }
}
```

---

#### **Phase 3: View Results**

**Step 3.1: Get Session Summary**

```javascript
async function getSessionSummary(sessionId) {
  const response = await fetch(`/api/v1/simulation/${sessionId}/summary`);
  const summary = await response.json();
  
  displaySummary(summary);
}

function displaySummary(summary) {
  const summaryDiv = document.getElementById('summary-container');
  summaryDiv.innerHTML = `
    <h2>Shopping Summary</h2>
    <div class="cost-info">
      <p>Total Spent: $${summary.total_cost_summary.total_spent}</p>
      <p>Items Purchased: ${summary.total_cost_summary.items_purchased}</p>
      <p>Average Savings Per Item: $${summary.total_cost_summary.average_savings_per_item}</p>
    </div>
    
    <h3>Purchases (${summary.completed_purchases})</h3>
    <ul>
      ${summary.purchases.map(p => `
        <li>
          <strong>${p.item_name}</strong>: ${p.quantity} units from ${p.selected_seller} 
          @ $${p.final_price_per_unit} each (Total: $${p.total_cost})
          <br><small>Negotiated in ${p.negotiation_rounds} rounds</small>
        </li>
      `).join('')}
    </ul>
    
    ${summary.failed_items.length > 0 ? `
      <h3>Failed Items</h3>
      <ul>
        ${summary.failed_items.map(f => `
          <li>${f.item_name}: ${f.reason}</li>
        `).join('')}
      </ul>
    ` : ''}
  `;
}
```

---

### 7.2 UI/UX Recommendations

#### **Configuration Screen**

**Buyer Form:**
```
┌─────────────────────────────────────┐
│ Buyer Configuration                 │
├─────────────────────────────────────┤
│ Name: [___________________]         │
│                                     │
│ Shopping List:                      │
│  Item 1: [________] Qty: [__]      │
│          Min Price: [$____]        │
│          Max Price: [$____]        │
│  Item 2: [________] Qty: [__]      │
│          Min Price: [$____]        │
│          Max Price: [$____]        │
│  [+ Add Item]                       │
└─────────────────────────────────────┘
```

**Seller Form (Repeatable):**
```
┌─────────────────────────────────────┐
│ Seller #1 Configuration             │
├─────────────────────────────────────┤
│ Name: [___________________]         │
│                                     │
│ Profile:                            │
│  Priority: (•) Customer Retention   │
│            ( ) Maximize Profit      │
│  Style:    (•) Very Sweet           │
│            ( ) Rude                 │
│                                     │
│ Inventory:                          │
│  ┌──────────────────────────────┐  │
│  │ Item: [________]             │  │
│  │ Cost: [$____]                │  │
│  │ Selling: [$____]             │  │
│  │ Least: [$____]               │  │
│  │ Stock: [__]                  │  │
│  └──────────────────────────────┘  │
│  [+ Add Inventory Item]             │
│                                     │
│ [Remove Seller]                     │
└─────────────────────────────────────┘
[+ Add Seller] (max 10)
```

**LLM Configuration:**
```
┌─────────────────────────────────────┐
│ LLM Settings                        │
├─────────────────────────────────────┤
│ Model: [llama-3-8b-instruct ▼]     │
│                                     │
│ Advanced:                           │
│  Temperature: [0.7____]             │
│  Max Tokens: [500___]               │
└─────────────────────────────────────┘
```

---

#### **Negotiation Screen**

```
┌────────────────────────────────────────────────────────────────┐
│ Negotiating: Laptop (Need: 2 units)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────┐   │
│  │ Current Offers   │  │      Chat                        │   │
│  ├──────────────────┤  ├──────────────────────────────────┤   │
│  │ TechStore        │  │ [Buyer]: Hello @TechStore and   │   │
│  │ $1150 / unit     │  │ @GadgetHub! Looking for 2       │   │
│  │ Updated: 10:30   │  │ laptops. What are your best...  │   │
│  │ [Best Price]     │  │                                  │   │
│  ├──────────────────┤  │ [TechStore]: Hi! I can offer... │   │
│  │ GadgetHub        │  │ Price: $1150                     │   │
│  │ $1100 / unit     │  │                                  │   │
│  │ Updated: 10:31   │  │ [GadgetHub]: Best I can do...   │   │
│  │                  │  │ Price: $1100                     │   │
│  ├──────────────────┤  │                                  │   │
│  │ CompuWorld       │  │ [Buyer]: Thanks @GadgetHub...   │   │
│  │ $1180 / unit     │  │                                  │   │
│  │ Updated: 10:29   │  │ [typing...] ⌛                  │   │
│  └──────────────────┘  └──────────────────────────────────┘   │
│                                                                 │
│  Round: 3/10                           [Force Decision] [Stop] │
└────────────────────────────────────────────────────────────────┘
```

---

#### **Summary Screen**

```
┌────────────────────────────────────────────────────────────────┐
│ Shopping Complete! 🎉                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Purchases (1)                                                  │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ✅ Laptop x2                                              │ │
│  │    From: GadgetHub @ $1080/unit = $2160                  │ │
│  │    Negotiated in 5 rounds (2m 25s)                       │ │
│  │    [View Conversation Log]                               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Failed Items (1)                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ❌ Mouse x5                                               │ │
│  │    Reason: No sellers have this item in inventory        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [Download Report] [Start New Session] [View All Logs]        │
└────────────────────────────────────────────────────────────────┘
```

---

### 7.3 State Management (Frontend)

**Recommended Frontend State Structure:**

```javascript
const appState = {
  session: {
    id: null,
    status: 'idle', // 'idle' | 'initializing' | 'active' | 'completed'
    buyer: {},
    sellers: [],
    llmConfig: {}
  },
  
  negotiations: {
    'room_laptop_001': {
      roomId: 'room_laptop_001',
      itemName: 'Laptop',
      status: 'active', // 'pending' | 'active' | 'completed'
      currentRound: 3,
      maxRounds: 10,
      messages: [],
      offers: {
        'seller_001': { price: 1150, quantity: 2, timestamp: '...' },
        'seller_002': { price: 1100, quantity: 2, timestamp: '...' }
      },
      stream: null, // EventSource instance
      decision: null
    }
  },
  
  ui: {
    activeNegotiation: 'room_laptop_001',
    showSummary: false,
    errors: []
  }
};
```

---

## 8. State Management Flow

### 8.1 Backend State Lifecycle

```
[User Submits Config]
         ↓
[Create Global Session State]
         ↓
    Store in memory:
    - session_id → SessionState
    - SessionState contains:
        - buyer config
        - sellers config
        - llm config
        - negotiation_rooms: {}
         ↓
[For each item in shopping list]
         ↓
[Run Seller Selection]
         ↓
[Create NegotiationRoom State]
         ↓
    Add to session:
    - room_id → NegotiationRoomState
    - NegotiationRoomState contains:
        - conversation_history: []
        - current_offers: {}
        - status: "pending"
         ↓
[Return session_id + room_ids to frontend]
```

### 8.2 Negotiation State Updates

```
[Frontend calls /start on room_id]
         ↓
[Backend updates room status → "active"]
         ↓
[LangGraph starts execution]
         ↓
    For each turn:
    - Generate buyer/seller message
    - Append to conversation_history
    - Update current_offers
    - Stream events via SSE
         ↓
[Buyer makes decision]
         ↓
[Update room status → "completed"]
         ↓
[Save to JSON file]
         ↓
[Keep in memory for 1 hour for queries]
         ↓
[Cleanup on session delete or timeout]
```

### 8.3 State Cleanup Strategy

**In-Memory Retention:**
- Active sessions: Indefinite (until completed or user deletes)
- Completed sessions: 1 hour
- Abandoned sessions: 2 hours timeout, auto-cleanup

**Persistence:**
- All completed negotiations saved to JSON immediately
- Session summary generated on completion
- Logs accessible via API for 24 hours
- Automatic cleanup of logs older than 7 days

---

## 9. Error Handling & Status Codes

### 9.1 HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful request |
| 201 | Created | New session/resource created |
| 400 | Bad Request | Invalid input (validation failed) |
| 404 | Not Found | Session/room ID doesn't exist |
| 409 | Conflict | Resource already exists or in invalid state |
| 422 | Unprocessable Entity | Valid JSON but business logic fails |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | LLM failure, unexpected error |
| 503 | Service Unavailable | LLM provider unreachable |

### 9.2 Error Response Format

**Standard Error Schema:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Seller pricing constraint violated",
    "details": [
      {
        "field": "sellers[0].inventory[0].least_price",
        "issue": "least_price (950) must be greater than cost_price (800) and less than selling_price (900)"
      }
    ],
    "timestamp": "2025-11-15T10:30:00Z"
  }
}
```

### 9.3 Error Codes Catalog

| Error Code | HTTP Status | Meaning | Frontend Action |
|------------|-------------|---------|-----------------|
| `VALIDATION_ERROR` | 400 | Input validation failed | Show field-specific errors |
| `SESSION_NOT_FOUND` | 404 | Session ID invalid | Redirect to home |
| `ROOM_NOT_FOUND` | 404 | Room ID invalid | Show error, refresh session |
| `NEGOTIATION_ALREADY_ACTIVE` | 409 | Attempted to start active negotiation | Show current state |
| `MAX_SELLERS_EXCEEDED` | 400 | >10 sellers submitted | Show limit message |
| `LLM_TIMEOUT` | 500 | LLM took too long | Retry or skip agent |
| `LLM_PROVIDER_UNAVAILABLE` | 503 | Can't reach LM Studio | Show connection error |
| `INSUFFICIENT_INVENTORY` | 422 | Seller out of stock | Show availability error |

### 9.4 Frontend Error Handling Strategy

```javascript
async function apiCall(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new APIError(errorData.error, response.status);
    }
    
    return await response.json();
    
  } catch (error) {
    if (error instanceof APIError) {
      handleAPIError(error);
    } else {
      handleNetworkError(error);
    }
  }
}

function handleAPIError(error) {
  switch (error.code) {
    case 'SESSION_NOT_FOUND':
      showErrorModal('Session expired. Redirecting to home...');
      setTimeout(() => window.location.href = '/', 2000);
      break;
      
    case 'LLM_PROVIDER_UNAVAILABLE':
      showErrorBanner('LLM service unavailable. Please check your LM Studio connection.');
      enableRetryButton();
      break;
      
    case 'VALIDATION_ERROR':
      error.details.forEach(detail => {
        highlightFieldError(detail.field, detail.issue);
      });
      break;
      
    default:
      showErrorModal(`Error: ${error.message}`);
  }
}
```

---

## 10. Environment Configuration

### 10.1 Environment Variables

**File: `.env`**

```bash
# Application
APP_NAME="Multi-Agent Marketplace"
APP_VERSION="1.0.0"
ENVIRONMENT="development"  # development | production
DEBUG=true

# Server
HOST="0.0.0.0"
PORT=8000
WORKERS=1  # For development, increase for production

# CORS
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"  # Frontend URLs
CORS_ALLOW_CREDENTIALS=true

# Database
DATABASE_URL="sqlite:///data/marketplace.db"
DATABASE_ECHO=false  # Set to true for SQL logging in development

# LM Studio
LM_STUDIO_BASE_URL="http://localhost:1234/v1"
LM_STUDIO_DEFAULT_MODEL="llama-3-8b-instruct"
LM_STUDIO_TIMEOUT=30  # seconds

# LLM Settings
LLM_DEFAULT_TEMPERATURE=0.7
LLM_DEFAULT_MAX_TOKENS=500
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2  # seconds

# Negotiation Settings
MAX_NEGOTIATION_ROUNDS=10
MAX_SELLERS_PER_SESSION=10
NEGOTIATION_TIMEOUT_MINUTES=30
SESSION_CLEANUP_HOURS=1

# Streaming
SSE_HEARTBEAT_INTERVAL=15  # seconds
SSE_RETRY_TIMEOUT=5  # seconds

# Logging
LOG_LEVEL="INFO"  # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT="json"  # json | text
LOG_FILE="logs/app.log"

# Persistence
LOGS_DIR="logs/sessions"
LOG_RETENTION_DAYS=7
AUTO_SAVE_NEGOTIATIONS=true

# Rate Limiting (optional)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=60
```

### 10.2 Configuration Loading

**File: `app/core/config.py`**

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str
    app_version: str
    environment: str
    debug: bool
    
    # Server
    host: str
    port: int
    workers: int
    
    # CORS
    cors_origins: List[str]
    cors_allow_credentials: bool
    
    # Database
    database_url: str
    database_echo: bool
    
    # LM Studio
    lm_studio_base_url: str
    lm_studio_default_model: str
    lm_studio_timeout: int
    
    # ... other settings
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
settings = Settings()
```

---

## 11. Implementation Checklist

### Phase 1: Foundation (Days 1-2)

**Backend Setup:**
- [ ] Initialize FastAPI project structure
- [ ] Setup Pydantic models for all schemas
- [ ] Create environment configuration
- [ ] Implement structured logging
- [ ] Setup CORS middleware
- [ ] Create health check endpoint

**Core Logic:**
- [ ] Implement Seller Selection Algorithm
- [ ] Create StateManager for in-memory storage
- [ ] Build validation utilities
- [ ] Setup error handling middleware

---

### Phase 2: LLM Integration (Days 3-4)

**LLM Integration:**
- [ ] Implement LMStudioAdapter
  - [ ] Connection testing
  - [ ] Streaming support
  - [ ] Error handling

**Agent Prompts:**
- [ ] Design buyer prompt template
- [ ] Design seller prompt templates (rude/sweet variants)
- [ ] Create dynamic context injection
- [ ] Test prompt effectiveness with sample LLMs

---

### Phase 3: LangGraph Workflow (Days 5-6)

**Graph Construction:**
- [ ] Design negotiation subgraph structure
- [ ] Implement BuyerTurnNode
- [ ] Implement MessageRoutingNode
- [ ] Implement SellerResponseNode (parallel execution)
- [ ] Implement DecisionCheckNode
- [ ] Implement BuyerDecisionNode
- [ ] Connect nodes in LangGraph

**Message Routing:**
- [ ] Build @mention parser
- [ ] Implement visibility filter
- [ ] Create conversation history manager
- [ ] Test routing logic with mock data

---

### Phase 4: FastAPI Endpoints (Day 7)

**API Implementation:**
- [ ] POST `/simulation/initialize` - Create session
- [ ] GET `/simulation/{session_id}` - Get session details
- [ ] DELETE `/simulation/{session_id}` - Cleanup session
- [ ] POST `/negotiation/{room_id}/start` - Start negotiation
- [ ] GET `/negotiation/{room_id}/stream` - SSE streaming
- [ ] POST `/negotiation/{room_id}/message` - Send message
- [ ] POST `/negotiation/{room_id}/decide` - Force decision
- [ ] GET `/negotiation/{room_id}/state` - Get state
- [ ] GET `/simulation/{session_id}/summary` - Get summary
- [ ] GET `/llm/status` - Check LLM providers

**SSE Implementation:**
- [ ] Setup sse-starlette
- [ ] Create async event generator
- [ ] Implement heartbeat mechanism
- [ ] Handle client disconnections
- [ ] Test streaming with multiple clients

---

### Phase 5: Persistence & Testing (Day 8)

**Persistence:**
- [ ] Implement JSON log saving
- [ ] Create negotiation summary generator
- [ ] Build session cleanup scheduler
- [ ] Test log retrieval endpoints

**Testing:**
- [ ] Unit tests for seller selection
- [ ] Unit tests for message routing
- [ ] Unit tests for visibility filtering
- [ ] Integration test: Full negotiation flow
- [ ] Integration test: SSE streaming
- [ ] Load test with multiple sessions

**Documentation:**
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Setup instructions (README)
- [ ] Frontend integration examples
- [ ] Deployment guide

---

### Phase 6: Frontend Integration Support

**For Frontend Team:**
- [ ] Provide OpenAPI spec export
- [ ] Create Postman collection
- [ ] Write frontend integration guide
- [ ] Setup demo data fixtures
- [ ] Create example frontend code snippets
- [ ] Host test backend instance
- [ ] Schedule integration testing session

---

## 12. FastAPI Application Structure

### 12.1 Main Application File

**File: `app/main.py`**

**Responsibilities:**
- FastAPI app initialization
- Middleware registration
- Router inclusion
- Startup/shutdown events
- Global exception handlers

**Key Components:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.middleware.error_handler import add_exception_handlers
from app.utils.logger import setup_logging

# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

# Setup logging
setup_logging()

# Add exception handlers
add_exception_handlers(app)

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize LLM providers
    # Setup state manager
    # Check LLM connectivity
    pass

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup sessions
    # Save pending logs
    # Close LLM connections
    pass
```

### 12.2 Router Aggregation

**File: `app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1.endpoints import simulation, negotiation, streaming, status

api_router = APIRouter()

api_router.include_router(
    simulation.router, 
    prefix="/simulation", 
    tags=["simulation"]
)

api_router.include_router(
    negotiation.router, 
    prefix="/negotiation", 
    tags=["negotiation"]
)

api_router.include_router(
    streaming.router, 
    tags=["streaming"]
)

api_router.include_router(
    status.router, 
    tags=["status"]
)
```

### 12.3 Endpoint File Structure

**Each endpoint file (e.g., `simulation.py`) contains:**
- Router definition
- Request/response models import
- Business logic service calls
- Error handling
- Documentation strings

**Example Pattern:**
```python
from fastapi import APIRouter, HTTPException, status
from app.models.api_schemas import InitializeSessionRequest, InitializeSessionResponse
from app.services.session_manager import SessionManager
from app.utils.exceptions import ValidationError

router = APIRouter()

@router.post(
    "/initialize",
    response_model=InitializeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize new marketplace session",
    description="Creates a new session with buyer, sellers, and LLM configuration"
)
async def initialize_session(request: InitializeSessionRequest):
    """
    Initialize a new marketplace simulation session.
    
    - Validates buyer and seller configurations
    - Runs seller selection algorithm for each item
    - Creates negotiation rooms
    - Returns session ID and room details
    """
    try:
        session_manager = SessionManager()
        result = await session_manager.create_session(request)
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        )
```

---

## 13. Deployment Considerations

### 13.1 Development Deployment

**Run FastAPI:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Run LM Studio:**
- Start LM Studio application
- Load model (e.g., llama-3-8b-instruct)
- Enable local server on port 1234

### 13.2 Production Deployment (Optional)

**Using Docker Compose:**

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped
```

**Using Gunicorn (Production ASGI Server):**
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

---

## 14. Testing Strategy for Frontend Developers

### 14.1 API Testing Tools

**Postman Collection:**
- Pre-built requests for all endpoints
- Environment variables for session/room IDs
- Example request bodies
- Automated tests for status codes

**Swagger UI:**
- Available at `/api/docs`
- Interactive API testing
- Schema validation
- Try-it-out functionality

### 14.2 Mock Data Fixtures

**Provide pre-configured test data:**

```javascript
// Example buyer configuration
const mockBuyer = {
  name: "Test Buyer",
  shopping_list: [
    { 
      item_id: "laptop_001", 
      item_name: "Laptop", 
      quantity_needed: 2,
      min_price_per_unit: 900,
      max_price_per_unit: 1500
    },
    { 
      item_id: "mouse_001", 
      item_name: "Mouse", 
      quantity_needed: 5,
      min_price_per_unit: 10,
      max_price_per_unit: 25
    }
  ]
};

// Example sellers
const mockSellers = [
  {
    name: "TechStore",
    inventory: [
      {
        item_id: "laptop_001",
        item_name: "Laptop",
        cost_price: 800,
        selling_price: 1200,
        least_price: 1000,
        quantity_available: 10
      }
    ],
    profile: {
      priority: "customer_retention",
      speaking_style: "very_sweet"
    }
  },
  // ... more sellers
];

// Example LLM config
const mockLLMConfig = {
  model: "llama-3-8b-instruct",
  temperature: 0.7,
  max_tokens: 500
};
```

### 14.3 End-to-End Test Scenario

**Test Script for Frontend Developers:**

```javascript
// 1. Initialize session
const initResponse = await fetch('/api/v1/simulation/initialize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    buyer: mockBuyer,
    sellers: mockSellers,
    llm_config: mockLLMConfig
  })
});

const { session_id, negotiation_rooms } = await initResponse.json();
console.log('Session created:', session_id);

// 2. Start negotiation for first room
const room = negotiation_rooms[0];
const startResponse = await fetch(`/api/v1/negotiation/${room.room_id}/start`, {
  method: 'POST'
});

console.log('Negotiation started for', room.item_name);

// 3. Open SSE stream
const eventSource = new EventSource(`/api/v1/negotiation/${room.room_id}/stream`);

eventSource.onmessage = (event) => {
  console.log('Event:', JSON.parse(event.data));
};

// 4. After negotiation completes, get summary
setTimeout(async () => {
  const summaryResponse = await fetch(`/api/v1/simulation/${session_id}/summary`);
  const summary = await summaryResponse.json();
  console.log('Summary:', summary);
}, 60000); // Wait 1 minute
```

---

## 15. Security & Best Practices

### 15.1 Input Sanitization

**Enforce at multiple levels:**
1. Pydantic model validation (types, ranges)
2. Custom validators for business logic
3. SQL injection prevention (if database added)
4. XSS prevention in message content

### 15.2 Rate Limiting (Optional)

**Protect against abuse:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/simulation/initialize")
@limiter.limit("10/minute")
async def initialize_session(...):
    ...
```

### 15.3 Database Security

**For SQLite Database:**
- Restrict file system permissions on database file
- Use database-level constraints to enforce data integrity
- Regularly backup database file
- Consider write-ahead logging (WAL) mode for better concurrency

### 15.4 CORS Configuration

**Production settings:**
```python
CORS_ORIGINS = [
    "https://your-frontend-domain.com",
    "https://www.your-frontend-domain.com"
]
```

---

## 16. Troubleshooting Guide

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| LM Studio not connecting | 503 error on initialize | Check LM Studio is running on port 1234 |
| SSE not streaming | No events received | Check browser EventSource support, CORS headers |
| Validation errors | 400 on initialize | Check price constraints (cost < least < selling) |
| Session not found | 404 on queries | Session may have expired (1hr timeout) |
| Slow responses | Long wait times | Check LLM model size, consider smaller model |

---

## 17. Future Enhancements (Post-Hackathon)

**Potential additions:**
- [ ] Multi-buyer support (competitive bidding)
- [ ] WebSocket bidirectional communication
- [ ] PostgreSQL for persistent storage
- [ ] Redis for distributed state management
- [ ] Real-time analytics dashboard
- [ ] Agent learning/memory across sessions
- [ ] Complex negotiation tactics (bundles, bulk discounts)
- [ ] Seller reputation system
- [ ] GraphQL API
- [ ] Mobile app support

---

## 18. Conclusion

This backend architecture provides a complete, production-ready foundation for the multi-agent ecommerce marketplace with **opaque negotiations**. The FastAPI endpoints are designed with frontend integration as a priority, offering:

✅ **Opaque Agent Model:** Buyers cannot see seller costs, strategies, or internal profiles  
✅ **SQLite Persistence:** All configurations and negotiations stored in database  
✅ **Per-Item Pricing:** No global budget - only min/max constraints per item  
✅ **Real-time updates:** SSE streaming for live negotiations  
✅ **LM Studio Integration:** Focus on local inference for on-device simulation  
✅ **Session-based Workflow:** Support multiple negotiation runs per configuration  
✅ **Comprehensive error handling:** Actionable error messages  
✅ **Scalable structure:** Modular design for easy extension  

**Next Steps:**
1. Review this document with frontend team
2. Setup shared API testing environment
3. Begin Phase 1 implementation
4. Establish communication protocol for blockers

---

**Document Status:** ✅ Final & Ready for Implementation  
**Last Updated:** November 15, 2025  
**Prepared For:** Frontend Integration Team  
**Backend Lead:** [Your Name]  

---

**Contact for Questions:**
- Architecture: [Contact details]
- API Issues: [Contact details]
- LLM Integration: [Contact details]