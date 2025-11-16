'use client';

import { useState, useEffect } from 'react';
import { getLLMStatus } from '@/lib/api/status';
import { DEFAULT_PROVIDER } from '@/lib/constants';
import type { LLMStatusResponse } from '@/lib/types';

type Provider = 'openrouter' | 'lm_studio';

interface ProviderSelectorProps {
  selectedProvider: Provider;
  onProviderChange: (provider: Provider) => void;
}

export function ProviderSelector({ selectedProvider, onProviderChange }: ProviderSelectorProps) {
  const [status, setStatus] = useState<LLMStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getLLMStatus();
      setStatus(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check provider status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleProviderChange = (provider: Provider) => {
    onProviderChange(provider);
    // Re-check status when provider changes
    checkStatus();
  };

  const isAvailable = status?.llm?.available ?? false;
  const providerName = status?.llm?.provider ?? 'unknown';

  return (
    <div className="flex items-center gap-4 p-3 bg-white rounded-lg border border-neutral-200 shadow-sm">
      <div className="flex items-center gap-2">
        <label htmlFor="provider-select" className="text-sm font-medium text-neutral-700">
          LLM Provider:
        </label>
        <select
          id="provider-select"
          value={selectedProvider}
          onChange={(e) => handleProviderChange(e.target.value as Provider)}
          className="px-3 py-1.5 text-sm border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          <option value="openrouter">OpenRouter</option>
          <option value="lm_studio">LM Studio</option>
        </select>
      </div>

      <div className="flex items-center gap-2">
        {loading ? (
          <span className="text-xs text-neutral-500">Checking...</span>
        ) : error ? (
          <span className="text-xs text-danger-600">Error: {error}</span>
        ) : (
          <>
            <div
              className={`w-2 h-2 rounded-full ${
                isAvailable ? 'bg-secondary-500' : 'bg-danger-500'
              }`}
              title={isAvailable ? 'Available' : 'Unavailable'}
            />
            <span className="text-xs text-neutral-600">
              Backend: {providerName} ({isAvailable ? 'Available' : 'Unavailable'})
            </span>
          </>
        )}
      </div>

      <div className="text-xs text-neutral-500 italic">
        Note: Backend provider is set via environment variable. Restart backend to change.
      </div>
    </div>
  );
}

