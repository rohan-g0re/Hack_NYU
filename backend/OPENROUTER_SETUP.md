# OpenRouter Setup Guide

**WHAT:** Instructions for enabling and testing OpenRouter provider  
**WHY:** Enable cloud-based LLM inference when local models are insufficient  
**HOW:** Configure environment variables and test the provider

---

## Quick Start

### 1. Enable OpenRouter in `.env`

Add or update these settings in `Hack_NYU/.env`:

```ini
# Enable OpenRouter provider
LLM_ENABLE_OPENROUTER=true

# Your OpenRouter API key (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=your_api_key_here

# Default model (optional, defaults to google/gemini-2.5-flash-lite)
OPENROUTER_DEFAULT_MODEL=google/gemini-2.5-flash-lite

# Timeout in seconds (optional, defaults to 60)
OPENROUTER_TIMEOUT=60
```

### 2. Test OpenRouter

```powershell
cd Hack_NYU\backend
python test_openrouter_inference.py
```

---

## Configuration Details

### Required Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_ENABLE_OPENROUTER` | Enable/disable OpenRouter | `true` or `false` |
| `OPENROUTER_API_KEY` | Your API key from OpenRouter | `sk-or-v1-...` |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_DEFAULT_MODEL` | Model to use | `google/gemini-2.5-flash-lite` |
| `OPENROUTER_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` |
| `OPENROUTER_TIMEOUT` | Request timeout (seconds) | `60` |

---

## Testing

### Test OpenRouter Directly

```powershell
python test_openrouter_inference.py
```

This will test:
- ✅ Ping/Health check
- ✅ Non-streaming generation
- ✅ Streaming generation

### Test Both Providers

```powershell
python test_both_providers.py
```

This tests both LM Studio and OpenRouter (if enabled).

### Switch Provider

To use OpenRouter as the default provider:

```ini
# In Hack_NYU/.env
LLM_PROVIDER=openrouter
LLM_ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=your_key_here
```

---

## Available Models

OpenRouter supports many models. Some popular options:

- `google/gemini-2.5-flash-lite` (fast, cost-effective)
- `openai/gpt-4o-mini` (OpenAI compatible)
- `anthropic/claude-3-haiku` (Anthropic)
- `meta-llama/llama-3.1-8b-instruct` (Open source)

See all models at: https://openrouter.ai/models

---

## Troubleshooting

### "OpenRouter is disabled"

**Problem:** `LLM_ENABLE_OPENROUTER` is not set to `true`

**Solution:**
```ini
LLM_ENABLE_OPENROUTER=true
```

### "OPENROUTER_API_KEY is not set"

**Problem:** API key missing or incorrect

**Solution:**
1. Get your API key from https://openrouter.ai/keys
2. Add to `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`

### "Authentication failed"

**Problem:** Invalid API key

**Solution:**
1. Verify API key at https://openrouter.ai/keys
2. Check for typos or extra spaces
3. Ensure key starts with `sk-or-v1-`

### "Connection timeout"

**Problem:** Network issues or API down

**Solution:**
1. Check internet connection
2. Verify OpenRouter status: https://status.openrouter.ai
3. Increase timeout: `OPENROUTER_TIMEOUT=120`

### "Model not found"

**Problem:** Model name incorrect

**Solution:**
1. Check model name at https://openrouter.ai/models
2. Use exact model ID (e.g., `google/gemini-2.5-flash-lite`)
3. Verify model is available and not deprecated

---

## API Reference

OpenRouter uses OpenAI-compatible API endpoints:

- **Models:** `GET /models` - List available models
- **Chat:** `POST /chat/completions` - Generate responses
- **Streaming:** `POST /chat/completions` (with `stream: true`)

See full documentation: https://openrouter.ai/docs

---

## Cost Considerations

OpenRouter charges per token. Monitor usage at:
https://openrouter.ai/activity

**Tips:**
- Use `max_tokens` to limit response length
- Choose cost-effective models (e.g., `gemini-2.5-flash-lite`)
- Monitor API usage regularly

---

## Example Usage

### In Code

```python
from app.llm.provider_factory import get_provider

# Get provider (will use OpenRouter if LLM_PROVIDER=openrouter)
provider = get_provider()

# Generate response
messages = [{"role": "user", "content": "Hello!"}]
result = await provider.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=100
)

print(result.text)
```

---

## Status

**Implementation:** ✅ Complete  
**Features:**
- ✅ Ping/Health check
- ✅ Non-streaming generation
- ✅ Streaming generation
- ✅ Error handling
- ✅ Retry logic
- ✅ Authentication

**Ready for:** Production use

---

**Last Updated:** November 15, 2025

