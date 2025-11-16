# Thinking Tokens Management Fix

**Date:** 2025-11-16  
**Status:** ✅ COMPLETE (Updated 2025-11-16)

## Problem

The application was displaying raw thinking/reasoning tokens from LLM models (like DeepSeek-R1) that emit internal reasoning in `<think>...</think>` blocks. These tokens were appearing in the UI chat interface, cluttering the user experience.

Additionally, when using LM Studio for inference, aggressive backend filtering was truncating responses, preventing full model outputs from reaching the frontend.

## Solution Overview (Updated)

**CHANGED APPROACH:** Removed thinking token filtering entirely to show raw model outputs:
- **Frontend**: ~~Strip thinking tokens on message receipt~~ **NOW DISPLAYS RAW MESSAGES INCLUDING THINKING TOKENS**
- **Backend**: ~~Sanitize agent outputs and filter streaming responses~~ **NOW EMITS RAW, UNFILTERED TOKENS**
- **Prompts**: Add explicit instructions to discourage thinking token emission (unchanged, but may be ignored for debugging)

## Changes Made

### Frontend Changes (Updated)

#### 1. `frontend/src/utils/formatters.ts` (UNCHANGED)
- Added `escapeHtml()` function to prevent XSS by escaping HTML special characters
- Added `stripThinking()` function (kept for backward compatibility but no longer used)
- Updated `highlightMentions()` to safely escape HTML before highlighting mentions

#### 2. `frontend/src/features/negotiation-room/hooks/useNegotiationStream.ts` (UPDATED)
- ~~Import `stripThinking` utility~~ **REMOVED IMPORT**
- ~~Apply thinking token stripping to buyer messages~~ **NOW DISPLAYS RAW BUYER MESSAGES**
- ~~Apply thinking token stripping to seller messages~~ **NOW DISPLAYS RAW SELLER MESSAGES**
- Raw messages with thinking tokens are now stored and displayed in the negotiation state

#### 3. `frontend/src/features/negotiation-room/components/ChatPanel.tsx` (UNCHANGED)
- Updated `SellerMessage` component to use safe `highlightMentions()` with HTML escaping
- Now uses `dangerouslySetInnerHTML` with sanitized content for consistent mention highlighting

### Backend Changes (Updated)

#### 4. `backend/app/utils/text.py` (DEPRECATED)
- ~~Created centralized text utility module~~ **NOW DEPRECATED**
- ~~Implemented `strip_thinking()` function~~ **Function now returns text unchanged with deprecation warning**
- Kept for backward compatibility but no longer performs filtering
- Backend thinking token stripping has been moved to frontend

#### 5. `backend/app/agents/buyer_agent.py` (UPDATED)
- ~~Import `strip_thinking` utility~~ **REMOVED IMPORT**
- ~~Updated `_sanitize_message()` to call `strip_thinking()`~~ **REMOVED CALL**
- Updated docstring to reflect that reasoning tokens are now handled by frontend
- Still performs markdown/JSON cleanup but no longer strips thinking tokens

#### 6. `backend/app/agents/seller_agent.py` (UPDATED)
- ~~Import `strip_thinking` utility~~ **REMOVED IMPORT**
- ~~Updated `_sanitize_message()` to call `strip_thinking()`~~ **REMOVED CALL**
- Updated docstring to reflect that reasoning tokens are now handled by frontend
- Still performs JSON offer cleanup but no longer strips thinking tokens

#### 7. `backend/app/llm/lm_studio.py` (UPDATED)
- ~~Enhanced `stream()` method with stateful thinking token filtering~~ **REMOVED FILTERING**
- ~~Tracks `in_think` state across streaming chunks~~ **REMOVED STATE TRACKING**
- **NOW EMITS RAW, UNFILTERED TOKENS** to allow full responses to reach frontend
- Still ignores structured reasoning deltas (future-proofing)
- Updated docstring to reflect unfiltered streaming

#### 8. `backend/app/llm/openrouter.py` (UPDATED)
- ~~Enhanced `stream()` method with thinking token filtering~~ **REMOVED FILTERING**
- **NOW EMITS RAW, UNFILTERED TOKENS** for consistency with LM Studio
- Updated docstring to reflect unfiltered streaming
- Future-proof for reasoning-capable models via OpenRouter

#### 9. `backend/app/agents/prompts.py`
- Updated `render_buyer_prompt()` system prompt with explicit instructions:
  - "Do NOT reveal your chain-of-thought or internal reasoning"
  - "NEVER output <think>...</think> tags or similar reasoning blocks"
  - "Respond ONLY with your final message to the sellers"
- Updated `render_seller_prompt()` system prompt with same instructions
- Updated `render_decision_prompt()` with instructions to only output decision format

## Technical Details

### Filtering Strategy (Updated)

**Frontend (Post-Processing) - CHANGED:**
- ~~Strips thinking content after receiving complete messages~~ **REMOVED - now displays raw messages**
- ~~Regex-based removal of various thinking formats~~ **REMOVED - thinking tokens now visible in UI**
- Safe HTML escaping before display via `highlightMentions()` (unchanged for security)

