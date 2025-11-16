'use client';

import { useState, useEffect } from 'react';
import { useConfig } from '@/store/configStore';
import { useSession } from '@/store/sessionStore';
import { Card } from '@/components/Card';
import { Select } from '@/components/Select';
import { Input } from '@/components/Input';
import { DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS } from '@/lib/constants';

// LM Studio models (local)
const LM_STUDIO_MODELS = [
  { value: 'qwen/qwen3-1.7b', label: 'Qwen 3 1.7B (Fast, Lightweight)' },
  { value: 'llama-3-8b-instruct', label: 'Llama 3 8B Instruct' },
  { value: 'mistral-7b-instruct', label: 'Mistral 7B Instruct' },
  { value: 'codellama-7b-instruct', label: 'CodeLlama 7B Instruct' },
];

// OpenRouter models (cloud)
const OPENROUTER_MODELS = [
  { value: 'google/gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite (Recommended)' },
  { value: 'google/gemini-2.0-flash-exp:free', label: 'Gemini 2.0 Flash (Free)' },
  { value: 'meta-llama/llama-3.2-3b-instruct:free', label: 'Llama 3.2 3B (Free)' },
  { value: 'meta-llama/llama-3.1-8b-instruct:free', label: 'Llama 3.1 8B (Free)' },
  { value: 'mistralai/mistral-7b-instruct:free', label: 'Mistral 7B (Free)' },
];

const PROVIDERS = [
  { value: 'lm_studio', label: '🖥️ LM Studio (Local)' },
  { value: 'openrouter', label: '☁️ OpenRouter (Cloud)' },
];

