## 1. Product Overview (Updated)

**Name:** Multi-Agent Marketplace Simulator (MAMS)

**Core Idea (Revised):**
Simulate **realistic, opaque negotiations** between:

* One **Buyer agent**, and
* Up to **N Seller agents** (max ~10 per session),

for multiple items, where:

* Buyer **does not know**:

  * Seller cost price
  * Seller least acceptable price
  * Seller strategy/profile or priorities
* Buyer only sees what sellers choose to reveal in chat.
* Sellers negotiate using their own internal constraints and style, but those are **never exposed** to the buyer unless disclosed.
* **No explicit scoring functions or numeric decision heuristics** in the product design — decisions are left to the LLM’s reasoning within prompts.
* All state (config, negotiations, messages, outcomes) is persisted in a **database**, so:

  * You can configure once per session,
  * Then run **multiple negotiations** on top of that configuration.

---

## 2. Updated Design Principles

1. **Opaque Opponent Models**

   * Buyer treats sellers as black boxes with only conversational evidence.
   * Seller’s intrinsic attributes (costs, least_price, style, priorities) are internal.
2. **Per-Item View for Buyer**

   * Buyer only has **per-item constraints**:

     * Min acceptable price for that item
     * Max acceptable price for that item
     * Required quantity
   * There is **no global cross-item budget optimization**.
3. **LLM-Driven Reasoning (No Handcrafted Scoring)**

   * No designed numerical scoring like “price_score + behavior_score”.
   * Buyer’s decision is purely described as “Let LLM think and justify” using instructions in prompts.
4. **DB-Backed State**

   * All configuration and negotiation logs stored in a DB.
   * One configuration session can spawn multiple negotiations over time without re-entering configs.
5. **Single Backend: LM Studio**

   * All agents (Buyer and Sellers) use LM Studio–hosted models.
   * Focus is on **on-device**, single-machine simulation.

---

## 3. Core Entities (Revised)

### 3.1 Buyer Agent

**Configuration Inputs (per session):**

* **Item demand list** (same as before):
  `[(item_name, quantity, min_price, max_price)]`
  e.g.

  * `"iPhone Case", qty=2, min_price=10, max_price=18`
  * `"USB-C Cable", qty=3, min_price=5, max_price=9`

> These min/max prices are the **only numeric constraints** the buyer has regarding money.

**Buyer knowledge:**

* Knows:

  * Item name and quantity.
  * Per-item min and max price constraints.
  * Which sellers are *available* for that item (as identities/handles only, e.g. `@seller_A`, `@seller_B`).
* Does **not** know:

  * Seller cost price.
  * Seller least_price (bottom line).
  * Seller internal strategies, priorities, or speaking style configuration.
  * Seller’s negotiation history across past runs.

**Buyer behavior (conceptual):**

* For each item negotiation:

  * Opens a “room” with all sellers who can supply that item.
  * Asks initial questions (price, terms, quality, etc.).
  * Uses **LLM reasoning** to:

    * Interpret seller responses.
    * Decide who seems better.
    * Decide if an offer is acceptable within `[min_price, max_price]`.
    * Decide when to keep pushing vs settle vs walk away.
* No explicit scoring, just instructions like:

  * “Think about the offers and pick the seller whose offer and behavior most align with your constraints and preferences on this item.”

---

### 3.2 Seller Agents

**Configuration (per session, stored in DB):**

Each seller has:

* **Seller identity:**

  * `seller_id`, `name/handle` (e.g. `"seller_1"`, `"@AlphaStore"`)
* **Inventory entries** (per item):

  * `item_name`
  * `cost_price`
  * `selling_price` (initial ask)
  * `least_price` (price floor, strictly > cost_price)
* **Soft internal profile (not exposed to buyer):**

  * Priority balance:

    * `customer_retention_weight`
    * `profit_maximization_weight`
  * Speaking style preference:

    * Rude ↔ Neutral ↔ Very Sweet

**Seller knowledge:**

* Knows (for each item negotiation run):

  * Buyer’s stated demand for that item (item name and quantity).
  * Whatever the buyer messages during **this** negotiation.
  * Their own cost, selling_price, least_price, and stylistic profile.
* Does **not**:

  * Persist negotiation history beyond the current negotiation session.
  * Remember past runs with the same buyer — every negotiation is fresh from seller’s perspective.
  * See other sellers’ conversations or offers.

**Key change:**

> Sellers **do not carry persistent “negotiation history”** across runs — they are stateless between negotiations except for their inventory and intrinsic parameters stored in DB.

---

## 4. Knowledge & Visibility Model (Updated)

### 4.1 Buyer View

Per item negotiation, buyer sees:

* Their own constraints:

  * Item name
  * Quantity
  * Min and max acceptable price
* Sellers participating (by name/handle).
* Messages received from each seller.
* Only the information **sellers explicitly mention**:

  * If seller chooses to say “my cost is 30, I can’t go below 35”, buyer sees that.
  * Otherwise, buyer never sees those numbers.

### 4.2 Seller View

Per item negotiation, each seller sees:

* Request context:

  * Item name
  * Quantity buyer wants
  * Any item-related details buyer shares (e.g., use-case preferences).
