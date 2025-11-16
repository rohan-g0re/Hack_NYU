

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

---

## 9. What We Explicitly Removed / Changed

* ❌ **Buyer internal knowledge of seller costs, least prices, or strategy knobs**

  * Buyer only learns what sellers reveal in conversation.

* ❌ **Seller long-term negotiation history as private knowledge**

  * Sellers are stateless across runs (beyond static config in DB).

* ❌ **Global budget optimization across items**

  * Buyer only uses per-item `min_price` and `max_price` and quantity.

* ❌ **Hand-engineered scoring & numeric decision rules (6.2)**

  * No structured “score = a*price + b*behavior”.
  * Decisions are left to LLM’s qualitative reasoning.

* ❌ **OpenRouter / remote models (7.1 old)**

  * Only LM Studio / local inference now.

* ✅ **DB for all state (instead of pure in-memory)**

  * Sessions, configs, negotiation logs, outcomes all persisted.
  * Enables multiple negotiations on top of a single configuration.



I’ll treat this as **“User Flow + Episode Lifecycle”** layered on top of the architecture we already defined.

---

## 1. Top-Level Concept: Negotiation Episode

A **Negotiation Episode** is one complete run where:

* You configure **seller agents** and their inventories,
* Configure the **buyer’s purchase plan**,
* The system computes which sellers can serve which items,
* Then runs **per-item negotiation chats**, and
* Ends with a **final receipt** summarizing all purchased items.

Everything (config, chats, outcome) is tied to that episode.

---

## 2. Screen-by-Screen User Flow

### 2.1 Start New Negotiation Episode

**Entry point UI:**

* Button: **“Start New Negotiation”**
* System creates a new `episode_id` in the DB with status `draft`.

Data created:

* `Episode`:

  * `episode_id`
  * `created_at`
  * `status = "draft"`

The user now moves into a multi-step wizard:

1. Add Sellers
2. Configure Items & Catalog (if needed)
3. Configure Buyer Purchase Plan
4. Run Negotiations
5. View Final Receipt

---

### 2.2 Step 1 – Add Seller Agents (One by One)

UI: **“Add Seller”** form, repeated.

For each seller, user fills:

* **Seller identity**

  * Seller name / handle (used for `@mentions` in chat)
* **Item list (inventory)**

  * Item (chosen from allowed items list)
  * Available quantity
  * Cost price
  * Selling (listed) price
  * Least acceptable price (floor)
* **Internal profile (hidden from buyer, used for prompting)**

  * Importance of customer retention vs profit
  * Speaking style: rude / neutral / very sweet

User can:

* Save seller
* Add another seller
* Edit/remove sellers before finalizing episode config

Data written per seller:

* `SellerConfig` linked to `episode_id`
* `SellerInventory` rows for each item

> At this point, the **universe of sellers** for the episode is fixed.

---

### 2.3 Step 2 – Available Items (Global Catalog)

Two options (conceptually):

* **Hardcoded catalog** in backend (e.g., `["Laptop", "Phone Case", "Cable", ...]`)
* Or a **Settings** page where admin/user defines the total list of available items.

In the episode flow, we just **use** this list:

* The “Add Seller” and “Buyer Purchase Plan” forms both **pick from the same catalog**.
* This guarantees matching between seller inventory and buyer demand.

Data:

* Not episode-specific; this is global “catalog” configuration.

---

### 2.4 Step 3 – Configure Buyer Purchase Plan

UI: **“Buyer Purchase Plan”** form.

For the current `episode_id`, user defines:

For each planned item:

* Choose **Item** (from catalog)
* Enter **Quantity to purchase**
* Set **Minimum acceptable price** per unit (buyer’s lower bound)
* Set **Maximum acceptable price** per unit (buyer’s upper bound)

Example row:

* Item: `Phone Case`
* Quantity: `2`
* Min price: `8`
* Max price: `15`

User can add multiple rows:

* `[(item_1, qty_1, min_1, max_1), (item_2, qty_2, min_2, max_2), ...]`

Data written:

* `BuyerConfig` rows linked to `episode_id`
  (one row per item the buyer wants)

> Key constraint:
> Buyer has **no global budget**, only *per-item* min/max price and quantity.

---

### 2.5 Step 4 – Match Sellers to Items (Algorithmic Seller Discovery)

Once sellers and buyer plan are defined, user clicks something like **“Generate Negotiations”**.

System does:

1. For each item in the **Buyer Purchase Plan**:

   * Look up all `SellerInventory` rows in this episode where:

     * `item_name` matches
     * `available_quantity > 0` (or at least enough for requested qty if you want that check)

2. Build a mapping:

   ```text
   item_name → [seller_1, seller_2, ..., seller_k]
   ```

