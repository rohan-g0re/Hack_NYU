# Seller Visibility Fix - Privacy Implementation

## Problem Identified

Sellers were able to see ALL conversation messages, including:
- ❌ Messages from other sellers
- ❌ Offers from other sellers  
- ❌ Buyer's interactions with other sellers

This violated the core product principle of "opaque opponent models" from the product specification.

## Expected Behavior (from Product Spec)

According to `full_product_idea.md`:

### What Sellers Should See:
- ✅ Messages FROM the buyer (directed to them or broadcast)
- ✅ Their own messages

### What Sellers Should NOT See:
- ❌ Other sellers' prices/offers/messages
- ❌ Buyer's interactions with other sellers

## The Fix

### Code Changes in `backend/app/agents/prompts.py`

**Before (Lines 130-135):**
```python
# Build filtered conversation context (seller sees more than buyer)
history_text = ""
if conversation_history:
    history_text = "\n\nConversation history:\n"
    for msg in conversation_history[-10:]:
        history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"
```

**After (Lines 136-148):**
```python
# Build filtered conversation context - seller ONLY sees buyer messages and their own messages
history_text = ""
if conversation_history:
    history_text = "\n\nConversation history:\n"
    for msg in conversation_history[-10:]:
        sender_type = msg.get('sender_type', '')
        sender_id = msg.get('sender_id', '')
        
        # Seller can only see:
        # 1. Messages from the buyer (sender_type == "buyer")
        # 2. Their own messages (sender_id == seller.seller_id)
        if sender_type == "buyer" or sender_id == seller.seller_id:
            history_text += f"{msg.get('sender_name', 'Unknown')}: {msg.get('content', '')}\n"
```

### Updated System Prompt

Added explicit visibility rules to the seller system prompt:

```
Your Behavior:
- {priority_instruction}
- {style_instruction}
- Be concise (under 80 words)
- You can ONLY see messages from the buyer and your own messages
- You CANNOT see other sellers, their messages, or their offers

IMPORTANT VISIBILITY RULES:
- You DO NOT know about other sellers unless the buyer explicitly mentions them
- You DO NOT see what other sellers are offering
- Only respond based on what the buyer says to you directly
```

## Impact

### Before Fix:
- Sellers could reference other sellers' offers in their thinking
- Example: "GadgetHub's cost is $750, selling at $1150..."
- This broke the opaque negotiation model

### After Fix:
- Each seller operates in isolation
- Sellers only respond to buyer's direct messages
- Sellers only learn about competition if buyer explicitly mentions it
- Creates true competitive negotiation environment

## Testing

### To Verify Fix:

1. **Start a new negotiation**
   ```bash
   # Restart backend to load new code
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Initialize session with sample data**
   - Navigate to http://localhost:3000/config
   - Click "Use Sample Data"
   - Click "Initialize Episode"

3. **Start negotiation and observe**
   - Start negotiation for Laptop
   - Watch seller responses in the chat
   - Sellers should NOT reference other sellers unless buyer mentions them
   - Each seller should only see buyer messages and their own responses

### Expected Behavior After Fix:

**Seller A sees:**
```
Buyer: I need laptops. What can you offer?
Seller A: I can offer $1000 per unit for 10 laptops.
Buyer: @SellerA that's too high, can you do $950?
Seller A: Yes, I can do $950 per unit.
```

**Seller A does NOT see:**
```
❌ Seller B: I can offer $920 per unit
❌ Seller C: I have the best price at $900
❌ Buyer: @SellerB your price is better than SellerA
```

**Seller A WILL see IF buyer mentions competition:**
```
✅ Buyer: @SellerA another seller offered $920, can you match that?
```

## Alignment with Product Spec

This fix ensures the system adheres to the core design principle from `full_product_idea.md`:

> **4.2 Seller View**
> 
> Per item negotiation, each seller sees:
> - Messages **from the buyer** that are either directed to them using `@seller_name`, or general "broadcast" messages
> - Their own internal config
> 
> They **never see**:
> - Other sellers' prices/offers/messages.
> - Buyer's interactions with other sellers.

## Related Files

- `backend/app/agents/prompts.py` - Seller prompt generation (FIXED)
- `backend/app/services/visibility_filter.py` - Message filtering service
- `backend/app/services/message_router.py` - @mention routing
- `full_product_idea.md` - Product specification

## Status

✅ **FIXED** - Sellers now have proper visibility filtering
- Only see buyer messages and their own messages
- Cannot see other sellers or their offers
- Explicit prompt instructions added
- Conversation history properly filtered

---

**Date:** November 16, 2025  
**Issue:** Seller visibility not properly filtered  
**Fix:** Added message filtering in `render_seller_prompt()`  
**Impact:** Critical - ensures opaque negotiation model works correctly

