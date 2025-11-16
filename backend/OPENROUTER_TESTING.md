# OpenRouter Testing Guide

## Quick Setup

### 1. Enable OpenRouter in `.env`

Add or update these variables in your `.env` file (in `Hack_NYU/` or `Hack_NYU/backend/`):

```bash
LLM_PROVIDER=openrouter
LLM_ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get your API key from: https://openrouter.ai/keys

### 2. Configure Test Parameters (Optional)

You can adjust negotiation behavior in `.env`:

```bash
# Negotiation settings
MAX_NEGOTIATION_ROUNDS=5          # Max rounds per negotiation
MIN_NEGOTIATION_ROUNDS=2          # Minimum rounds before buyer can decide
PARALLEL_SELLER_LIMIT=3           # Max concurrent seller responses

# LLM settings
LLM_DEFAULT_TEMPERATURE=0.0       # Lower = more deterministic
LLM_DEFAULT_MAX_TOKENS=256        # Max tokens per generation
```

### 3. Run Tests

```bash
cd Hack_NYU/backend
python test_openrouter_negotiation.py
```

## What Changed (Option B Implementation)

### Buyer Agent Decision Making
- **Before**: Simple heuristic (lowest price wins immediately)
- **Now**: Buyer agent evaluates offers and decides when to accept
- Buyer sees all valid offers and makes decision based on:
  - Price
  - Seller responsiveness
  - Conversation quality
  - Number of rounds negotiated

### Improved Offer Parsing
- **Before**: Only JSON format accepted
- **Now**: Multiple parsing strategies:
  1. JSON block parsing (preferred)
  2. Regex fallback for price mentions (`$XX.XX`, `XX.XX dollars`, etc.)
  3. Regex fallback for quantity mentions

### Minimum Rounds Enforcement
- Buyer cannot accept offers before `MIN_NEGOTIATION_ROUNDS` (default: 2)
- Ensures meaningful negotiation even with good early offers

## Test Scenarios

### Scenario 1: Competitive Pricing (2 Sellers)
- **Buyer**: Alice, budget $800-$1200
- **Sellers**: TechStore (rude, maximize profit) vs BudgetElectronics (sweet, customer retention)
- **Goal**: Test buyer decision-making with competing offers

### Scenario 2: Single Seller Negotiation
- **Buyer**: Bob, budget $400-$600
- **Seller**: PhoneStore (sweet, maximize profit)
- **Goal**: Test negotiation depth and buyer persistence

### Scenario 3: Multiple Sellers Comparison
- **Buyer**: Charlie, needs 2 tablets, budget $200-$400
- **Sellers**: 3 sellers with different pricing and styles
- **Goal**: Test buyer's ability to compare and select best offer

## Expected Behavior

### Decision Logic
1. **Round < MIN_ROUNDS**: Always continue (no decision check)
2. **Round >= MIN_ROUNDS**: Buyer agent evaluates offers
3. **Buyer Response**:
   - `"ACCEPT [SellerName]"` → Negotiation completes
   - `"CONTINUE"` or `"KEEP NEGOTIATING"` → Continue to next round
   - Unclear response → Continue (conservative)

### Offer Parsing
- Sellers can make offers in multiple formats:
  - JSON: `{"offer": {"price": 950, "quantity": 1}}`
  - Natural: "I can offer $950 per unit"
  - Natural: "Price: $950, Quantity: 1"

### Stopping Conditions
1. **Buyer accepts offer** → `negotiation_complete` with selected seller
2. **Max rounds reached** → `negotiation_complete` with no selection
3. **No responding sellers** → Early termination

## Debugging

### Check Logs
Logs are written to `backend/data/logs/app.log`. Look for:
- `Buyer decision response: ...` - Shows buyer's decision reasoning
- `Buyer decided to accept offer from ...` - Successful acceptance
- `Buyer decided to continue negotiating` - Decision to continue

### Common Issues

**Issue**: Provider not available
- **Fix**: Check `OPENROUTER_API_KEY` is set correctly
- **Fix**: Verify `LLM_ENABLE_OPENROUTER=true`

**Issue**: No offers being parsed
- **Fix**: Check seller prompts include offer format instructions
- **Fix**: Verify regex patterns match seller responses

**Issue**: Buyer never decides
- **Fix**: Check `MIN_NEGOTIATION_ROUNDS` isn't too high
- **Fix**: Verify buyer decision prompt is clear
- **Fix**: Check decision parsing logic for "ACCEPT" keyword

## Performance Notes

- Each negotiation round makes 1 buyer call + N seller calls (parallel)
- Decision check adds 1 additional LLM call per round (after MIN_ROUNDS)
- Typical negotiation: 3-5 rounds = ~10-15 LLM calls total
- With OpenRouter, expect ~1-2 seconds per call = ~10-30 seconds per negotiation

## Next Steps

1. Run test suite: `python test_openrouter_negotiation.py`
2. Observe buyer decision-making patterns
3. Adjust prompts if buyer is too aggressive/conservative
4. Tune `MIN_NEGOTIATION_ROUNDS` based on desired negotiation depth
5. Test with different seller profiles and priorities

