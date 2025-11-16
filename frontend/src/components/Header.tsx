'use client';

import { useSession } from '@/store/sessionStore';
import { ProviderSelector } from './ProviderSelector';

export function Header() {
  const { llmProvider, setLLMProvider } = useSession();

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
          <ProviderSelector selectedProvider={llmProvider} onProviderChange={setLLMProvider} />
        </div>
      </div>
    </header>
  );
}