**Backend (Real-Time & Pre-Processing) - CHANGED:**
- ~~Agent sanitizers strip thinking from generated text~~ **REMOVED - agents no longer strip thinking**
- ~~Streaming providers filter thinking tokens in real-time~~ **REMOVED - providers emit raw tokens**
- ~~Stateful parsing handles tags split across chunks~~ **REMOVED - no more chunk-level filtering**
- Prompt engineering discourages emission at source (unchanged but may be ignored for debugging)

**Key Change:** Complete elimination of thinking token filtering throughout the entire stack. Raw model outputs including `<think>` blocks are now visible in the UI for debugging and transparency.

### Edge Cases Handled (No Longer Applicable)

**Previous frontend `stripThinking()` function handled:**
1. **Dangling Tags**: `<think>` without closing `</think>`
2. **Stray Closing Tags**: `</think>` without opening
3. **Case Insensitive**: Handles `<THINK>`, `<Think>`, etc.
4. **Multiple Blocks**: Removes all thinking blocks in a response
5. **Reasoning Prefixes**: Removes lines starting with "Thought:", "Reasoning:", etc.

**Note:** All thinking token filtering has been removed. Raw model outputs including all thinking patterns are now displayed in the UI as-is for maximum transparency and debugging capability.

### Security Improvements

- Frontend now properly escapes HTML before using `dangerouslySetInnerHTML`
- Prevents XSS attacks from malicious model outputs
- Maintains mention highlighting functionality with safe rendering

## Testing Recommendations

### Frontend Tests
1. Send messages with `<think>test</think>` blocks - verify they're filtered
2. Send messages with HTML like `<script>alert('xss')</script>` - verify it's escaped
3. Verify @mention highlighting still works correctly
4. Test with split thinking tags across multiple stream chunks

### Backend Tests (Updated)
1. ~~Test buyer agent output with thinking tokens - verify sanitization~~ **Test that agents preserve thinking tokens**
2. ~~Test seller agent output with thinking tokens - verify sanitization~~ **Test that agents preserve thinking tokens**
3. ~~Test streaming with models that emit `<think>` tags - verify filtering~~ **Test that streaming preserves all tokens**
4. ~~Test with dangling/stray tags - verify robust handling~~ **Test that raw tokens reach frontend**
5. Verify decision prompts don't leak reasoning (unchanged - handled by prompts)

### Integration Tests (Updated)
1. Run full negotiation with reasoning-capable model (e.g., DeepSeek-R1)
2. **Verify complete responses now reach frontend (including thinking tokens)**
3. **Verify thinking tokens are now visible in the UI chat display**
4. Verify offers are still parsed correctly from raw responses
5. Verify mention highlighting works (with HTML escaping for security)
6. Test with multiple rounds and sellers
7. **Test that LM Studio streaming no longer truncates responses**
8. **Verify raw thinking content helps with debugging agent behavior**

## Future Improvements

1. **Structured Reasoning Support**: If OpenAI or other providers add dedicated reasoning fields, the code is already prepared to ignore `delta.reasoning`
2. **Configurable Filtering**: Could add settings to optionally show reasoning for debugging
3. **Analytics**: Track frequency of thinking token filtering for model behavior insights
4. **Additional Patterns**: Monitor for new reasoning formats from emerging models

## Files Modified (Updated)

### Frontend (3 files) - UNCHANGED
- `frontend/src/utils/formatters.ts`
- `frontend/src/features/negotiation-room/hooks/useNegotiationStream.ts`
- `frontend/src/features/negotiation-room/components/ChatPanel.tsx`

### Backend (6 files + 1 deprecated)
- `backend/app/utils/text.py` (**DEPRECATED** - function now returns text unchanged)
- `backend/app/agents/buyer_agent.py` (**UPDATED** - removed strip_thinking import/call)
- `backend/app/agents/seller_agent.py` (**UPDATED** - removed strip_thinking import/call)
- `backend/app/agents/prompts.py` (unchanged)
- `backend/app/llm/lm_studio.py` (**UPDATED** - removed chunk-level filtering)
- `backend/app/llm/openrouter.py` (**UPDATED** - removed chunk-level filtering)
- `THINKING_TOKENS_FIX_SUMMARY.md` (**UPDATED** - reflects new frontend-only approach)

## Backward Compatibility (Updated)

✅ All changes remain backward compatible:
- Existing messages without thinking tokens are unaffected
- Non-reasoning models continue to work normally  
- Streaming and non-streaming modes both supported
- No breaking changes to API contracts
- **UI now shows raw model outputs for maximum transparency**
- **Backend preserves complete model responses for debugging**

⚠️ **Note:** 
- Database-stored conversation transcripts now include raw thinking tokens (better debugging, slightly more storage)
- **UI will now display thinking tokens to users** - this provides full transparency into model reasoning but may be verbose
- Consider this a "debug mode" where you can see exactly what the AI models are thinking during negotiations

