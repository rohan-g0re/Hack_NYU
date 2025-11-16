## 1. Product Overview

**Working name:** Multi-Agent Marketplace Simulator (MAMS)
**Core idea:**
Simulate a 1-Buyer vs N-Sellers ecommerce marketplace where:

* A **single buyer agent** negotiates for each item in their cart
* With up to **10 seller agents** who each have their own inventory, pricing constraints, and “personality”
* Negotiations happen in a **WhatsApp-style multi-agent chat** per item
* Sellers **only see buyer messages explicitly directed to them** (via `@seller_name`) and never see other sellers’ private conversations
* The **buyer sees everything** and makes the final purchase decision per item.

The system is built for a **hackathon setting**:

* Single device, no distributed infra
* In-memory state
* Two model backends: **local (LM Studio/Ollama)** and **remote (OpenRouter)**
* Streaming LLM responses for “live chat” feel.

No code or backend details here – this is purely the **product / architecture concept**.

---

## 2. Goals & Non-Goals

### 2.1 Goals

* Simulate **realistic marketplace dynamics** between one buyer and multiple independent sellers.
* Allow **multi-agent negotiation** for each item in the buyer’s cart.
* Reflect **asymmetric information**:

  * Buyer knows each seller’s constraints and profile.
  * Sellers only know the buyer’s profile and their own situation, not competitors’.
* Support **dynamic negotiation strategies** inferred by LLMs, not hardcoded rules.
* Make it trivial to:

  * Configure sellers & buyer via a form
  * Run one or multiple simulation runs
  * Inspect **conversation logs + final purchase decisions**.

### 2.2 Non-Goals

* No real payments, logistics, or actual ecommerce integration.
* No large-scale distributed system; only **single-machine** simulation.
* No complex persistent analytics warehouse; just **basic logging** for now.
* No hardcoded “game theory optimal” strategies; LLMs are allowed to improvise inside soft constraints.

---

## 3. Core Entities & Concepts

### 3.1 Buyer Agent

**Buyer profile (inputs from user):**

* **Item demand map:**
  `item_name → quantity`
  Example: `{ "iPhone Case": 2, "USB-C Cable": 3 }`
* **Budget range:**

  * `min_budget`
  * `max_budget`
* **Preference knobs (conceptual):**

  * Price sensitivity vs quality sensitivity
  * Tolerance for rude vs sweet tone (could influence seller preference)
  * Appetite for negotiation length (short vs detailed bargaining)

**Buyer capabilities:**

* For each item:

  * Initiate a **multi-seller chat** for that item.
  * Address sellers individually with `@seller_name` mentions.
  * Ask for offers, discounts, bundles, guarantees, etc.
* Compare seller responses using:

  * Offered price vs budget
  * Seller’s tone/behavior
  * Past history (if we simulate multiple runs)
* Decide:

  * Which seller (if any) to buy from for that item
  * At what price
  * Or to **drop** the item if budget is too tight / offers are bad.

Buyer agent has **global knowledge**:

* Knows each seller’s:

  * Cost price
  * Current selling price
  * Least acceptable price
  * Stated priorities (customer retention vs profit)
  * Speaking style configuration

But **does not reveal this directly** unless we want to test certain scenarios. This becomes its internal reasoning context.

### 3.2 Seller Agents

Each seller is configured via a form and has:

**Inventory:**

* `items = [item1, item2, ..., itemX]`
* For each item:

  * `cost_price`
  * `selling_price` (initial listed price)
  * `least_price` (price floor)

    * Always strictly greater than `cost_price`
    * Seller must **not go below** this during negotiation

**Profile:**

* **Priority trade-off:**

  * `customer_retention_weight`
  * `profit_maximization_weight`
    Conceptually: a soft preference that guides how much they are willing to sacrifice margin to retain the buyer.
