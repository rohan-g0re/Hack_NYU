'use client';

import { useEffect } from 'react';
import { useSession } from '@/store/sessionStore';
import { useConfig } from '@/store/configStore';
import { ProviderSelector } from './ProviderSelector';

export function Header() {
  const { llmProvider, setLLMProvider } = useSession();
  const { llmConfig, updateLLMConfig } = useConfig();

  // Sync configStore -> sessionStore on mount (if configStore has provider set)
  useEffect(() => {
    if (llmConfig.provider && llmConfig.provider !== llmProvider) {
      console.log('[Header] Syncing configStore provider to sessionStore:', llmConfig.provider);
      setLLMProvider(llmConfig.provider);
    }
  }, [llmConfig.provider, llmProvider, setLLMProvider]);

  // Sync provider changes to configStore (which is used in API requests)
  const handleProviderChange = (provider: 'openrouter' | 'lm_studio') => {
    console.log('[Header] Provider change requested:', provider);
    
    // Update sessionStore for UI consistency
    setLLMProvider(provider);
    
    // Always switch to provider-appropriate default model when provider changes
    // This ensures we never send an LM Studio model to OpenRouter or vice versa
    const defaultModel = provider === 'lm_studio' 
      ? 'qwen/qwen3-1.7b' 
      : 'google/gemini-2.5-flash-lite';
    
    updateLLMConfig({
      provider: provider,
      model: defaultModel, // Always use provider-appropriate default
    });
    
    console.log('[Header] Synced provider to configStore:', provider, 'with model:', defaultModel);
  };

  // Use configStore provider as source of truth, fallback to sessionStore
  const displayProvider = llmConfig.provider || llmProvider;

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-neutral-200 shadow-sm">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <span className="text-lg font-bold text-neutral-900">Multi-Agent Marketplace</span>
          </div>
          <ProviderSelector selectedProvider={displayProvider} onProviderChange={handleProviderChange} />
        </div>
      </div>
    </header>
  );
}