3. For each (episode, item) pair with at least one seller:

   * Create a **Negotiation Record**:

     * `negotiation_id`
     * `episode_id`
     * `item_name`
     * Linked sellers
     * Status = `pending`

If no seller is available for an item:

* The system can immediately mark that item as `unfulfillable` and show this in the UI before negotiations even start.

At the end of this step, the episode has:

* A defined **set of negotiation rooms**, one per buyer-item, each with:

  * Buyer
  * Set of candidate sellers.

---

### 2.6 Step 5 – Per-Item Negotiation Chats

For each item in the Buyer Purchase Plan that has at least one seller:

#### 2.6.1 Start Chat for Item X

UI:

* You click on an item row (e.g., `Phone Case`) and enter its **Negotiation Chat View**:

  * Shows:

    * Item name & requested quantity
    * Buyer’s min/max price constraints
    * Participating sellers (handles only)
    * Conversation window

Backend:

* Instantiate a **Buyer Agent instance** keyed by `(episode_id, negotiation_id, item_name)`.
* For each participating seller, instantiate a **Seller Agent instance** logged against that `negotiation_id`.

> Note: This is conceptual “instance”; in practice it’s just state + prompt context per agent within the negotiation.

#### 2.6.2 Chat Mechanics

* **Buyer sends first message** (generated by LLM or user-triggered via “Start Negotiation” button).

* System:

  * Records the message in `Messages` table.
  * Routes the content to all relevant **Seller Agents** for this item.

* Each **Seller Agent**:

  * Calls LM Studio with:

    * Their internal inventory/pricing for this item.
    * Their style/priorities.
    * The buyer’s latest message.
  * Generates their reply.
  * Reply is recorded in `Messages`, then displayed in the UI under their handle.

* Buyer Agent:

  * Sees all seller replies for that item.
  * Uses LM Studio reasoning to:

    * Ask follow-ups
    * Focus on specific sellers using `@seller_name`
    * Decide whether any offer is acceptable within `[min_price, max_price]`
    * Decide when to stop.

> There is **no explicit scoring algorithm** here – decisions are all in “prompted reasoning” space.

#### 2.6.3 Ending the Negotiation for Item X

The item’s negotiation ends when the Buyer Agent:

* Accepts an offer:

  * Pick `seller_id`
  * Agree on `final_price`
  * Confirm `quantity` (or adjust if needed)
* Or declares **“no deal”**.

System then:

* Marks the `NegotiationRun` as `completed`.
* Writes an `Outcome` row for this `negotiation_id`:

  * If deal:

    * `decision_type = "deal"`
    * `seller_id`
    * `final_price`
    * `quantity`
  * If no deal:

    * `decision_type = "no_deal"`

Optionally decrements seller’s available quantity in `SellerInventory` for that item (if we want stock depletion to matter across negotiations in the same episode).

Repeat for each item.

Negotiations for multiple items can be run:

* Sequentially (simple for hackathon + LM Studio), or
* Conceptually “independently” from a user perspective (one chat per item).

---

### 2.7 Step 6 – Final Receipt

After all item negotiations are done (or the user chooses to stop):

UI: **“View Final Receipt”** for the episode.

System aggregates from `Outcomes`:

* For each item in Buyer Purchase Plan:

  * Was a deal made?
  * If yes:

    * Seller chosen
    * Final unit price
    * Quantity purchased
    * Total price
* Items with no deal are displayed as **“Not Purchased”** with a reason (e.g., “No acceptable offer within min–max range”).

The **Final Receipt** view shows:

* **Episode summary:**

  * `episode_id`, timestamp
* **Itemized table:**

  * Item
  * Quantity requested
  * Quantity purchased
  * Seller
  * Final price
  * Total cost (per item)
  * Deal / No deal status
* **Totals:**

  * Total number of items successfully purchased
  * Total spend (sum of item totals)

All of this is persisted in the DB, so you can later:

* Re-open an episode
* Inspect per-item negotiation logs
* Compare behavior across episodes.

---

## 3. How This Fits the Overall Idea

Putting it all together:

* **Episode = One full configured world**:

  * Sellers + Inventory
  * Buyer purchase plan (per-item constraints)
  * Negotiations per item
  * Final receipt

* **Flow** is:

  1. Start new episode
  2. Add sellers one by one via UI form
  3. Define buyer’s items, quantities, and per-item min/max prices
  4. System computes which sellers are viable for each item
  5. For each item, run a **Buyer ↔ Multiple Sellers** chat in isolation
  6. Once all are done, compile a **final receipt** from outcomes

* **LLM (LM Studio)** drives:

  * All agent decisions
  * All negotiation behavior
  * All qualitative reasoning (no hand-coded scores).