export function LLMConfigForm() {
  const { llmConfig, updateLLMConfig } = useConfig();
  const { setLLMProvider } = useSession();
  const [isExpanded, setIsExpanded] = useState(true);

  // Get current provider or default
  const currentProvider = llmConfig.provider || 'lm_studio';
  
  // Debug logging
  console.log('[LLMConfigForm] Current llmConfig:', llmConfig);
  console.log('[LLMConfigForm] Current provider:', currentProvider);
  
  // Get models based on current provider
  const availableModels = currentProvider === 'lm_studio' ? LM_STUDIO_MODELS : OPENROUTER_MODELS;

  // Track provider changes
  useEffect(() => {
    console.log('[LLMConfigForm] useEffect - llmConfig changed:', llmConfig);
    console.log('[LLMConfigForm] useEffect - provider:', llmConfig.provider);
  }, [llmConfig, llmConfig.provider]);

  // Handle provider change - update both provider and switch to default model for that provider
  const handleProviderChange = (newProvider: 'lm_studio' | 'openrouter') => {
    console.log('[LLMConfigForm] Provider change requested:', newProvider);
    console.log('[LLMConfigForm] Current state before update:', { 
      currentProvider, 
      llmConfigProvider: llmConfig.provider 
    });
    
    const defaultModel = newProvider === 'lm_studio' 
      ? LM_STUDIO_MODELS[0].value 
      : OPENROUTER_MODELS[0].value;
    
    console.log('[LLMConfigForm] Updating to provider:', newProvider, 'with model:', defaultModel);
    
    // Update configStore (this is what gets sent to backend)
    updateLLMConfig({ 
      provider: newProvider,
      model: defaultModel 
    });
    
    // Also sync to sessionStore for Header consistency
    setLLMProvider(newProvider);
    
    console.log('[LLMConfigForm] Update called - synced to both stores');
    
    // Check state after a brief delay
    setTimeout(() => {
      console.log('[LLMConfigForm] State check after update - should be:', newProvider);
    }, 100);
  };

  return (
    <Card
      className="transition-all duration-200"
      header={
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-warning-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-warning-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-neutral-900">LLM Configuration</h2>
              <p className="text-sm text-neutral-600">
                {currentProvider === 'lm_studio' ? 'Local inference via LM Studio' : 'Cloud inference via OpenRouter'}
              </p>
            </div>
          </div>
          <svg
            className={`w-5 h-5 text-neutral-400 transition-transform ${isExpanded ? 'transform rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      }
    >
      {isExpanded && (
        <div className="space-y-6">
          {/* Provider Selection */}
          <div className="w-full">
            <label htmlFor="llm-provider-select" className="block text-sm font-medium text-neutral-700 mb-1">
              LLM Provider
            </label>
            <select
              id="llm-provider-select"
              key={`provider-select-${currentProvider}`}
              value={currentProvider}
              onChange={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const newValue = e.target.value as 'lm_studio' | 'openrouter';
                console.log('[LLMConfigForm] ===== NATIVE SELECT onChange FIRED! =====');
                console.log('[LLMConfigForm] New value:', newValue);
                console.log('[LLMConfigForm] Event target value:', e.target.value);
                console.log('[LLMConfigForm] Current value before change:', currentProvider);
                console.log('[LLMConfigForm] Event type:', e.type);
                console.log('[LLMConfigForm] Event:', e);
                handleProviderChange(newValue);
              }}
              onInput={(e) => {
                console.log('[LLMConfigForm] onInput fired:', e);
              }}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-colors appearance-none bg-white"
            >
              {PROVIDERS.map((provider) => (
                <option key={provider.value} value={provider.value}>
                  {provider.label}
                </option>
              ))}
            </select>
            <div className="mt-2 flex items-center gap-4">
              <p className="text-xs text-neutral-500">
                Display: <strong className="text-blue-600">{currentProvider}</strong> | 
                Stored: <strong className="text-green-600">{llmConfig.provider || 'undefined'}</strong>
              </p>
              <button
                type="button"
                onClick={() => {
                  console.log('[LLMConfigForm] MANUAL BUTTON CLICKED - Switching to OpenRouter');
                  handleProviderChange('openrouter');
                }}
                className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Test: Force OpenRouter
              </button>
              <button
                type="button"
                onClick={() => {
                  console.log('[LLMConfigForm] MANUAL BUTTON CLICKED - Switching to LM Studio');
                  handleProviderChange('lm_studio');
                }}
                className="px-3 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
              >
                Test: Force LM Studio
              </button>
            </div>
          </div>

          {/* Model Selection */}
          <Select
            label="Model"
            value={llmConfig.model}
            onChange={(e) => updateLLMConfig({ model: e.target.value })}
            options={availableModels}
          />

          {/* Advanced Settings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="temperature" className="block text-sm font-medium text-neutral-700 mb-1">
                Temperature: {llmConfig.temperature}
              </label>
              <input
                id="temperature"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={llmConfig.temperature}
                onChange={(e) => updateLLMConfig({ temperature: Number(e.target.value) })}
                className="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
              />
              <p className="mt-1 text-xs text-neutral-500">Controls randomness (0 = deterministic, 1 = creative)</p>
            </div>

            <Input
              label="Max Tokens"
              type="number"
              value={llmConfig.max_tokens}
              onChange={(e) => updateLLMConfig({ max_tokens: Number(e.target.value) })}
              min={100}
              max={2000}
              step={50}
              helpText="Maximum response length"
            />
          </div>

          {/* Info */}
          {currentProvider === 'lm_studio' ? (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="text-sm font-medium text-blue-900 mb-1">🖥️ LM Studio Setup</h4>
                  <p className="text-sm text-blue-700">
                    Make sure LM Studio is running on{' '}
                    <code className="bg-blue-100 px-1 rounded">http://localhost:1234</code> with the selected model loaded.
                    All inference happens locally on your machine.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-green-600 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="text-sm font-medium text-green-900 mb-1">☁️ OpenRouter Setup</h4>
                  <p className="text-sm text-green-700">
                    Using cloud inference via OpenRouter. Make sure your API key is configured in the backend{' '}
                    <code className="bg-green-100 px-1 rounded">.env</code> file. Free models are available!
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

