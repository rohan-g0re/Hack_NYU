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
│  - "Create New Session" button                                   │
│  - (Optional) "Load Previous Session" if time permits            │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 2: CONFIGURATION                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 1: Configure Buyer                                  │   │
│  │  - Name, Budget, Shopping List                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 2: Add Sellers (up to 10)                           │   │
│  │  - Name, Inventory, Profile                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Step 3: LLM Settings                                      │   │
│  │  - Provider (LM Studio / OpenRouter)                       │   │
│  │  - Model selection                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│  [Initialize Marketplace] button                                 │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 3: NEGOTIATION DASHBOARD                                 │
│  - List of items to negotiate                                    │
│  - For each item: Available sellers + [Start] button             │
│  - Budget tracker                                                │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 4: NEGOTIATION ROOM (Per Item)                           │
│  ┌────────────────┐  ┌──────────────────────────────────────┐   │
│  │  Current       │  │       Live Chat                       │   │
│  │  Offers        │  │  - Buyer messages                     │   │
│  │  Panel         │  │  - Seller responses (streaming)       │   │
│  │                │  │  - @mentions highlighted              │   │
│  └────────────────┘  └──────────────────────────────────────┘   │
│  - Progress: Round X/10                                          │
│  - [Force Decision] button (optional)                            │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  DECISION MODAL                                                  │
│  - Selected seller + final price                                 │
│  - Decision reason                                               │
│  - [Next Item] or [View Summary] button                          │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SCREEN 5: SESSION SUMMARY                                       │
│  - Total budget vs spent                                         │
│  - List of purchases                                             │
│  - Failed items                                                  │
│  - [Download Report] [Start New Session]                         │
└─────────────────────────────────────────────────────────────────┘
                         ▼
                      END
```

### 2.2 Key User Actions

| Action | Screen | Backend Call | User Feedback |
|--------|--------|--------------|---------------|
| Create session | Configuration | POST /simulation/initialize | Loading spinner → Redirect |
| Start negotiation | Dashboard | POST /negotiation/{id}/start | Transition to chat |
| Watch negotiation | Negotiation Room | GET /stream (SSE) | Live message updates |
| View decision | Negotiation Room | Auto from stream | Modal popup |
| View summary | Summary | GET /summary | Display results |

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

### 3.2 Screen 2: Configuration Wizard

**Purpose:** Collect all session configuration in one screen

**Layout:** Single-page form with collapsible sections

```
┌──────────────────────────────────────────────────────────────┐
│  Session Configuration                              [X Close] │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ 👤 Buyer Configuration                              ▼  ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Name: [________________________]                      ┃  │
│  ┃                                                         ┃  │
│  ┃  Budget Range:                                          ┃  │
│  ┃    Min: [$________]  Max: [$________]                  ┃  │
│  ┃                                                         ┃  │
│  ┃  Shopping List:                                         ┃  │
│  ┃  ┌──────────────────────────────────────────────┐      ┃  │
│  ┃  │ Item: [________] Quantity: [__] [X Remove]   │      ┃  │
│  ┃  │ Item: [________] Quantity: [__] [X Remove]   │      ┃  │
│  ┃  └──────────────────────────────────────────────┘      ┃  │
│  ┃  [+ Add Item]                                           ┃  │
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
│  ┃ 🤖 LLM Configuration                                 ▼  ┃  │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫  │
│  ┃  Provider: (•) LM Studio  ( ) OpenRouter               ┃  │
│  ┃  Model: [llama-3-8b-instruct        ▼]                 ┃  │
│  ┃  Temperature: [0.7____] Max Tokens: [500___]           ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│               [Initialize Marketplace] [Use Sample Data]      │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Key Features:**

**Buyer Section:**
- Text input for name
- Number inputs for budget (with validation: min < max)
- Dynamic list for shopping items
- Add/remove item buttons

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
- Radio buttons for provider selection
- Dropdown for model (populated from backend /llm/status)
- Sliders for temperature and max_tokens

**Helpers:**
- "Use Sample Data" button - loads pre-filled demo config
- Real-time validation feedback (red borders, error messages)
- Progress indicator: "X/10 sellers added"