* **Speaking style range:**

  * Can be configured between **“rude” ↔ “very sweet”**
  * This is not fixed; the agent can modulate tone dynamically based on the conversation but biased by configuration.

**Seller knowledge:**

* Knows:

  * Their own costs, floor price, and inventory
  * Buyer’s declared needs and budget range for the overall cart / that item
* Does **not** know:

  * Other sellers’ prices, costs, or existence (beyond “you might have competitors” as a generic fact)
  * Messages that buyer sends to other sellers.

**Seller behavior (conceptual):**

* When `@mentioned` by the buyer:

  * Looks at current item, buyer’s requests, and their own constraints.
  * Proposes or updates:

    * A price offer (maybe with discount steps but never below `least_price`)
    * Non-price terms (delivery claims, support claims, “loyalty” offers)
  * May adjust tone (sweet/rude) and concessions based on:

    * How close buyer’s ask is to `least_price`
    * How many times buyer pushed
    * Priority: retention vs profit.

---

## 4. Simulation Structure

### 4.1 Overall Simulation Session

A **simulation run** is:

1. User fills a configuration form:

   * Buyer demand & budget
   * Seller list (up to 10), inventory & pricing data, style, and priorities
   * Choice of **LLM backend** preferences:

     * Local (LM Studio / Ollama)
     * Remote (OpenRouter)
     * Possibly: which agents use which backend

2. System prepares:

   * In-memory **marketplace state**
   * Buyer and seller **agent contexts** (prompts + parameters)
   * A list of items to process from buyer’s cart.

3. For each item:

   * Create an **item-specific multi-agent chat room**:

     * Participants: Buyer + all sellers who stock that item.
   * Run a negotiation episode (multi-turn chat) until:

     * Buyer decides on a seller or
     * Buyer abandons the item / hits a stopping condition.

4. After all items:

   * Produce a **simulation report**:

     * Which seller won which item at what price
     * Items not purchased and why (budget exceeded, no acceptable offers, etc.)
     * Conversation logs per item.

### 4.2 Episodic vs Continuous

* **Chosen model:** **Episodic per item**
  Each item’s negotiation is a **self-contained episode**:

  * Has a start (buyer initiates chat)
  * Middle (multi-turn negotiations)
  * End (buyer decision)
* The larger simulation run is a sequence of these episodes, one per item (possibly with internal loops/iterations inside each episode).

---

## 5. Communication & Visibility Model

### 5.1 Chat Metaphor

Each item negotiation is conceptually like a **WhatsApp group**:

* **Participants:**

  * `Buyer`
  * `Seller_A`, `Seller_B`, ..., `Seller_N` (only those carrying that item)

* **Rules:**

  * Buyer can send:

    * Public messages
    * Seller-specific messages with `@seller_name`
  * **Only seller-specific messages are visible to that seller**.
    For simulation: each seller agent receives **only** the subset of messages from the buyer where they are mentioned.
  * Sellers respond only when:

    * They are explicitly @mentioned
    * Or when we allow “initiative” (e.g., they respond after each buyer broadcast that’s visible to them).

### 5.2 Decentralized Communication

* **Conceptual stance:**

  * There is **no “god” agent** making the decisions.
  * Buyer and each seller act based on **local views**:

    * Buyer has a global view of all seller states (hidden knowledge).
    * Sellers only see what is logically available to them.
* Under the hood, there is still an orchestrator (LangGraph-style) passing messages, but **logically**:

  * Each agent is an independent entity with own state and policy.
  * Communication is message-based, not direct function calls like “decide price”.

### 5.3 Knowledge Partitioning

* **Public knowledge**:

  * Item name, requested quantity
  * Buyer’s high-level budget range (if we choose to share)
  * Generic info like “market is competitive”
* **Buyer-private knowledge**:

  * Sellers’ cost and least_price
  * Sellers’ internal priorities and style knobs
* **Seller-private knowledge**:

  * Their own cost structure & internal willingness to negotiate
  * Their own negotiation history with buyer (for that item and past runs)