* Messages **from the buyer** that are either:

  * Directed to them using `@seller_name`, or
  * General “broadcast” messages if you choose to support that.
* Their own internal config:

  * cost_price, selling_price, least_price
  * style, priorities

They **never see**:

* Other sellers’ prices/offers/messages.
* Buyer’s interactions with other sellers.

### 4.3 Orchestration Logic (Conceptual)

* Internally, there is an orchestrator that:

  * Receives buyer messages.
  * Routes them to appropriate sellers based on `@handles`.
  * Collects seller messages and presents them to the buyer.
* But logically, it behaves like:

  * Decentralized agents chatting in a group, with **visibility filtering** implemented at routing layer.

---

## 5. Negotiation Episode Structure (Adjusted)

Each **negotiation episode** is:

1. **Initialization:**

   * Item `I` selected.
   * Relevant sellers for `I` fetched from DB (where inventory includes `I`).
   * Buyer’s per-item constraints loaded from DB:

     * quantity, min_price, max_price.
2. **Conversation Loop (LLM-driven):**

   * Buyer sends initial message (e.g., “Hi, I need 3 units of X. What can you offer?”).
   * Orchestrator:

     * Routes buyer message to all sellers (or only those mentioned).
   * Each seller agent:

     * Generates response using LM Studio model based on:

       * Their pricing structure.
       * Their style and internal priorities.
       * The buyer’s latest message.
     * Response is recorded in DB and returned to buyer.
   * Buyer:

     * Sees all seller responses.
     * Uses LM Studio model to:

       * Think about trade-offs qualitatively.
       * Check if any offer fits within `[min_price, max_price]`.
       * Decide:

         * Ask follow-ups (possibly @mentioning specific sellers).
         * Push for better deal.
         * Accept an offer.
         * Reject all and walk away.
3. **Termination:**

   * Episode ends when:

     * Buyer explicitly selects a seller for this item and price (within their constraints), or
     * Buyer explicitly decides not to purchase this item.
   * Final decision (seller, price, quantity, or “no deal”) is stored in DB.

> No numeric scoring or formula is explicitly defined – the system just tells the LLM: “Reason about which offer is best based on your constraints and the conversation so far.”

---

## 6. Session & Multi-Negotiation Model

### 6.1 Session Concept

A **Session** = a configured environment with:

* A single Buyer configuration:

  * List of (item_name, quantity, min_price, max_price)
* A set of Seller configurations:

  * Inventory & internal parameters.

This configuration is stored in the DB and can be reused.

### 6.2 Multiple Negotiations per Session

Once a session is configured:

* You can start **multiple negotiation runs** without re-entering configs:

  * For different subsets of items.
  * For the same items again (e.g., repeated experiments).
  * With variation in prompts (e.g., different buyer behavior instructions).

Each **NegotiationRun** references:

* `session_id`
* `item_name`
* A sequence of messages and a final outcome.

The DB acts as the backbone tying:

* Session → NegotiationRuns → Messages → Outcomes.

---

## 7. State & Database Model (Conceptual)

At a high level, you’ll likely need the following logical entities in your DB (no implementation details, just structure):

1. **Sessions**

   * `session_id`
   * `created_at`
   * `description` (optional)
2. **BuyerConfig**

   * `session_id` (FK)
   * Per-item rows:

     * `item_name`
     * `quantity`
     * `min_price`
     * `max_price`
3. **SellerConfig**

   * `seller_id`
   * `session_id` (FK)
   * `name/handle`
   * `customer_retention_weight`
   * `profit_maximization_weight`
   * `style_profile` (rude/neutral/sweet label or similar)
4. **SellerInventory**

   * `seller_id` (FK)
   * `item_name`
   * `cost_price`
   * `selling_price`
   * `least_price`
5. **NegotiationRuns**

   * `negotiation_id`
   * `session_id` (FK)
   * `item_name`
   * `status` (in_progress / completed / aborted)
   * `started_at`, `ended_at`
6. **Messages**

   * `message_id`
   * `negotiation_id` (FK)
   * `sender_type` (buyer / seller)
   * `sender_id` (seller_id or “buyer”)
   * `text`
   * `timestamp`
   * Metadata: who it was routed to (for sellers), internal logs, etc.
7. **Outcomes**

   * `negotiation_id` (FK)
   * `decision_type` (deal / no_deal)
   * If `deal`:

     * `seller_id`
     * `final_price`
     * `quantity`
   * Optional: `llm_reasoning_summary` (a short explanation generated at the end).

---

## 8. Inference & Runtime (Finalized)

### 8.1 Model Backend

* Only **LM Studio** is used.
* All agents (Buyer and Sellers) call into LM Studio with:

  * Different system prompts and instructions.
  * Same or different local models, depending on your LM Studio setup.

### 8.2 Execution Pattern

* For simplicity:

  * Negotiations are run **sequentially**:

    * Message → seller responses → buyer response → repeat.
* You can still simulate “parallel” sellers by:

  * Requesting all seller responses for a given buyer message in a single “step”.
* Responses are **streamed** back to UI for chat-like experience.
