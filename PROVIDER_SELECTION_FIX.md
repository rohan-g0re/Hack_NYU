# Provider Selection Debug Guide

## Issue
Provider selection in frontend shows OpenRouter, but LM Studio is sent to backend.

## Root Causes

### 1. Browser Cache
The updated code might not be loaded due to browser cache.

### 2. localStorage Persistence
`sessionStore` has localStorage that persists provider separately.

### 3. Initial State
If the page loaded before the fix, old state is in memory.

---

## Fix Steps (Do ALL of these)

### Step 1: Clear Browser Storage

Open browser console (F12) and run:

```javascript
// Clear all localStorage
localStorage.clear();

// Verify it's cleared
console.log('localStorage cleared:', localStorage.length);
```

### Step 2: Hard Refresh

- **Windows/Linux:** `Ctrl + Shift + R` or `Ctrl + F5`
- **Mac:** `Cmd + Shift + R`

### Step 3: Test Provider Selection

1. Open Configuration page
2. **Watch the console** - you should see logs like:
   ```
   [LLMConfigForm] Current llmConfig: {model: '...', provider: 'lm_studio'}
   [LLMConfigForm] Current provider: lm_studio
   ```

3. **Click the Provider dropdown**
4. **Select "☁️ OpenRouter (Cloud)"**
5. **Watch console** - you should see:
   ```
   [LLMConfigForm] Provider change requested: openrouter
   [LLMConfigForm] Updating to provider: openrouter with model: google/gemini-2.0-flash-exp:free
   [ConfigStore] updateLLMConfig called with: {provider: 'openrouter', model: '...'}
   [ConfigStore] Previous llmConfig: {...}
   [ConfigStore] New llmConfig: {provider: 'openrouter', model: '...'}
   ```

6. **Verify the model list changed** to show OpenRouter models
7. **Click "Use Sample Data"** (optional)
8. **Watch console again** - provider should still be `openrouter`
9. **Click "Initialize Episode"**
10. **Check logs**:
   ```
   === REQUEST DATA ===
   Provider in llmConfig: openrouter  ← Should say 'openrouter' now!
   ```

---

## If Still Not Working

### Debug Checklist:

1. **Is the provider dropdown changing?**
   - If not, there's a UI issue

2. **Are the console logs showing?**
   - If not, code not updated - try harder refresh

3. **Do you see "[ConfigStore] updateLLMConfig called"?**
   - If not, the onChange handler isn't firing

4. **Is provider still 'lm_studio' after selection?**
   - Check if there's a state reset somewhere

5. **Did you click "Use Sample Data" BEFORE selecting provider?**
   - If yes, select provider AFTER loading sample data

---

## Manual Verification Script

Run this in browser console to check current state:

```javascript
// Check what's in the config store
const config = JSON.parse(localStorage.getItem('config') || '{}');
console.log('Stored config:', config);

// Check provider in localStorage
const provider = localStorage.getItem('llmProvider');
console.log('Stored provider:', provider);

// Force clear everything
localStorage.clear();
console.log('✅ Cleared - now refresh page');
```

---

## Expected Behavior

### When You Select OpenRouter:

1. Provider dropdown shows: **☁️ OpenRouter (Cloud)**
2. Model dropdown shows: **Gemini 2.0 Flash (Free)** and other OpenRouter models
3. Help text shows: **"☁️ OpenRouter Setup"** (green box)
4. Console shows: **`provider: 'openrouter'`**

### When You Select LM Studio:

1. Provider dropdown shows: **🖥️ LM Studio (Local)**
2. Model dropdown shows: **Qwen 3 1.7B** and other LM Studio models
3. Help text shows: **"🖥️ LM Studio Setup"** (blue box)
4. Console shows: **`provider: 'lm_studio'`**

---

## Alternative: Manual Configuration

If dropdowns don't work, you can manually set provider in console:

```javascript
// In browser console, force set OpenRouter:
window.__NEXT_DATA__ = window.__NEXT_DATA__ || {};

// This is a workaround - the real fix should work
```

---

## Nuclear Option: Complete Reset

If nothing works:

1. Close all browser tabs
2. Clear browser cache completely (Settings > Clear browsing data)
3. Close browser
4. Open browser fresh
5. Navigate to app
6. Try again

---

## Verification Backend Logs

Check your backend console for:

```
=== INITIALIZE SESSION REQUEST ===
Sellers count: 3
LLM Config: model=google/gemini-2.0-flash-exp:free, temp=0.7, max_tokens=500
LLM Provider received: openrouter  ← Should show 'openrouter'
```

---

## Last Resort: Code Inspection

If still not working, in browser console:

```javascript
// Check if the component has the fix
const element = document.querySelector('[data-testid="llm-provider-select"]');
console.log('Provider select exists:', !!element);

// Check React DevTools
// 1. Open React DevTools
// 2. Find LLMConfigForm component
// 3. Check props.llmConfig.provider
// 4. Manually change it to see if it updates
```

---

## Success Criteria

✅ Provider dropdown changes the model list  
✅ Console logs show provider being updated  
✅ "Use Sample Data" preserves provider selection  
✅ Initialize request shows correct provider  
✅ Backend logs show correct provider received  

---

**If you've done all this and it still doesn't work, share the console logs and I'll investigate further!**