---

## 6. Agent Decision Logic (Conceptual)

### 6.1 Buyer Decision Logic

For each item:

1. Collect offers from sellers:

   * Price(s)
   * Any additional perks (warranty, express delivery, bundle offers)
   * Observed tone / respect

2. Evaluate each seller offer using a **scoring function**, conceptually combining:

   * **Price score:**

     * Lower price → better
     * If price exceeds item’s implicit budget share → heavily penalized
   * **Behavior score:**

     * Very rude → penalty
     * Very sweet / helpful → bonus
   * **Trust/consistency score:**

     * Seller flip-flopping or contradicting itself → penalty
   * **Retention perspective:**

     * If buyer wants long-term relationship (scenario configurable), may favor consistent fair pricing over rock-bottom.

3. Decide:

   * Choose best seller for this item, if any pass thresholds.
   * Optionally push for “final counter-offer” with top seller before finalizing.
   * Or decide **not to purchase** that item.

4. Enforce **global budget constraint**:

   * The buyer considers cumulative spend so far across items when deciding:

     * Accept / reject offers for remaining items
     * Possibly drop lower-priority items to afford high-priority ones.

### 6.2 Seller Decision Logic

Given an incoming `@seller_name` message about item X:

1. Parse buyer’s intent:

   * Asking for first quote?
   * Asking for discount?
   * Threatening to go to “other sellers”?
2. Consider numeric constraints:

   * Cost price `c`
   * Current offer price `p_current`
   * Floor `least_price = p_min`
3. Decide on new offer:

   * If buyer’s ask < `p_min` → politely or rudely reject.
   * If buyer’s ask between `p_min` and `selling_price`:

     * Maybe meet in the middle or step down gradually, using priority weights:

       * High retention weight → more flexibility
       * High profit weight → more resistance
4. Choose tone:

   * Based on seller style configuration, plus buyer’s behavior:

     * If buyer is very demanding, rude seller may push back.
     * Sweet seller may stay polite and persuasive.
5. Send response:

   * New price offer (or refusal)
   * Justification, marketing spin, or value proposition.

---

## 7. Model Backends & Runtime Modes

### 7.1 Two Inference Backends

The product supports two categories of model backends:

1. **Local inference (on device):**

   * Using **LM Studio / Ollama** with local models (e.g., LLaMA-family, Mistral, etc.)
   * Pros: no network dependency, full control.
   * Cons: slower, likely **sequential** simulation to avoid resource contention.

2. **Remote inference (OpenRouter):**

   * Hosted models via HTTP APIs.
   * Pros: can handle **batched / parallel** calls more easily; access to stronger models.
   * Cons: network latency, cost, rate limits.

### 7.2 Simulation Schedules

* **Local mode:**

  * Run **sequentially** item-by-item and message-by-message (to keep resource usage sane).
  * Good for hackathon demos on a laptop.

* **Remote mode:**

  * Can support more **parallel calls**:

    * Multiple sellers responding in parallel for the same buyer message.
    * Multiple items processed in batched simulations.

### 7.3 Streaming Responses

All chat-like interactions should be **streamed** to the UI:

* When buyer or sellers speak, the message appears token-by-token / line-by-line.
* This makes the simulation feel like a real group chat unfolding in real time, even though it's synthetic.

---

## 8. State & Data Handling

### 8.1 In-Memory Marketplace State

For hackathon scope, everything is stored **in memory** during the run:

* **Buyer state:** demand map, budget, negotiation history (per item).
* **Sellers state:** inventory, dynamic pricing movements, conversation flags.
* **Conversations:** message history per item room.

No need for full database design in this doc; conceptually:

```text
SimulationRun
  - buyer_profile
  - sellers: [SellerProfile]
  - items: [ItemConfig]
  - conversations: { item_name → ConversationLog }
  - decisions: { item_name → PurchaseDecision }
```