**Design Notes:**
- Use accordion/collapse to reduce visual clutter
- Auto-expand next section when previous is valid
- Sticky "Initialize" button at bottom
- Consider multi-step wizard if single page feels overwhelming

---

### 3.3 Screen 3: Negotiation Dashboard

**Purpose:** Overview of all items and their negotiation status

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│  Session: #550e8400  |  Buyer: John Doe  |  Budget: $3000    │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Budget Overview                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Total: $3000 | Spent: $0 | Remaining: $3000            │  │
│  │ ████████████████████████████████████████░░░░░░  0%     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Items to Negotiate (2)                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  💻 Laptop (Need: 2 units)                             │  │
│  │  Available Sellers: TechStore, GadgetHub, CompuWorld   │  │
│  │  Price Range: $950 - $1200                             │  │
│  │                                                         │  │
│  │  Status: Pending              [Start Negotiation]      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  🖱️ Mouse (Need: 5 units)                              │  │
│  │  Available Sellers: None                                │  │
│  │                                                         │  │
│  │  Status: No sellers available                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│                                       [View All Sellers Info] │
└──────────────────────────────────────────────────────────────┘
```

**Elements:**

**Header Bar:**
- Session ID
- Buyer name
- Total budget
- (Optional) Time elapsed

**Budget Widget:**
- Visual progress bar
- Real-time updates as negotiations complete
- Color changes: green (plenty left) → yellow (low) → red (over budget)

**Item Cards:**
Each card shows:
- Item emoji/icon + name
- Quantity needed
- List of available sellers (clickable to see details)
- Price range (lowest least_price to highest selling_price)
- Status badge:
  - **Pending:** Gray, "Start Negotiation" button
  - **In Progress:** Blue, "Resume" button + live indicator
  - **Completed:** Green, "View Details" button
  - **No Sellers:** Red, disabled

**Interactions:**
- Click "Start Negotiation" → Transition to Negotiation Room
- Click seller name → Popup with seller details
- Click completed item → Show decision modal

**Design Notes:**
- Use cards for clear separation
- Status colors: Gray, Blue (pulsing), Green, Red
- Empty state for "no sellers" with helpful message

---

### 3.4 Screen 4: Negotiation Room

**Purpose:** Real-time chat interface for buyer-seller negotiation

**Layout:** Split-screen design

```
┌──────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard  |  Laptop Negotiation  |  Round: 3/10  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌──────────────────────────────────────┐ │
│  │              │   │  💬 Live Chat                        │ │
│  │  Current     │   ├──────────────────────────────────────┤ │
│  │  Offers      │   │                                      │ │
│  │              │   │  [Buyer] 10:30:01                    │ │
│  │  TechStore   │   │  Hello @TechStore and @GadgetHub!    │ │
│  │  💰 $1150    │   │  I'm looking for 2 laptops...        │ │
│  │  📦 2 units  │   │                                      │ │
│  │  🕐 10:31    │   │  [TechStore] 10:30:15                │ │
│  │  [Best]      │   │  Hi there! 😊 I can offer $1150...   │ │
│  │              │   │  💰 Offer: $1150 per unit            │ │
│  │  GadgetHub   │   │                                      │ │
│  │  💰 $1100    │   │  [GadgetHub] 10:30:18                │ │
│  │  📦 2 units  │   │  Best I can do is $1100. Final.      │ │
│  │  🕐 10:32    │   │  💰 Offer: $1100 per unit            │ │
│  │  [Lowest]    │   │                                      │ │
│  │              │   │  [Buyer] 10:30:45                    │ │
│  │  CompuWorld  │   │  Thanks! @GadgetHub that's close     │ │
│  │  💰 $1180    │   │  to my budget...                     │ │
│  │  📦 2 units  │   │                                      │ │
│  │  🕐 10:29    │   │  [typing...] ⏳                      │ │
│  │              │   │                                      │ │
│  └──────────────┘   │                                      │ │
│                     │                                      │ │
│  Budget Info        │                                      │ │
│  Max: $3000         │                                      │ │
│  Target: ~$1000     │                                      │ │
│                     └──────────────────────────────────────┘ │
│                                                               │
│                                      [Force Decision] [Stop]  │
└──────────────────────────────────────────────────────────────┘
```

**Left Panel: Current Offers**

**Structure:**
- Seller cards in a vertical list
- Auto-sorted by price (lowest to highest)
- Each card shows:
  - Seller name with style badge (😊 sweet / 😠 rude)
  - Current price (large, bold)
  - Quantity
  - Last updated time
  - Badge: "Best Price" or "Lowest" or "Highest"

**Visual Indicators:**
- Green highlight for lowest price
- Red highlight for highest price
- Pulsing animation when offer updates
- Strikethrough for old prices (show price history)

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

### 3.6 Screen 5: Session Summary

**Purpose:** Final overview of all purchases and budget usage

**Layout:**

```
┌──────────────────────────────────────────────────────────────┐
│  🎊 Shopping Complete!                                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 💰 Budget Summary                                        │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Initial Budget:     $3000                               │ │
│  │  Total Spent:        $2160                               │ │
│  │  Remaining:          $840                                │ │
│  │                                                           │ │
│  │  ████████████████████████░░░░░░░░░░  72% Utilized       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ✅ Successful Purchases (1)                              │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  💻 Laptop x2                                            │ │
│  │  ├─ Seller: GadgetHub                                    │ │
│  │  ├─ Price: $1080/unit                                    │ │
│  │  ├─ Total: $2160                                         │ │
│  │  ├─ Rounds: 5 (2m 25s)                                   │ │
│  │  └─ [View Chat Log]                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ❌ Failed Items (1)                                      │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  🖱️ Mouse x5                                             │ │
│  │  └─ Reason: No sellers have this item in inventory      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 📊 Negotiation Metrics                                   │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Average Rounds:           5                             │ │
│  │  Average Duration:         2m 25s                        │ │
│  │  Total Messages:           18                            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│         [Download PDF Report] [Start New Session] [Home]     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Sections:**

