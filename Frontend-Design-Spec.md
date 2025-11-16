# Multi-Agent Ecommerce Marketplace - Frontend Design Specification
## Hackathon Edition - Quick Implementation Guide

**Version:** 1.0  
**Date:** November 15, 2025  
**Target:** Hackathon MVP (Single-day build)

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [User Journey](#2-user-journey)
3. [Screen-by-Screen Breakdown](#3-screen-by-screen-breakdown)
4. [Component Architecture](#4-component-architecture)
5. [State Management Strategy](#5-state-management-strategy)
6. [UI/UX Patterns](#6-uiux-patterns)
7. [Technology Stack](#7-technology-stack)
8. [Responsive Design](#8-responsive-design)
9. [Real-time Updates Strategy](#9-real-time-updates-strategy)
10. [Error Handling & Loading States](#10-error-handling--loading-states)
11. [Implementation Timeline](#11-implementation-timeline)

---

## 1. Design Philosophy

### Core Principles

**🎯 Hackathon-First**
- Build fast, iterate faster
- Focus on core flow, skip edge cases
- Hardcoded test data for demos
- No authentication (single user assumed)

**🎨 Visual Style**
- Clean, modern interface
- Clear agent identification (buyer vs sellers)
- Real-time feedback emphasis
- Mobile-first approach (but desktop primary for demo)

**⚡ Performance Goals**
- Fast initial load (<2s)
- Instant UI feedback
- Smooth streaming animations
- No janky scrolling

**👥 User Experience**
- Minimal clicks to complete flow (3-step process)
- Clear progress indicators
- Obvious next actions
- Helpful error messages

---

## 2. User Journey

### 2.1 Complete Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         START                                    │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 1: LANDING / HOME                                        │
│  - Welcome message                                               │
│  - "Start New Episode" button                                    │
│  - (Optional) "Load Previous Episode" if time permits            │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 2: EPISODE CONFIGURATION WIZARD                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 1: Add Seller Agents (One by One)                   │   │
│  │  - Seller identity, inventory, internal profile           │   │
│  │  - Repeat up to 10 sellers                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 2: Configure Buyer Purchase Plan                     │   │
│  │  - Per-item: name, quantity, min/max price                │   │
│  │  - NO global budget concept                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 3: LLM Settings (LM Studio Only)                     │   │
│  │  - Model selection, temperature, max tokens               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  [Generate Negotiations] button                                  │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 3: NEGOTIATION DASHBOARD                                 │
│  - List of items from buyer purchase plan                        │
│  - For each item: Matched sellers + negotiation status           │
│  - Items without sellers marked as "Unfulfillable"               │
│  - [Start Negotiation] per item                                  │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 4: PER-ITEM NEGOTIATION ROOM                             │
│  ┌────────────────┐  ┌──────────────────────────────────────┐   │
│  │  Current       │  │       Live Chat                       │   │
│  │  Offers        │  │  - Buyer messages to matched sellers  │   │
│  │  Panel         │  │  - Seller responses (streaming)       │   │
│  │  (This Item)   │  │  - @mentions for specific sellers     │   │
│  └────────────────┘  └──────────────────────────────────────┘   │
│  - Item: X, Quantity: Y, Price Range: $A-$B                     │
│  - Progress: Round X/10                                          │
│  - [Force Decision] button (optional)                            │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  DECISION MODAL                                                  │
│  - Selected seller + final price for this item                   │
│  - LLM-generated decision reason                                 │
│  - [Next Item] or [View Final Receipt] button                    │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 5: FINAL RECEIPT                                         │
│  - Episode summary with timestamp                                │
│  - Itemized table: item, seller, price, total                   │
│  - Items with "No Deal" status and reasons                       │
│  - Total items purchased and total spend                         │
│  - [Download Report] [Start New Episode]                         │
└─────────────────────────────────────────────────────────────────┘
                         ▼
                      END
```

### 2.2 Key User Actions

> Terminology note: the UI uses the term **“Episode”** for user-facing clarity, while the backend represents this as a **Session** (`session_id`) and **Negotiation Runs** (`room_id`/`negotiation_id`).

| Action | Screen | Backend Call | User Feedback |
|--------|--------|--------------|---------------|
| Create episode (initialize session) | Configuration | `POST /api/v1/simulation/initialize` | Loading spinner → Redirect to dashboard with generated negotiation rooms |
| View episode/session details | Dashboard | `GET /api/v1/simulation/{session_id}` | Refresh episode metadata and negotiation rooms |
| Start item negotiation | Dashboard | `POST /api/v1/negotiation/{room_id}/start` | Transition to per-item chat and open SSE stream |
| Watch negotiation | Negotiation Room | `GET /api/v1/negotiation/{room_id}/stream` (SSE) | Live message updates and offer updates |
| View decision | Negotiation Room | Auto from stream (`negotiation_complete` event) | Modal popup |
| View final receipt (summary) | Receipt | `GET /api/v1/simulation/{session_id}/summary` | Display itemized episode/session results |

---

## 3. Screen-by-Screen Breakdown

### 3.1 Screen 1: Landing Page

**Purpose:** Welcome users and initiate session creation

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│                    🛒 Multi-Agent Marketplace                 │
│                                                               │
│              Simulate ecommerce negotiations with             │
│                   AI-powered buyer & sellers                  │
│                                                               │
│                   ┌─────────────────────┐                     │
│                   │  Create New Session │                     │
│                   └─────────────────────┘                     │
│                                                               │
│              (Optional: View Previous Sessions)               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Elements:**
- **Hero Section:** Large title + tagline
- **Primary CTA:** "Create New Session" button (prominent, centered)
- **Secondary Options:** (If time) Previous sessions list
- **Footer:** Hackathon info, team credits

**Design Notes:**
- Simple, uncluttered
- Big, obvious button
- No navigation needed (single flow)

---

### 3.2 Screen 2: Episode Configuration Wizard

**Purpose:** Collect all episode configuration in step-by-step process

**Layout:** Multi-step wizard with progressive sections

```
┌──────────────────────────────────────────────────────────────┐
│  Episode Configuration (Step 2/3)                   [X Close] │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ 👤 Buyer Purchase Plan                              ▼  ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Buyer Name: [________________________]                 ┃  │
│  ┃                                                         ┃  │
│  ┃  Purchase Plan (Per-Item Constraints):                  ┃  │
│  ┃  ┌──────────────────────────────────────────────┐      ┃  │
│  ┃  │ Item: [Laptop____] Qty: [2_]                 │      ┃  │
│  ┃  │ Min Price: [$900] Max Price: [$1200]         │      ┃  │
│  ┃  │ [X Remove]                                    │      ┃  │
│  ┃  └──────────────────────────────────────────────┘      ┃  │
│  ┃  ┌──────────────────────────────────────────────┐      ┃  │
│  ┃  │ Item: [Mouse____] Qty: [5_]                  │      ┃  │
│  ┃  │ Min Price: [$15_] Max Price: [$25_]          │      ┃  │
│  ┃  │ [X Remove]                                    │      ┃  │
│  ┃  └──────────────────────────────────────────────┘      ┃  │
│  ┃  [+ Add Item to Purchase Plan]                          ┃  │
│  ┃                                                         ┃  │
│  ┃  Note: No global budget - each item has independent     ┃  │
│  ┃  min/max price constraints only.                        ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ 🏪 Sellers Configuration (0/10)                     ▼  ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Seller #1                                [X Remove]    ┃  │
│  ┃  ┌────────────────────────────────────────────────┐    ┃  │
│  ┃  │ Name: [__________________]                     │    ┃  │
│  ┃  │                                                 │    ┃  │
│  ┃  │ Profile:                                        │    ┃  │
│  ┃  │   Priority: ( ) Customer Retention              │    ┃  │
│  ┃  │             (•) Maximize Profit                 │    ┃  │
│  ┃  │   Style:    (•) Very Sweet  ( ) Rude            │    ┃  │
│  ┃  │                                                 │    ┃  │
│  ┃  │ Inventory: [+ Add Item]                         │    ┃  │
│  ┃  │  • Laptop: Cost $800, Sell $1200, Min $1000    │    ┃  │
│  ┃  │    Stock: 10 units                              │    ┃  │
│  ┃  └────────────────────────────────────────────────┘    ┃  │
│  ┃                                                         ┃  │
│  ┃  [+ Add Another Seller]                                 ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ 🤖 LLM Configuration (LM Studio Only)                ▼  ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Model: [llama-3-8b-instruct        ▼]                 ┃  │
│  ┃  Temperature: [0.7____] Max Tokens: [500___]           ┃  │
│  ┃                                                         ┃  │
│  ┃  Note: All agents use LM Studio backend for inference. ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│               [Initialize Episode] [Use Sample Data]          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Key Features:**

**Buyer Purchase Plan Section:**
- Text input for buyer name
- Dynamic list for purchase plan items
- Per-item constraints: name, quantity, min price, max price
- Validation: min price < max price per item
- Add/remove item buttons
- No global budget concept

**Sellers Section:**
- Repeatable seller cards (max 10)
- Each seller has:
  - Name input
  - Radio buttons for profile (priority, style)
  - Nested inventory items (dynamic list)
  - Each inventory item: name, cost, selling price, least price, stock
- Validation: cost < least < selling
- Color-coded by priority/style for quick scanning

**LLM Section:**
- Dropdown for model selection (LM Studio models only)
- Sliders for temperature and max_tokens
- Note about LM Studio requirement

**Helpers:**
- "Use Sample Data" button - loads pre-filled demo episode config
- Real-time validation feedback (red borders, error messages)
- Progress indicator: "X/10 sellers added"
- Step-by-step wizard navigation

**Design Notes:**
- Multi-step wizard approach for better UX
- Progressive disclosure of configuration sections
- Step 1: Add sellers → Step 2: Configure buyer plan → Step 3: LLM settings
- Auto-validation at each step before proceeding
- "Initialize Episode" creates session and matches sellers to items

---

### 3.3 Screen 3: Negotiation Dashboard

**Purpose:** Overview of all items in buyer's purchase plan and their seller matching status for the current episode/session

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│  Episode: #550e8400  |  Buyer: John Doe  |  Items: 2/2       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Purchase Plan / Episode Overview                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Items Planned: 2 | Negotiations Started: 0 | Completed: 0│  │
│  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0%      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Items from Purchase Plan (2)                                 │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  💻 Laptop (Want: 2 units)                             │  │
│  │  Price Constraints: $900 - $1200 per unit              │  │
│  │  Matched Sellers: TechStore, GadgetHub, CompuWorld     │  │
│  │                                                         │  │
│  │  Status: Ready to Negotiate   [Start Negotiation]      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  🖱️ Mouse (Want: 5 units)                              │  │
│  │  Price Constraints: $15 - $25 per unit                 │  │
│  │  Matched Sellers: None Available                        │  │
│  │                                                         │  │
│  │  Status: Unfulfillable        [Skip Item]              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│                                       [View Episode Details] │
└──────────────────────────────────────────────────────────────┘
```

**Elements:**

**Header Bar:**
- Episode ID
- Buyer name
- Item count (completed/total)
- (Optional) Episode creation time

**Progress Widget:**
- Visual progress bar showing negotiation completion
- Real-time updates as item negotiations finish
- Color changes: gray (not started) → blue (in progress) → green (completed)

**Item Cards:**
Each card shows:
- Item emoji/icon + name
- Quantity wanted from purchase plan
- Per-item price constraints (min - max per unit)
- List of matched sellers (based on inventory)
- Status badge:
  - **Ready:** Gray, "Start Negotiation" button
  - **In Progress:** Blue, "Resume" button + live indicator
  - **Completed:** Green, "View Details" button + final price
  - **Unfulfillable:** Red, "Skip Item" button

**Interactions:**
- Click "Start Negotiation" → Transition to Per-Item Negotiation Room
- Click seller name → Popup with seller details and inventory
- Click "View Details" → Show negotiation summary and decision
- Click "Skip Item" → Mark as unfulfillable, continue to next

**Design Notes:**
- Use cards for clear item separation
- Status colors: Gray (ready), Blue (in progress), Green (completed), Red (unfulfillable)
- Clear indication of seller matching results
- Focus on per-item constraints rather than global budget

---

### 3.4 Screen 4: Per-Item Negotiation Room

**Purpose:** Real-time chat interface for buyer negotiating with matched sellers for a specific item

**Layout:** Split-screen design focused on single item

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard  |  Laptop Negotiation  |  Round: 3/10  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌──────────────────────────────────────┐ │
│  │              │   │  💬 Live Chat                        │ │
│  │  Current     │   ├──────────────────────────────────────┤ │
│  │  Offers      │   │                                      │ │
│  │  (Laptop)    │   │  [Buyer] 10:30:01                    │ │
│  │              │   │  Hello @TechStore and @GadgetHub!    │ │
│  │  TechStore   │   │  I need 2 laptops. What can you     │ │
│  │  💰 $1150    │   │  offer?                              │ │
│  │  📦 2 units  │   │                                      │ │
│  │  🕐 10:31    │   │  [TechStore] 10:30:15                │ │
│  │  [Best]      │   │  Hi! 😊 I can offer $1150 per unit   │ │
│  │              │   │  💰 Offer: $1150 per unit            │ │
│  │  GadgetHub   │   │                                      │ │
│  │  💰 $1100    │   │  [GadgetHub] 10:30:18                │ │
│  │  📦 2 units  │   │  Best I can do is $1100. Final.      │ │
│  │  🕐 10:32    │   │  💰 Offer: $1100 per unit            │ │
│  │  [Lowest]    │   │                                      │ │
│  │              │   │  [Buyer] 10:30:45                    │ │
│  │              │   │  @GadgetHub that's within my range!  │ │
│  └──────────────┘   │  Can you match quantity?              │ │
│                     │                                      │ │
│  Item Constraints   │  [typing...] ⏳                      │ │
│  Want: 2 units      │                                      │ │
│  Min: $900/unit     │                                      │ │
│  Max: $1200/unit    │                                      │ │
│                     └──────────────────────────────────────┘ │
│                                                               │
│                                      [Force Decision] [Stop]  │
└──────────────────────────────────────────────────────────────┘
```

**Left Panel: Current Offers (This Item Only)**

**Structure:**
- Seller cards showing only matched sellers for this specific item
- Auto-sorted by price (lowest to highest)
- Each card shows:
  - Seller name with style badge (😊 sweet / 😠 rude)
  - Current price per unit (large, bold)
  - Available quantity for this item
  - Last updated time
  - Badge: "Best Price" or "Within Budget" or "Over Budget"

**Item Constraints Panel:**
- Shows buyer's constraints for this specific item
- Wanted quantity
- Min/max price per unit (from purchase plan)
- No global budget references

**Visual Indicators:**
- Green highlight for best price within constraints
- Red highlight for prices outside min/max range
- Pulsing animation when offer updates
- Clear indication if seller can fulfill quantity needed

**Right Panel: Live Chat**

**Message Types:**

1. **Buyer Messages:**
   - Left-aligned
   - Blue background
   - @mentions highlighted in yellow
   - Avatar: 👤 or buyer emoji

2. **Seller Messages:**
   - Right-aligned
   - Gray/white background (color-coded by seller)
   - Avatar: 🏪 or seller-specific icon
   - Show personality (emojis for sweet, blunt for rude)

3. **System Messages:**
   - Centered
   - Light gray background
   - Examples: "Round 3 started", "Offer updated"

**Special Elements:**
- **Offer Updates:** Show price change inline with message
  ```
  [TechStore]: I can go down to $1100
  💰 Offer Updated: $1150 → $1100
  ```
- **@Mentions:** Highlighted with background color + tooltip showing "This message is for TechStore"
- **Typing Indicator:** Animated dots when LLM is generating response
- **Timestamp:** Small, gray, on each message

**Actions:**
- Auto-scroll to latest message
- Manual scroll to review history
- "Force Decision" button (triggers buyer decision logic)
- "Stop" button (abandons negotiation)

**Design Notes:**
- Chat should feel like WhatsApp/Slack
- Smooth animations for new messages
- Loading skeletons while waiting for responses
- Sound notification (optional) when seller responds

---

### 3.5 Decision Modal

**Purpose:** Show buyer's final decision after negotiation completes

**Layout:** Centered overlay modal

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│                 ╔═══════════════════════════════╗             │
│                 ║  🎉 Decision Made!            ║             │
│                 ╠═══════════════════════════════╣             │
│                 ║                               ║             │
│                 ║  Selected Seller:             ║             │
│                 ║  🏪 GadgetHub                 ║             │
│                 ║                               ║             │
│                 ║  Final Price: $1080/unit      ║             │
│                 ║  Quantity: 2 units            ║             │
│                 ║  Total Cost: $2160            ║             │
│                 ║                               ║             │
│                 ║  Reason:                      ║             │
│                 ║  "GadgetHub offered the best  ║             │
│                 ║  price within budget and was  ║             │
│                 ║  very responsive throughout   ║             │
│                 ║  the negotiation."            ║             │
│                 ║                               ║             │
│                 ║  Negotiation Stats:           ║             │
│                 ║  • Rounds: 5                  ║             │
│                 ║  • Duration: 2m 25s           ║             │
│                 ║  • Messages: 18               ║             │
│                 ║                               ║             │
│                 ║  [Next Item] [View Summary]   ║             │
│                 ║                               ║             │
│                 ╚═══════════════════════════════╝             │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Elements:**
- Celebration icon/animation (confetti effect)
- Large, clear display of winning seller
- Price breakdown (per unit, total)
- LLM-generated decision reason (in quotes)
- Stats summary (rounds, time, messages)
- Action buttons:
  - "Next Item" → Go to next pending item in dashboard
  - "View Summary" → Jump to final summary screen

**Design Notes:**
- Use modal overlay to focus attention
- Positive, celebratory tone
- Clear typography hierarchy
- Auto-close after 10 seconds if no action (go to next item)

---

### 3.6 Screen 5: Final Receipt

**Purpose:** Episode summary showing itemized results of all negotiations

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  🎊 Episode Complete!                                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📋 Episode Summary                                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Episode ID:         #550e8400                           │ │
│  │  Buyer:              John Doe                            │ │
│  │  Completed:          November 16, 2025 at 10:45 AM      │ │
│  │  Items Planned:      2                                   │ │
│  │  Items Purchased:    1                                   │ │
│  │  Total Spent:        $2160                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ✅ Successful Purchases (1)                              │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  💻 Laptop x2                                            │ │
│  │  ├─ Seller: GadgetHub                                    │ │
│  │  ├─ Final Price: $1080/unit                              │ │
│  │  ├─ Total Cost: $2160                                    │ │
│  │  ├─ Constraint Range: $900-$1200                         │ │
│  │  ├─ Negotiation: 5 rounds (2m 25s)                       │ │
│  │  └─ [View Chat Log]                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ❌ Failed Items (1)                                      │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  🖱️ Mouse x5                                             │ │
│  │  ├─ Constraint Range: $15-$25                            │ │
│  │  └─ Reason: No sellers available for this item          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📊 Episode Metrics                                       │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Total Negotiation Rounds:    5                          │ │
│  │  Total Duration:               2m 25s                    │ │
│  │  Total Messages Exchanged:     18                        │ │
│  │  Success Rate:                 50% (1/2 items)           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│         [Download PDF Report] [Start New Episode] [Home]     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Sections:**

1. **Episode Summary Card:**
   - Episode metadata (ID, buyer, timestamp)
   - High-level statistics (items planned vs purchased)
   - Total spend across all successful purchases

2. **Successful Purchases:**
   - Itemized list with full details per purchase
   - Show seller chosen, final price, total cost
   - Display original constraint range for context
   - Negotiation stats (rounds, duration)
   - Link to view full chat log

3. **Failed Items:**
   - Items from purchase plan that couldn't be fulfilled
   - Show original constraints that couldn't be met
   - Clear reasons for failure (no sellers, price mismatch, etc.)

4. **Episode Metrics:**
   - Aggregate stats across all negotiations in this episode
   - Success rate calculation
   - Total time and message counts

**Actions:**
- Download PDF report (episode receipt)
- Start new episode (new configuration)
- Go to home

**Design Notes:**
- Receipt-style layout (professional, itemized)
- Clear success vs failure visual distinction
- Focus on per-item results rather than budget utilization
- Episode-centric language throughout

---

## 4. Component Architecture

### 4.1 Component Hierarchy

```
App
├── Router
│   ├── LandingPage
│   ├── ConfigurationPage
│   │   ├── BuyerConfigForm
│   │   │   ├── NameInput
│   │   │   └── ShoppingListEditor
│   │   │       └── ItemRow (repeatable)
│   │   ├── SellersConfigForm
│   │   │   └── SellerCard (repeatable, max 10)
│   │   │       ├── SellerInfoInputs
│   │   │       ├── ProfileSelector (radio buttons)
│   │   │       └── InventoryEditor
│   │   │           └── InventoryItemRow (repeatable)
│   │   └── LLMConfigForm
│   │       ├── ProviderSelector
│   │       └── ModelDropdown
│   ├── DashboardPage
│   │   ├── EpisodeOverview
│   │   └── ItemCardList
│   │       └── ItemCard (repeatable)
│   ├── NegotiationRoomPage
│   │   ├── NegotiationHeader
│   │   ├── OffersPanel
│   │   │   └── OfferCard (repeatable per seller)
│   │   ├── ChatPanel
│   │   │   ├── MessageList
│   │   │   │   └── Message (repeatable)
│   │   │   │       ├── BuyerMessage
│   │   │   │       ├── SellerMessage
│   │   │   │       └── SystemMessage
│   │   │   └── TypingIndicator
│   │   └── ActionButtons
│   └── SummaryPage
│       ├── EpisodeSummaryCard
│       ├── PurchasesList
│       │   └── PurchaseCard (repeatable)
│       ├── FailedItemsList
│       │   └── FailedItemCard (repeatable)
│       └── MetricsCard
├── SharedComponents
│   ├── Button
│   ├── Input
│   ├── Modal
│   ├── Card
│   ├── Badge
│   ├── ProgressBar
│   ├── LoadingSpinner
│   ├── ErrorMessage
│   └── Tooltip
└── Providers
    ├── SessionProvider (global state)
    ├── NotificationProvider (toasts)
    └── ThemeProvider (optional)
```

### 4.2 Key Components Breakdown

#### **BuyerConfigForm**
- Inputs: buyer name (text)
- Shopping list: dynamic array of items with per-item min/max price and quantity
- Validation: per-item `maxPrice > minPrice`, items unique

#### **SellerCard**
- Repeatable component (up to 10)
- Contains: name, profile selector, inventory editor
- Self-contained validation
- Remove button (except when only 1 seller)

#### **ItemCard (Dashboard)**
- Shows item details, available sellers, status
- Conditional rendering of action button based on status
- Click handlers for navigation

#### **OffersPanel**
- Real-time sorting of offers
- Visual indicators (badges, colors)
- Animation on offer updates

#### **ChatPanel**
- Auto-scrolling message list
- Message type detection (buyer/seller/system)
- @mention highlighting
- Streaming text animation (optional)

#### **Message Components**
- BuyerMessage: Left-aligned, blue
- SellerMessage: Right-aligned, seller-specific color
- SystemMessage: Centered, gray

---

## 5. State Management Strategy

### 5.1 State Structure

**Global State (Context API or Zustand):**

```javascript
{
  episode: {
    id: null,
    status: 'idle', // idle | configuring | initializing | active | completed
    buyer: {
      name: '',
      purchasePlan: [
        {
          itemName: 'Laptop',
          quantity: 2,
          minPrice: 900,
          maxPrice: 1200
        }
      ]
    },
    sellers: [
      {
        id: 'seller_1',
        name: 'TechStore',
        profile: {
          customerRetentionWeight: 0.7,
          profitMaximizationWeight: 0.3,
          style: 'sweet'
        },
        inventory: [
          {
            itemName: 'Laptop',
            costPrice: 800,
            sellingPrice: 1200,
            leastPrice: 1000,
            availableQuantity: 10
          }
        ]
      }
    ],
    llmConfig: {
      model: 'llama-3-8b-instruct',
      temperature: 0.7,
      maxTokens: 500
    },
    createdAt: null
  },

  negotiations: {
    'negotiation_id_1': {
      negotiationId: 'negotiation_id_1',
      episodeId: 'episode_id',
      itemName: 'Laptop',
      status: 'pending', // pending | active | completed
      matchedSellers: ['seller_1', 'seller_2'],
      buyerConstraints: {
        quantity: 2,
        minPrice: 900,
        maxPrice: 1200
      },
      currentRound: 0,
      maxRounds: 10,
      messages: [],
      offers: {},
      decision: null,
      eventSource: null // SSE connection
    }
  },

  ui: {
    activeNegotiationId: null,
    showDecisionModal: false,
    notifications: [],
    loading: {
      initializingEpisode: false,
      generatingNegotiations: false,
      startingNegotiation: false
    },
    errors: {}
  }
}
```

### 5.2 State Updates

**Key Actions:**

1. **Initialize Episode:**
   - User submits episode config → Set loading
   - API call to create episode → Store episode data
   - Navigate to dashboard

2. **Generate Negotiations:**
   - System matches sellers to buyer's purchase plan items
   - Creates negotiation records for each viable item
   - Updates dashboard with matched/unmatched status

3. **Start Item Negotiation:**
   - User clicks "Start Negotiation" for specific item → Set loading
   - API call → Open SSE connection for that negotiation
   - Navigate to per-item negotiation room

4. **Receive SSE Events:**
   - Event: buyer_message → Add to messages[] for this negotiation
   - Event: seller_response → Add to messages[], update offers{} for this item
   - Event: negotiation_complete → Show decision modal for this item

5. **Complete Item Negotiation:**
   - Close SSE connection for this item
   - Update negotiation status to completed
   - Store decision/outcome
   - Navigate to next item or final receipt

### 5.3 Recommended Library

**For Hackathon:**

**Option 1: React Context API (Built-in)**
- Pros: No dependencies, simple
- Cons: Verbose for complex state
- Best for: Small teams, time-constrained

**Option 2: Zustand (Lightweight)**
- Pros: Simple API, minimal boilerplate
- Cons: One more dependency
- Best for: Slightly larger state, want cleaner code

**Recommendation:** Start with Context API, refactor to Zustand if needed

---

## 6. UI/UX Patterns

### 6.1 Color Scheme

**Primary Colors:**
```
Primary:     #3B82F6 (Blue)      - Buttons, links, buyer messages
Secondary:   #10B981 (Green)     - Success, best price
Warning:     #F59E0B (Orange)    - Warnings, constraint/price alerts
Danger:      #EF4444 (Red)       - Errors, failed items
Neutral:     #6B7280 (Gray)      - Text, borders, backgrounds
```

**Agent-Specific Colors:**
```
Buyer:       #3B82F6 (Blue)      - Buyer messages, avatar
Sellers:     Assigned from palette per seller
  - Seller 1: #8B5CF6 (Purple)
  - Seller 2: #EC4899 (Pink)
  - Seller 3: #14B8A6 (Teal)
  - ... (cycle through 10 distinct colors)
```

### 6.2 Typography

**Font Stack:**
```
Primary:     'Inter', 'Segoe UI', sans-serif
Monospace:   'Fira Code', 'Courier New', monospace (for prices)
```

**Sizes:**
```
Headings:
  H1: 2.5rem (40px)  - Page titles
  H2: 2rem (32px)    - Section headers
  H3: 1.5rem (24px)  - Card titles

Body:
  Large:  1.125rem (18px) - Important info
  Normal: 1rem (16px)     - Default text
  Small:  0.875rem (14px) - Captions, timestamps
```

### 6.3 Spacing System

**Use 8px base unit:**
```
xs:  0.5rem (8px)
sm:  1rem (16px)
md:  1.5rem (24px)
lg:  2rem (32px)
xl:  3rem (48px)
```

### 6.4 Animation Guidelines

**Use sparingly, purposefully:**

1. **Page Transitions:** 200-300ms ease-in-out
2. **Button Hovers:** 150ms ease
3. **Loading Spinners:** 1s continuous rotation
4. **New Messages:** Slide-in from bottom, 200ms
5. **Offer Updates:** Pulse effect, 500ms
6. **Modal Open/Close:** Fade + scale, 300ms

**No animations for:**
- Chat scrolling (instant)
- Text streaming (immediate append)

---

## 7. Technology Stack

### 7.1 Recommended Stack (Hackathon-Optimized)

**Core Framework:**
- **Next.js 14+ (App Router)** for routing/layout
- **React 18+** under the hood
- **Tailwind CSS** for styling (utility-first, fast)

**State Management:**
- **Context API** or **Zustand** (pick one)

**HTTP Client:**
- **Fetch API** (built-in, no dependencies)

**SSE Client:**
- **EventSource API** (built-in)

**Form Handling:**
- **React Hook Form** (optional, for complex validation)

**UI Components:**
- **Build custom** OR use lightweight library like **shadcn/ui** (if time permits)

**Icons:**
- **Lucide React** or **Hero Icons**

**Utilities:**
- **date-fns** (for timestamp formatting)
- **clsx** (for conditional classNames)

**Development Tools:**
- **ESLint** (basic rules)
- **Prettier** (auto-formatting)

### 7.2 Alternative Stacks

**If team prefers:**

**Vue Option:**
- Vue 3 + Vite
- Composition API
- Similar component structure

**Svelte Option:**
- SvelteKit
- Less boilerplate
- Great for speed

**Recommendation:** Stick with Next.js + Tailwind for maximum velocity

### 7.3 Project Structure (Next.js + App Router)

The frontend codebase lives in `frontend/` and follows a modular structure that mirrors backend concepts (session/episode configuration, negotiation rooms, summary):

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
    ├── features/                       # Feature modules aligned with backend
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
    │   └── shared/                     # Feature-level shared pieces
    │
    ├── lib/                            # API clients & shared logic
    │   ├── api/                        # Mirrors backend endpoints
    │   │   ├── client.ts               # Fetch wrapper + error handling
    │   │   ├── simulation.ts           # /simulation endpoints (init, summary)
    │   │   ├── negotiation.ts          # /negotiation endpoints + SSE helpers
    │   │   └── status.ts               # /health, /llm/status
    │   ├── forms/                      # Zod schemas mirroring backend models
    │   ├── router.ts                   # Route helpers (config, negotiations, summary)
    │   └── constants.ts                # Enums: priorities, speaking styles, etc.
    │
    ├── store/                          # Global state (e.g., Zustand or Context)
    │   ├── sessionStore.ts             # Active session/episode metadata
    │   ├── configStore.ts              # Draft configuration during wizard
    │   └── negotiationStore.ts         # Per-room messages, offers, active room
    │
    ├── components/                     # Shared UI primitives (buttons, inputs, modals)
    ├── styles/                         # Global styles, Tailwind config or CSS modules
    └── utils/                          # Helpers (formatting, @mention highlighting, etc.)
```

This layout lines up directly with the backend:
- `episode-config` ↔ `/api/v1/simulation/initialize`
- `negotiation-room` ↔ `/api/v1/negotiation/{room_id}/*` + SSE stream
- `summary-receipt` ↔ `/api/v1/simulation/{session_id}/summary`

---

## 8. Responsive Design

### 8.1 Breakpoints

```
Mobile:  < 640px
Tablet:  640px - 1024px
Desktop: > 1024px
```

### 8.2 Responsive Strategy

**Mobile (< 640px):**
- Configuration: Single column, stack all sections
- Dashboard: Full-width cards
- Negotiation Room: Stack offers panel above chat (vertical layout)
- Summary: Single column

**Tablet (640px - 1024px):**
- Configuration: Two-column layout where possible
- Dashboard: 2-column grid for item cards
- Negotiation Room: Side-by-side panels (narrower)
- Summary: Two-column grid

**Desktop (> 1024px):**
- Configuration: Three-column for sellers
- Dashboard: 3-column grid
- Negotiation Room: Full side-by-side (offers + chat)
- Summary: Optimized layout with sidebars

### 8.3 Mobile-First Approach

**Design mobile screens first, then scale up:**
1. Mobile layout (base styles)
2. Add tablet breakpoint (md:)
3. Add desktop breakpoint (lg:)

**Tailwind Example:**
```
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

**Demo Focus:**
- Optimize for desktop (primary demo environment)
- Mobile responsive is nice-to-have
- Tablet can reuse mobile styles

---

## 9. Real-time Updates Strategy

### 9.1 SSE Connection Management

**Connection Lifecycle:**

1. **Open Connection:**
   - When user clicks "Start Negotiation"
   - Create new EventSource to `/stream` endpoint
   - Store connection in state

2. **Listen for Events:**
   - buyer_message → Append to messages
   - seller_response → Append to messages, update offers
   - negotiation_complete → Show decision modal
   - error → Show error notification
   - heartbeat → Update "active" indicator

3. **Close Connection:**
   - When negotiation completes
   - When user navigates away
   - On component unmount (cleanup)

**Implementation Pattern:**

```javascript
// Pseudo-code
useEffect(() => {
  const eventSource = new EventSource(`/api/v1/negotiation/${roomId}/stream`);

  eventSource.addEventListener('buyer_message', handleBuyerMessage);
  eventSource.addEventListener('seller_response', handleSellerResponse);
  eventSource.addEventListener('negotiation_complete', handleComplete);
  eventSource.addEventListener('error', handleError);

  return () => {
    eventSource.close(); // Cleanup on unmount
  };
}, [roomId]);
```

### 9.2 UI Updates During Streaming

**Immediate Feedback:**
- Show "typing..." indicator when waiting for response
- Animate message appearance (slide-in)
- Auto-scroll chat to latest message
- Pulse animation on offer updates

**Optimistic Updates:**
- None needed (backend drives all updates)

**Error Recovery:**
- If connection drops, show "Reconnecting..." toast
- Auto-retry with exponential backoff
- Manual "Retry" button if fails

---

## 10. Error Handling & Loading States

### 10.1 Error Categories

**1. Validation Errors (User Input):**
- Show inline field errors
- Red border on invalid inputs
- Error message below field
- Prevent form submission

**2. API Errors (Backend):**
- Toast notifications for general errors
- Modal for critical errors (session not found)
- Retry buttons where applicable

**3. Network Errors:**
- "Connection lost" banner at top
- Retry mechanism
- Offline indicator

**4. LLM Errors:**
- "LLM service unavailable" message
- Suggest checking LM Studio
- Fallback to error state in chat

### 10.2 Loading States

**Loading Indicators:**

1. **Full-Page Loading:**
   - During session initialization
   - Spinner + "Initializing marketplace..." text
   - Overlay entire screen

2. **Section Loading:**
   - When starting negotiation
   - Skeleton screens for chat
   - Spinner in button

3. **Inline Loading:**
   - Typing indicator in chat
   - "Seller is thinking..." message
   - Animated dots

4. **Button States:**
   - Disabled state during submission
   - Spinner inside button
   - Changed text: "Loading..." or "Starting..."

**Example Loading States:**

**Configuration Submit:**
```
[Initialize Marketplace] → [⏳ Initializing...]
```

**Start Negotiation:**
```
[Start Negotiation] → [⏳ Starting...]
```

**Chat Waiting:**
```
[Buyer] Hello @TechStore!
[typing...] ⌛
```

### 10.3 Empty States

**No Sellers Available:**
```
┌─────────────────────────────────────┐
│  😔 No Sellers Available             │
│  None of the sellers have this item  │
│  in their inventory.                 │
│                                      │
│  [Go Back to Dashboard]              │
└─────────────────────────────────────┘
```

**No Messages Yet:**
```
┌─────────────────────────────────────┐
│  💬 Negotiation Starting...          │
│  The buyer is crafting an opening    │
│  message. Hang tight!                │
└─────────────────────────────────────┘
```

---

## 11. Implementation Timeline

### Day 1: Sprint Plan (8 Hours)

**Hour 0-1: Setup**
- [ ] Initialize React + Vite project
- [ ] Setup Tailwind CSS
- [ ] Create basic routing structure
- [ ] Setup state management (Context/Zustand)

**Hour 1-3: Configuration Wizard**
- [ ] Build BuyerPurchasePlanForm (per-item constraints)
- [ ] Build SellerCard component (repeatable, step-by-step)
- [ ] Implement form validation (price ranges, inventory)
- [ ] Connect to POST /episode/initialize API
- [ ] Add "Use Sample Data" helper for episode config

**Hour 3-5: Dashboard & Navigation**
- [ ] Build DashboardPage layout (episode-based)
- [ ] Create ItemCard component (per-item constraints display)
- [ ] Implement negotiation progress tracker
- [ ] Connect to GET /episode/{id} API for seller matching
- [ ] Add navigation to per-item negotiation rooms

**Hour 5-7: Negotiation Room**
- [ ] Build split-screen layout (offers + chat)
- [ ] Implement OffersPanel with OfferCard
- [ ] Build ChatPanel with message components
- [ ] Connect SSE stream
- [ ] Handle real-time message updates
- [ ] Implement typing indicators

**Hour 7-8: Final Receipt & Polish**
- [ ] Build Final Receipt layout (episode summary)
- [ ] Connect to GET /episode/{id}/receipt API
- [ ] Add Decision Modal (per-item)
- [ ] Final styling pass
- [ ] Test end-to-end episode flow
- [ ] Fix critical bugs

---

### Priority Features (Must-Have)

**P0 (Critical Path):**
- ✅ Episode configuration wizard (step-by-step)
- ✅ Episode initialization with seller matching
- ✅ Dashboard with per-item negotiation cards
- ✅ Per-item negotiation room with SSE streaming
- ✅ Chat message display (buyer + matched sellers)
- ✅ Offers panel with item-specific constraints
- ✅ Decision modal (per-item)
- ✅ Final receipt screen (episode summary)

**P1 (Important):**
- Sample episode data loader
- Error handling (toasts)
- Loading states
- Basic animations (fade, slide)
- Negotiation progress tracker updates

**P2 (Nice-to-Have):**
- Advanced animations (confetti, pulse)
- Mobile responsive
- Download PDF report
- Dark mode
- Accessibility (ARIA labels)

**P3 (If Extra Time):**
- Previous episode viewer
- Seller detail popups with inventory
- Chat log export per item
- Episode analytics dashboard

---

## 12. Testing Strategy (Minimal)

### 12.1 Manual Testing Checklist

**Episode Configuration Flow:**
- [ ] Submit valid episode config → Success
- [ ] Submit invalid price constraints → Show errors
- [ ] Add/remove sellers step-by-step → Updates correctly
- [ ] "Use Sample Data" → Populates episode form

**Dashboard:**
- [ ] Shows all items from purchase plan correctly
- [ ] Shows seller matching results
- [ ] "Start Negotiation" button navigates to per-item room
- [ ] Progress tracker displays correctly

**Negotiation Room:**
- [ ] SSE connects successfully
- [ ] Messages appear in real-time
- [ ] Offers update correctly
- [ ] @mentions highlighted
- [ ] Decision modal appears on completion

**Final Receipt:**
- [ ] Shows all successful purchases with details
- [ ] Episode summary information correct  
- [ ] Failed items with reasons displayed
- [ ] Total spend calculations correct

### 12.2 Browser Testing

**Primary:** Chrome (latest)  
**Secondary:** Firefox, Safari (if time)  
**Skip:** IE, old browsers

### 12.3 Edge Cases

**Handle gracefully:**
- No internet connection
- LM Studio not running
- Episode expires or becomes invalid
- Zero sellers available for purchase plan items
- Price constraints impossible to meet

---

## 13. Accessibility Considerations

### 13.1 Basic Requirements (Hackathon Scope)

**Keyboard Navigation:**
- All buttons/links tabbable
- Logical tab order
- Enter key submits forms

**ARIA Labels:**
- Add labels to interactive elements
- Use semantic HTML (button, input, etc.)

**Color Contrast:**
- Text readable (WCAG AA minimum)
- Don't rely solely on color for info

**Focus Indicators:**
- Visible outline on focus
- Don't remove default outline

**Screen Reader:**
- Alt text for images/icons
- Descriptive button labels

### 13.2 Skip for Hackathon

- Full WCAG compliance
- Advanced keyboard shortcuts
- Screen reader optimization
- High contrast mode

---

## 14. Performance Optimizations

### 14.1 Quick Wins

**Code Splitting:**
- Lazy load routes
- Only load active negotiation room

**Image Optimization:**
- Use SVG for icons
- Compress images (if any)

**Bundle Size:**
- Don't over-import libraries
- Tree-shake unused code

**Rendering:**
- Memoize expensive components
- Use keys in lists
- Avoid unnecessary re-renders

### 14.2 Skip for Hackathon

- Server-side rendering
- Advanced caching strategies
- Service workers
- Web workers for background tasks

---

## 15. Deployment Strategy

### 15.1 Hackathon Demo

**Local Development:**
```bash
npm run dev  # Frontend on :5173
              # Backend on :8000
```

**Demo Setup:**
1. Start backend (FastAPI)
2. Start LM Studio (if using)
3. Start frontend (Vite)
4. Open browser to localhost:5173

### 15.2 Quick Deploy (Optional)

**If need to host:**

**Frontend:** Vercel, Netlify, GitHub Pages
- Build: `npm run build`
- Deploy: `vercel` or `netlify deploy`

**Backend:** Railway, Render, Fly.io
- Container or direct deploy

**Full Stack:** DigitalOcean, AWS (overkill for hackathon)

**Recommendation:** Demo locally, skip deployment unless required

---

## 16. Design Assets & Resources

### 16.1 Icons

**Use Lucide React for all icons:**
- ShoppingCart (marketplace)
- User (buyer)
- Store (seller)
- MessageCircle (chat)
- TrendingUp (offers)
- CheckCircle (success)
- XCircle (failure)
- DollarSign (price)
- Package (inventory)
- Settings (configuration)

### 16.2 Illustrations (Optional)

**If time permits:**
- Empty state illustrations from unDraw or Storyset
- Celebration animations from LottieFiles

**Skip if tight on time**

### 16.3 Fonts

**Primary:** Inter (Google Fonts)
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
```

---

## 17. Common Pitfalls to Avoid

### 17.1 Technical Pitfalls

❌ **Over-engineering state management**
  - Stick to simple Context API
  - Don't add Redux for hackathon

❌ **Complex animations**
  - Keep it simple (fade, slide)
  - Avoid custom physics-based animations

❌ **Perfect mobile responsive**
  - Focus on desktop first
  - Mobile is bonus points

❌ **Custom UI library**
  - Use Tailwind utility classes
  - Build simple custom components

❌ **Extensive testing**
  - Manual testing is enough
  - Skip unit/integration tests

### 17.2 UX Pitfalls

❌ **Too many steps in config**
  - Single-page form is better
  - Use "Sample Data" button

❌ **Unclear loading states**
  - Always show what's happening
  - Never leave user guessing

❌ **Hidden errors**
  - Show validation errors inline
  - Use toasts for API errors

❌ **Auto-scroll gone wrong**
  - Test chat auto-scroll carefully
  - Allow manual scroll override

---

## 18. Demo Preparation

### 18.1 Pre-Demo Checklist

**1 Hour Before:**
- [ ] Test full flow end-to-end
- [ ] Prepare sample data (preloaded)
- [ ] Clear browser cache
- [ ] Test on clean browser profile
- [ ] Close unnecessary apps (free RAM)
- [ ] Charge laptop fully

**Sample Data Setup:**
- Have 2-3 pre-configured scenarios ready
- One with all successful purchases
- One with mixed success/failure
- One with complex negotiation (many rounds)

### 18.2 Demo Script

**Suggested Flow (5 minutes):**

1. **Intro (30s):**
   - "Multi-agent marketplace with LLM negotiations"
   - "Buyer negotiates with multiple sellers using @mentions"

2. **Configuration (1m):**
   - Click "Use Sample Data"
   - Quick tour of buyer, sellers, LLM config
   - Click "Initialize"

3. **Dashboard (30s):**
   - Point out items, available sellers
   - Show per-item constraints and negotiation progress
   - Click "Start Negotiation" on Laptop

4. **Live Negotiation (2m):**
   - Watch buyer's opening message stream
   - Show @mentions highlighting
   - Watch sellers respond in real-time
   - Point out offers panel updating
   - Wait for decision

5. **Summary (1m):**
   - Show purchase details
   - Highlight how final prices relate to per-item constraint ranges
   - Show negotiation stats

**Total:** ~5 minutes with buffer for questions

### 18.3 Backup Plan

**If SSE streaming fails:**
- Have pre-recorded video of negotiation
- OR use polling fallback (if implemented)
- OR demo with mock data (hardcoded messages)

**If LLM is slow:**
- Use OpenRouter (faster than LM Studio)
- Use smaller model
- Pre-run negotiation, show replay

---

## 19. Future Enhancements (Post-Hackathon)

**If project continues:**

**Phase 2 Features:**
- [ ] User authentication
- [ ] Save/load sessions
- [ ] Export negotiations to PDF
- [ ] Analytics dashboard
- [ ] Multi-buyer support
- [ ] Seller reputation system

**Technical Improvements:**
- [ ] TypeScript migration
- [ ] Unit test coverage
- [ ] E2E tests (Playwright/Cypress)
- [ ] CI/CD pipeline
- [ ] Performance monitoring
- [ ] Error tracking (Sentry)

**UX Enhancements:**
- [ ] Dark mode
- [ ] Customizable themes
- [ ] Accessibility audit
- [ ] Keyboard shortcuts
- [ ] Advanced filters/search
- [ ] Notification preferences

---

## 20. Team Collaboration

### 20.1 Recommended Split

**If 2 Frontend Developers:**

**Developer 1:**
- Configuration screen
- Dashboard screen
- Summary screen
- API integration layer
- State management setup

**Developer 2:**
- Negotiation room layout
- SSE streaming logic
- Chat components
- Offers panel
- Real-time updates

**Shared:**
- Design system (colors, components)
- Routing setup
- Error handling patterns

### 20.2 Git Workflow

**Simple Hackathon Flow:**

**Branches:**
- `main` - Stable, demo-ready
- `dev` - Active development
- `feature/screen-name` - Individual features

**Process:**
1. Branch from `dev`
2. Work on feature
3. Merge to `dev` frequently
4. Test on `dev`
5. Merge to `main` before demo

**No PRs, no code reviews** (too slow for hackathon)

---

## 21. Conclusion

### Summary

This frontend design provides a **hackathon-optimized**, **single-day buildable** interface for the multi-agent marketplace. Key takeaways:

✅ **5 Core Screens:** Landing → Config → Dashboard → Negotiation → Summary  
✅ **Real-time Focus:** SSE streaming for live negotiations  
✅ **Simple State:** Context API sufficient  
✅ **Fast Tech Stack:** React + Vite + Tailwind  
✅ **Desktop-First:** Mobile is nice-to-have  

### Critical Path

**Must complete for working demo:**
1. Configuration form (1.5h)
2. Session initialization (0.5h)
3. Dashboard navigation (1h)
4. Negotiation room + SSE (3h)
5. Summary screen (1h)
6. Polish + testing (1h)

**Total: 8 hours** (achievable in one day)

### Success Criteria

**Demo is successful if:**
- ✅ User can configure buyer + sellers
- ✅ Session initializes correctly
- ✅ Live negotiation streams in real-time
- ✅ Messages and offers update live
- ✅ Decision is shown clearly
- ✅ Summary displays correctly

**Bonus points:**
- 🎨 Clean, professional design
- ⚡ Smooth animations
- 📱 Mobile responsive
- 🎉 Celebration effects

---

**Document Status:** ✅ Ready for Implementation  
**Build Time Estimate:** 8 hours (1 developer) or 5 hours (2 developers)  
**Demo Time:** 5 minutes  

**Next Step:** Share with team, assign tasks, start building! 🚀

---

**Questions?**
- Clarify any screen layout
- Discuss component structure
- Review state management approach
- Plan team split

Good luck with the hackathon! 🎊
