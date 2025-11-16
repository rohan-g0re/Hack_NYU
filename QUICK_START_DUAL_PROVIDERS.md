# Quick Start: Dual LLM Providers

**TL;DR:** You can now use **both LM Studio (local)** and **OpenRouter (cloud)** and switch between them in the frontend! 🎉

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Backend Configuration

```bash
cd Hack_NYU/backend

# Copy environment template
cp env.template .env

# Edit .env and add your OpenRouter API key (optional)
# OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Run migration (if you have existing database)
python migrate_add_provider.py

# Start backend
python -m app.main
```

### Step 2: Choose Your Provider

**Option A: LM Studio (Local - FREE)**
1. Download LM Studio from https://lmstudio.ai/
2. Load a model (e.g., `qwen3-1.7b`)
3. Start local server (port 1234)
4. Select "🖥️ LM Studio" in frontend

**Option B: OpenRouter (Cloud - FREE/Paid)**
1. Get API key from https://openrouter.ai/keys
2. Add to `backend/.env`: `OPENROUTER_API_KEY=sk-or-v1-...`
3. Select "☁️ OpenRouter" in frontend
4. Many free models available!

---

## 🎯 How to Use

### In the Frontend:

1. Go to **Configuration Page**
2. Find **LLM Configuration** section
3. Select **LLM Provider** dropdown:
   - **🖥️ LM Studio (Local)** ← Your machine, privacy-first
   - **☁️ OpenRouter (Cloud)** ← Cloud, easy setup
4. Pick a model from the updated list
5. Initialize Session & Start Negotiation!

### The UI Will Show:

```
┌─────────────────────────────────────────┐
│ LLM Configuration                    ▲│
├─────────────────────────────────────────┤
│ LLM Provider                           │
│ ┌─────────────────────────────────────┐ │
│ │ 🖥️ LM Studio (Local)           ▼│ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Model                                   │
│ ┌─────────────────────────────────────┐ │
│ │ Qwen 3 1.7B (Fast, Lightweight) ▼│ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Temperature: 0.7  Max Tokens: 500      │
│                                         │
│ ℹ️ Make sure LM Studio is running on   │
│   http://localhost:1234                │
└─────────────────────────────────────────┘
```

---

## 📋 Quick Comparison

| Feature | LM Studio | OpenRouter |
|---------|-----------|------------|
| **Setup** | Download app, load model | Get API key |
| **Cost** | FREE (after hardware) | FREE/Paid models |
| **Privacy** | ✅ 100% local | ❌ Cloud-based |
| **Speed** | Depends on hardware | ⚡ Very fast |
| **Models** | Must download | 100+ available |
| **Offline** | ✅ Works offline | ❌ Needs internet |

---

## 🎨 What Changed?

### Backend:
- ✅ Added `llm_provider` column to database
- ✅ API now accepts `provider` in llm_config
- ✅ Each session remembers its provider
- ✅ Provider factory supports both

### Frontend:
- ✅ Provider selector dropdown
- ✅ Dynamic model lists per provider
- ✅ Context-aware help text
- ✅ Auto-switch models when changing provider

---

## 🧪 Test It!

### Test LM Studio:
```bash
# 1. Start LM Studio with a model loaded
# 2. Create session with LM Studio provider
# 3. Watch console: "LM Studio generate success..."
```

### Test OpenRouter:
```bash
# 1. Add API key to .env
# 2. Create session with OpenRouter provider
# 3. Watch console: "OpenRouter API call..."
```

### Test Both Simultaneously:
```bash
# 1. Create Session A with LM Studio
# 2. Create Session B with OpenRouter
# 3. Run negotiations in both
# 4. Each uses its configured provider!
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| LM Studio not available | Ensure server running on port 1234 |
| OpenRouter 401 error | Check API key in `.env` |
| Models not changing | Hard refresh browser (Ctrl+Shift+R) |
| Provider not persisting | Check backend logs for errors |

---

## 📚 More Info

- **Full Setup:** See `DUAL_PROVIDER_SETUP.md`
- **Technical Details:** See `PROVIDER_IMPLEMENTATION_SUMMARY.md`
- **API Docs:** See `API_DOCUMENTATION.md`
- **Environment:** See `ENVIRONMENT_SETUP.md`

---

## 💡 Tips

1. **Development:** Use LM Studio (free, fast for testing)
2. **Production:** Use OpenRouter free models (Gemini 2.0 Flash)
3. **Privacy:** Always use LM Studio for sensitive data
4. **Speed:** OpenRouter is faster if you have slow hardware
5. **Mix:** Create different sessions with different providers!

---

## ✨ Example Workflow

```bash
# Morning: Testing locally
1. Start LM Studio with qwen3-1.7b
2. Create test sessions with LM Studio
3. Iterate quickly on local machine

# Afternoon: Demo to stakeholders
1. Switch to OpenRouter (Gemini 2.0 Flash)
2. Create demo sessions with cloud inference
3. Fast, reliable responses for presentation

# All sessions coexist! 🎉
```

---

## 🎉 You're Ready!

Now you can:
- ✅ Run inference locally with LM Studio
- ✅ Run inference in cloud with OpenRouter  
- ✅ Switch between them per session
- ✅ Use both simultaneously
- ✅ Choose based on your needs

**Happy Negotiating! 🤝**

---

**Quick Start Version:** 1.0  
**Last Updated:** 2025-11-16