1. **Budget Summary Card:**
   - Visual progress bar
   - Clear before/after comparison
   - Utilization percentage

2. **Successful Purchases:**
   - Expandable cards for each item
   - Show key details (seller, price, stats)
   - Link to view full chat log

3. **Failed Items:**
   - Clear reasons for failure
   - Suggestions (e.g., "Try adding more sellers")

4. **Metrics:**
   - Aggregate stats across all negotiations
   - Helpful for analyzing agent behavior

**Actions:**
- Download PDF report (backend generates)
- Start new session (resets state)
- Go to home

**Design Notes:**
- Celebration theme (success colors, emojis)
- Clear success vs failure visual distinction
- Easy to scan structure

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
│   │   │   ├── BudgetRangeInput
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
│   │   ├── BudgetOverview
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
│       ├── BudgetSummaryCard
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
- Inputs: name (text), budget min/max (numbers)
- Shopping list: dynamic array of items
- Validation: budget max > min, items unique

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
  session: {
    id: null,
    status: 'idle', // idle | initializing | active | completed
    buyer: {
      id: null,
      name: '',
      budget: { min: 0, max: 0 },
      shoppingList: []
    },
    sellers: [],
    llmConfig: {},
    createdAt: null
  },

  negotiations: {
    'room_id_1': {
      roomId: 'room_id_1',
      itemName: 'Laptop',
      status: 'pending', // pending | active | completed
      currentRound: 0,
      maxRounds: 10,
      messages: [],
      offers: {},
      decision: null,
      eventSource: null // SSE connection
    }
  },

  ui: {
    activeNegotiationRoom: null,
    showDecisionModal: false,
    notifications: [],
    loading: {
      initializingSession: false,
      startingNegotiation: false
    },
    errors: {}
  }
}
```

### 5.2 State Updates

**Key Actions:**

1. **Initialize Session:**
   - User submits config → Set loading
   - API call → Store session data
   - Navigate to dashboard

2. **Start Negotiation:**
   - User clicks "Start" → Set loading
   - API call → Open SSE connection
   - Navigate to negotiation room

3. **Receive SSE Events:**
   - Event: buyer_message → Add to messages[]
   - Event: seller_response → Add to messages[], update offers{}
   - Event: negotiation_complete → Show decision modal

4. **Complete Negotiation:**
   - Close SSE connection
   - Update negotiation status
   - Navigate to next item or summary

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
Warning:     #F59E0B (Orange)    - Warnings, budget alerts
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
- **React 18+** with Vite (fast dev server)
- **React Router** for navigation
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

**Next.js Option:**
- Next.js 14 (App Router)
- Better for production, more complex setup
- Only if team is experienced

**Vue Option:**
- Vue 3 + Vite
- Composition API
- Similar component structure

**Svelte Option:**
- SvelteKit
- Less boilerplate
- Great for speed

**Recommendation:** Stick with React + Vite for maximum velocity

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

**Hour 1-3: Configuration Screen**
- [ ] Build BuyerConfigForm
- [ ] Build SellerCard component (repeatable)
- [ ] Implement form validation
- [ ] Connect to POST /simulation/initialize API
- [ ] Add "Use Sample Data" helper

**Hour 3-5: Dashboard & Navigation**
- [ ] Build DashboardPage layout
- [ ] Create ItemCard component
- [ ] Implement budget tracker
- [ ] Connect to GET /simulation/{id} API
- [ ] Add navigation to negotiation room

**Hour 5-7: Negotiation Room**
- [ ] Build split-screen layout (offers + chat)
- [ ] Implement OffersPanel with OfferCard
- [ ] Build ChatPanel with message components
- [ ] Connect SSE stream
- [ ] Handle real-time message updates
- [ ] Implement typing indicators

**Hour 7-8: Summary & Polish**
- [ ] Build SummaryPage layout
- [ ] Connect to GET /summary API
- [ ] Add Decision Modal
- [ ] Final styling pass
- [ ] Test end-to-end flow
- [ ] Fix critical bugs

---

### Priority Features (Must-Have)

**P0 (Critical Path):**
- ✅ Configuration form with validation
- ✅ Session initialization
- ✅ Dashboard with item cards
- ✅ Negotiation room with SSE streaming
- ✅ Chat message display (buyer + sellers)
- ✅ Offers panel with real-time updates
- ✅ Decision modal
- ✅ Summary screen

**P1 (Important):**
- Sample data loader
- Error handling (toasts)
- Loading states
- Basic animations (fade, slide)
- Budget tracker updates

**P2 (Nice-to-Have):**
- Advanced animations (confetti, pulse)
- Mobile responsive
- Download PDF report
- Dark mode
- Accessibility (ARIA labels)

**P3 (If Extra Time):**
- Previous session viewer
- Seller detail popups
- Chat log export
- Analytics dashboard

---

## 12. Testing Strategy (Minimal)

### 12.1 Manual Testing Checklist

**Configuration Flow:**
- [ ] Submit valid config → Success
- [ ] Submit invalid prices → Show errors
- [ ] Add/remove sellers → Updates correctly
- [ ] "Use Sample Data" → Populates form

**Dashboard:**
- [ ] Shows all items correctly
- [ ] "Start" button navigates to negotiation
- [ ] Budget displays correctly

**Negotiation Room:**
- [ ] SSE connects successfully
- [ ] Messages appear in real-time
- [ ] Offers update correctly
- [ ] @mentions highlighted
- [ ] Decision modal appears on completion

**Summary:**
- [ ] Shows all purchases
- [ ] Budget calculations correct
- [ ] Failed items displayed

### 12.2 Browser Testing

**Primary:** Chrome (latest)  
**Secondary:** Firefox, Safari (if time)  
**Skip:** IE, old browsers

### 12.3 Edge Cases

**Handle gracefully:**
- No internet connection
- LM Studio not running
- Session expires
- Zero sellers for all items
- Budget exceeded

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
   - Show budget tracker
   - Click "Start Negotiation" on Laptop

4. **Live Negotiation (2m):**
   - Watch buyer's opening message stream
   - Show @mentions highlighting
   - Watch sellers respond in real-time
   - Point out offers panel updating
   - Wait for decision

5. **Summary (1m):**
   - Show purchase details
   - Highlight budget utilization
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
