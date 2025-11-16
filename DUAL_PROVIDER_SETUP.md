# Dual LLM Provider Setup Guide

**Last Updated:** 2025-11-16  
**Purpose:** Enable both LM Studio (local) and OpenRouter (cloud) inference in the Multi-Agent Marketplace

---

## Overview

The system now supports **two LLM providers** that can be switched dynamically:

- **🖥️ LM Studio:** Local inference on your machine (privacy-first, no API costs)
- **☁️ OpenRouter:** Cloud inference (convenient, supports many models, pay-per-use)

You can **switch between providers per session** via the frontend UI without restarting the backend!

---

## Quick Start

### 1. Backend Setup

#### Step 1: Copy Environment Template

```bash
cd Hack_NYU/backend
cp env.template .env
```

#### Step 2: Configure Both Providers in `.env`

Edit `.env` and configure:

```bash
# Default provider (can be overridden via frontend)
LLM_PROVIDER=lm_studio

# LM Studio Configuration
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_DEFAULT_MODEL=qwen/qwen3-1.7b
LM_STUDIO_TIMEOUT=30

# OpenRouter Configuration
LLM_ENABLE_OPENROUTER=true
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
```

**Important:** Replace `sk-or-v1-your-actual-key-here` with your real API key from [https://openrouter.ai/keys](https://openrouter.ai/keys)

#### Step 3: Run Database Migration (if upgrading)

```bash
python migrate_add_provider.py
```

This adds the `llm_provider` column to existing databases.

#### Step 4: Start the Backend

```bash
# Activate conda environment
conda activate hackathon

# Start server
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 2. LM Studio Setup (Optional but Recommended)

**If you want to use local inference:**

1. **Download LM Studio:** [https://lmstudio.ai/](https://lmstudio.ai/)

2. **Install and launch** the application

3. **Download a model:**
   - Go to the "Discover" tab
   - Search for `qwen3-1.7b` (small, fast) or `llama-3-8b-instruct` (larger, better quality)
   - Click "Download"

4. **Load the model:**
   - Go to "Local Server" tab
   - Select your downloaded model
   - Click "Start Server"
   - Verify it's running on `http://localhost:1234`

5. **Update `.env`** to match your loaded model:
   ```bash
   LM_STUDIO_DEFAULT_MODEL=qwen/qwen3-1.7b
   ```

---

### 3. OpenRouter Setup (Optional)

**If you want to use cloud inference:**

1. **Get API Key:**
   - Visit [https://openrouter.ai/keys](https://openrouter.ai/keys)
   - Sign up / Log in
   - Create a new API key
   - Copy the key (starts with `sk-or-v1-...`)

2. **Add to `.env`:**
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-copied-key-here
   LLM_ENABLE_OPENROUTER=true
   ```

3. **Choose a model** (free models available):
   ```bash
   OPENROUTER_DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
   ```

---

### 4. Frontend Setup

No additional configuration needed! The frontend automatically:
- Detects available providers from backend
- Shows a provider selector in LLM Configuration
- Switches models list based on selected provider

---

## Using the System

### Selecting Provider in Frontend

1. Navigate to the **Configuration Page**
2. Find the **LLM Configuration** section
3. Click on **LLM Provider** dropdown
4. Choose:
   - **🖥️ LM Studio (Local)** - Uses your local LM Studio server
   - **☁️ OpenRouter (Cloud)** - Uses OpenRouter API

5. Select a model from the updated model list
6. Configure temperature and max_tokens as needed
7. Click **Initialize Session**

### Provider Persistence

Each session remembers which provider was used:
- Sessions created with LM Studio will always use LM Studio
- Sessions created with OpenRouter will always use OpenRouter
- You can create different sessions with different providers simultaneously

---

## Testing

### Test LM Studio Inference

1. **Ensure LM Studio is running** on port 1234
2. **Check health:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

3. **Check LLM status:**
   ```bash
   curl http://localhost:8000/api/v1/llm/status
   ```

4. **Create a test session** with LM Studio:
   - Use frontend to select "LM Studio (Local)"
   - Initialize session
   - Start negotiation
   - Monitor console for inference logs

### Test OpenRouter Inference

1. **Verify API key is set** in `.env`
2. **Create a test session** with OpenRouter:
   - Use frontend to select "OpenRouter (Cloud)"
   - Initialize session
   - Start negotiation
   - Monitor console for API calls

### Test Switching Between Providers

1. **Create Session 1** with LM Studio
2. **Create Session 2** with OpenRouter
3. **Start negotiations** in both rooms
4. **Verify** each uses its configured provider

---

## Troubleshooting

### LM Studio Not Available

**Error:** `LM Studio is not reachable`

**Solutions:**
- Verify LM Studio app is running
- Check local server is started (green "Running" status)
- Confirm port is 1234 (default)
- Try accessing `http://localhost:1234/v1/models` in browser

### OpenRouter Authentication Error

**Error:** `401 Unauthorized` or `Invalid API key`

**Solutions:**
- Verify API key in `.env` starts with `sk-or-v1-`
- Check for extra spaces or newlines in `.env`
- Ensure `LLM_ENABLE_OPENROUTER=true`
- Regenerate key at [https://openrouter.ai/keys](https://openrouter.ai/keys)

### Provider Not Switching

**Issue:** Frontend shows same models after changing provider

**Solutions:**
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Clear browser cache
- Check browser console for errors
- Verify backend is running

### Model Not Found

**Error:** Model not available or not loaded

**Solutions:**
- **LM Studio:** Ensure model is loaded and server is running
- **OpenRouter:** Check model ID is correct (see [https://openrouter.ai/models](https://openrouter.ai/models))
- Update `LM_STUDIO_DEFAULT_MODEL` or `OPENROUTER_DEFAULT_MODEL` in `.env`

---

## Model Recommendations

### LM Studio (Local)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `qwen/qwen3-1.7b` | 1.7B | ⚡ Very Fast | Good | Testing, quick iterations |
| `llama-3-8b-instruct` | 8B | Fast | Excellent | Production, balanced |
| `mistral-7b-instruct` | 7B | Fast | Very Good | General purpose |
| `codellama-7b-instruct` | 7B | Fast | Good | Code-heavy negotiations |

### OpenRouter (Cloud)

| Model | Cost | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `google/gemini-2.0-flash-exp:free` | Free | ⚡ Very Fast | Excellent | Production, high quality |
| `meta-llama/llama-3.2-3b-instruct:free` | Free | Very Fast | Good | Testing, fast responses |
| `meta-llama/llama-3.1-8b-instruct:free` | Free | Fast | Excellent | Balanced quality/speed |
| `mistralai/mistral-7b-instruct:free` | Free | Fast | Very Good | General purpose |

---

## Architecture Changes

### Backend Changes

1. **Database Schema:**
   - Added `llm_provider` column to `sessions` table
   - Default value: `lm_studio`

2. **API Schema:**
   - `LLMConfig` now includes optional `provider` field
   - Provider can be specified per session in `POST /api/v1/simulation/initialize`

3. **Provider Factory:**
   - Updated to support dynamic provider selection
   - Caches multiple provider instances
   - `get_provider(provider_name)` accepts optional provider parameter

4. **Session Management:**
   - Stores provider per session
   - Room state includes `llm_provider` field
   - Negotiation graph uses session-specific provider

### Frontend Changes

1. **Types:**
   - `LLMConfig` includes `provider?: 'lm_studio' | 'openrouter'`

2. **Components:**
   - `LLMConfigForm` has provider selector dropdown
   - Dynamic model list based on selected provider
   - Context-aware help text (LM Studio vs OpenRouter)

3. **Constants:**
   - `DEFAULT_PROVIDER` changed to `lm_studio` (local-first)
   - Separate model lists for each provider

---

## Environment Variables Reference

### Core Settings

```bash
# Provider selection (default, can be overridden per session)
LLM_PROVIDER=lm_studio  # or openrouter

# Database
DATABASE_URL=sqlite:///./data/marketplace.db
```

### LM Studio Settings

```bash
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_DEFAULT_MODEL=qwen/qwen3-1.7b
LM_STUDIO_TIMEOUT=30  # seconds
```

### OpenRouter Settings

```bash
LLM_ENABLE_OPENROUTER=true  # Must be true to use OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=google/gemini-2.0-flash-exp:free
```

### LLM Request Settings (Both Providers)

```bash
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2  # seconds
LLM_DEFAULT_TEMPERATURE=0.0
LLM_DEFAULT_MAX_TOKENS=256
```

---

## API Documentation Updates

### Initialize Session Request

Now accepts optional `provider` in `llm_config`:

```json
{
  "buyer": { ... },
  "sellers": [ ... ],
  "llm_config": {
    "model": "qwen/qwen3-1.7b",
    "temperature": 0.7,
    "max_tokens": 500,
    "provider": "lm_studio"  // Optional: "lm_studio" or "openrouter"
  }
}
```

If `provider` is omitted, uses `LLM_PROVIDER` from `.env`.

### Health Check Response

```json
{
  "status": "healthy",
  "components": {
    "llm": {
      "available": true,
      "provider": "lm_studio"  // Current default provider
    },
    "database": {
      "available": true
    }
  }
}
```

---

## Cost Considerations

### LM Studio (Local)

- **Cost:** FREE (after hardware investment)
- **Requirements:** GPU recommended (8GB+ VRAM for 7B models)
- **Pros:** Private, no per-request cost, offline capable
- **Cons:** Hardware requirements, slower on CPU

### OpenRouter (Cloud)

- **Free Tier:** Available for many models (Gemini, Llama, Mistral)
- **Paid Models:** Typically $0.0001 - $0.01 per 1K tokens
- **Pros:** No hardware needed, fast, scalable
- **Cons:** Requires internet, data sent to third party

**Recommendation:** Use LM Studio for development/testing, OpenRouter for production or when local hardware is limited.

---

## Migration Guide (Existing Installations)

### If You Have an Existing Installation:

1. **Pull latest code**
2. **Run migration script:**
   ```bash
   cd Hack_NYU/backend
   python migrate_add_provider.py
   ```
3. **Update `.env`** with OpenRouter settings (optional)
4. **Restart backend**
5. **Refresh frontend** (hard reload)

### If Starting Fresh:

- No migration needed
- Database will be created with new schema automatically
- Follow Quick Start guide above

---

## Support

For issues or questions:
1. Check this guide
2. Check `API_DOCUMENTATION.md` for API details
3. Check `ENVIRONMENT_SETUP.md` for conda environment
4. Check backend logs: `backend/data/logs/app.log`

---

**Document Version:** 1.0.0  
**Compatibility:** Backend v0.1.0+, Frontend (Next.js)  
**Status:** Production Ready ✅

