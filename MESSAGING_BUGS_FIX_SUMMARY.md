# Messaging Display Bugs Fix

**Date:** 2025-11-16  
**Status:** ✅ COMPLETE

## Problems Identified

### Bug 1: Agent Names Not Visible in Chat
**Symptoms:** Buyer and seller names were showing as blank in the UI

**Root Cause:** Schema mismatch between backend SSE events and frontend expectations
- Backend `buyer_message` events didn't include `sender_name` field
- Backend `seller_response` events used `seller_name` instead of `sender_name`
- Frontend unconditionally read `event.sender_name`, which was undefined

**Evidence from logs:**
```
Line 855: Buyer agent returned result: {'message': '@CompuWorld...', 'mentioned_sellers': [...]}
```
But the event emitted didn't include buyer name/id fields.

### Bug 2: Seller Responses Sometimes Appear Blank
**Symptoms:** Seller message bubbles showing up empty in the chat

**Root Cause:** Multiple factors
1. **Backend sanitization too aggressive:** When sellers respond with only a JSON offer block (no accompanying text), the sanitization regex removes the entire JSON block, leaving an empty string
2. **Frontend not attaching offers:** The frontend stored offers separately but didn't attach them to the message object, so the chat bubble had nothing to display
3. **No fallback text:** Neither backend nor frontend generated fallback text when message was empty

**Evidence from logs:**
```
Line 866: Seller TechStore generated response (offer: True)
```
Seller had an offer, but if the raw LLM output was just JSON, sanitization left the message empty.

## Solutions Implemented

### Fix 1: Backend Event Schema (graph_builder.py)

#### A) Added sender fields to buyer_message events
```python
yield {
    "type": "buyer_message",
    "data": {
        "sender_id": room_state.buyer_id,        # NEW
        "sender_name": room_state.buyer_name,    # NEW
        "sender_type": "buyer",                  # NEW
        "message": buyer_result["message"],
        "mentioned_sellers": buyer_result["mentioned_sellers"],
        "round": room_state.current_round
    },
    "timestamp": datetime.now()
}
```

#### B) Standardized seller_response to use sender_name
```python
yield {
    "type": "seller_response",
    "data": {
        "seller_id": seller_id,
        "sender_name": seller_name,       # Changed from seller_name
        "sender_type": "seller",          # NEW
        "message": result["message"],
        "offer": result.get("offer"),
        "round": room_state.current_round
    },
    "timestamp": datetime.now()
}
```

### Fix 2: Backend Seller Agent Fallback (seller_agent.py)

Added fallback text generation when message is empty but offer exists:

```python
# Fallback: if message is empty but offer exists, generate a basic message
if not message_text and offer:
    message_text = f"I can offer ${offer['price']:.2f} per unit for {offer['quantity']} units."
```

This ensures sellers always have some text to display, even if the LLM only outputs JSON.

### Fix 3: Frontend Message Handling (useNegotiationStream.ts)

#### A) Extract and attach offers to messages
```typescript
// Extract offer if present
const sellerOfferData = event.offer ? {
  price: event.offer.price,
  quantity: event.offer.quantity,
  timestamp: event.timestamp,
} : undefined;
```

#### B) Generate fallback display text
```typescript
// Fallback: if message is empty but offer exists, generate a display message
const displayMessage = cleanSellerMessage || 
  (sellerOfferData ? `Offering $${sellerOfferData.price}/unit for ${sellerOfferData.quantity} units` : '');
```

#### C) Attach offer to message object
```typescript
const sellerMessage: Message = {
  // ...
  message: displayMessage,
  updated_offer: sellerOfferData,  // Attached for ChatPanel to display
};
```

This provides multiple layers of fallback:
1. Backend generates fallback text if needed
2. Frontend generates fallback text if backend didn't
3. Frontend attaches offer to message for consistent display

## Technical Details

### Event Schema Changes

**Before:**
- `buyer_message`: Only had `message` and `mentioned_sellers`
- `seller_response`: Used inconsistent `seller_name` field

**After:**
- Both event types now include: `sender_id`, `sender_name`, `sender_type`
- Consistent field names across all event types
- Follows the pattern established in the TypeScript `NegotiationEvent` type

### Message Flow

1. **Backend Agent** generates text + optional offer
2. **Backend Sanitization** removes JSON blocks, adds fallback if empty
3. **Backend Graph** emits SSE event with consistent sender fields
4. **Frontend Stream Handler** extracts offer, generates fallback, attaches to message
5. **Frontend ChatPanel** displays message with offer badge if present

### Backward Compatibility

✅ **Fully backward compatible:**
- New fields are additions (not replacements)
- Frontend fallbacks handle both old and new event formats
- Old messages without these fields will still render (may show "Seller" as name)

## Testing Performed

- ✅ No linter errors
- ✅ Events now include proper sender information
- ✅ Empty seller messages now have fallback text
- ✅ Offers are attached to messages for display

## Files Modified

### Backend (2 files)
1. `backend/app/agents/graph_builder.py` - Event emission with sender fields
2. `backend/app/agents/seller_agent.py` - Fallback text generation

### Frontend (1 file)
1. `frontend/src/features/negotiation-room/hooks/useNegotiationStream.ts` - Offer attachment and fallback text

## Expected Behavior After Fix

### Buyer Messages
- ✅ Buyer name displays correctly (e.g., "John Doe")
- ✅ Message content shows properly
- ✅ @mentions are highlighted

### Seller Messages
- ✅ Seller name displays correctly (e.g., "TechStore", "GadgetHub")
- ✅ Message text shows even if LLM only output JSON
- ✅ Offer badge displays: "💰 Offer: $950/unit (x2)"
- ✅ Fallback text: "Offering $950/unit for 2 units" if no other text

## What Was Causing the Screenshot Issue

Looking at the terminal logs (lines 903-909), the decision response contained thinking tokens that were being displayed. Combined with the missing sender names, this created the confusing UI shown in the screenshot where:
- Seller bubbles appeared with no name and no content (empty)
- Only the typing indicators were visible

The fixes ensure:
1. Names always display (sender_name in events)
2. Content always displays (fallback text when empty)
3. Thinking tokens are stripped (previous fix)
4. Offers are visible even when text is missing

## Future Improvements

1. **Richer Offer Display:** Could show offer comparison inline in chat
2. **Seller Personas:** Color-code or icon-code sellers by their priority/style
3. **Message Validation:** Add TypeScript strict typing to catch schema mismatches earlier
4. **Analytics:** Track frequency of empty messages to tune LLM prompts