### 8.2 Persistent Logs (Minimal)

Even though we don’t version full marketplace state, we **do persist**:

* Final **conversation logs per item** after negotiation ends.
* Final **purchase decisions**:

  * Which seller won item X
  * Final agreed price
  * Reason codes (if we choose to generate them)
* This allows:

  * Retro analysis of strategies
  * Comparative runs with different model settings.

---

## 9. User Experience / Configuration Flow

### 9.1 Seller Configuration Form (up to 10 sellers)

Fields per seller:

* **Seller name / handle** (used as `@seller_name` in chat)
* **Inventory table**:

  * Item name
  * Cost price
  * Selling price
  * Least price
* **Priority sliders / inputs:**

  * Customer retention vs profit maximization
* **Style configuration:**

  * Rude ↔ Neutral ↔ Very Sweet

### 9.2 Buyer Configuration Form

Fields:

* **Item demand map:**

  * Add rows: item name + quantity
* **Budget range:**

  * Min budget
  * Max budget
* (Optional) Preferences:

  * Price sensitivity
  * Tone preference
  * Max conversation length per item

### 9.3 Model & Run Settings

* Choose:

  * Local vs Remote model backend
  * For each agent type (Buyer / Seller), which backend to use
* Choose:

  * Number of items to simulate in this run
  * Whether to run:

    * Single run, or
    * Multiple runs with slightly varied random seeds (for experimentation).

### 9.4 Simulation View

For each item:

* **Chat window**:

  * Shows buyer messages and each seller’s responses.
  * From the viewer’s perspective, we display the full conversation (for debugging), but logically sellers don’t see each other.
* **Sidebar panel**:

  * Shows:

    * Sellers involved for this item
    * Their cost / selling / least prices (visible only to the tool owner, not to agents logically)
    * Buyer’s remaining budget.

At the end of each item negotiation:

* Display **Decision card**:

  * Selected seller
  * Final price vs initial selling price vs least_price
  * Savings / margin stats.

---

## 10. Success Criteria & Metrics

To evaluate the product and the simulations, we can track:

* **Buyer-centric metrics:**

  * Total spend vs max budget
  * Number of items successfully purchased
  * Average discount (selling_price − final_price)
  * Number of negotiation turns per item

* **Seller-centric metrics:**

  * Profit per item (final_price − cost_price)
  * Times they lost to other sellers (even if they don’t know it in-world)
  * Correlation between tone and win rate

* **System-centric metrics:**

  * Latency per LLM call (local vs remote)
  * Tokens per simulation run
  * Concurrency behavior (for OpenRouter runs)

---

## 11. Future Extensions (Out of Scope but Natural Next Steps)

* Multiple buyers simultaneously competing for limited stock.
* Marketplace coordinator agent:

  * Sets recommended prices
  * Enforces marketplace rules
* Fraud/risk agent:

  * Flags suspicious sellers or unrealistic offers.
* Recommendation agent:

  * Suggests alternative items if item can’t be purchased within budget.
* Basic reinforcement / learning logic:

  * Sellers adjusting future strategies based on win/loss logs.
* Visualization layer:

  * Price trajectories, negotiation curves, strategy clustering.

---

## 12. Summary

You now have a full **product and conceptual architecture** for:

* A **1 Buyer ↔ N Sellers** multi-agent ecommerce marketplace simulator
* With:

  * Asymmetric information
  * WhatsApp-style multi-agent chat for each item
  * Dynamic negotiation strategies driven by LLMs
  * Dual model backends (local and remote)
  * In-memory state & logged conversations for hackathon-friendly implementation.

Next step (when you’re ready) would be to turn this into:

* A concrete LangGraph graph design (nodes/edges for Buyer, Sellers, and message routing), and
* Actual backend implementation using Ollama/LM Studio + OpenRouter.

But for now, this doc covers the **idea and behavior** in full, as requested.
