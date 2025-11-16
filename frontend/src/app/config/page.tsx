'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useConfig } from '@/store/configStore';
import { useSession } from '@/store/sessionStore';
import { Button } from '@/components/Button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { BuyerConfigForm } from '@/features/episode-config/components/BuyerConfigForm';
import { SellersConfigForm } from '@/features/episode-config/components/SellersConfigForm';
import { LLMConfigForm } from '@/features/episode-config/components/LLMConfigForm';
import { initializeSession } from '@/lib/api/simulation';
import { validateEpisodeConfig } from '@/utils/validators';
import { ROUTES } from '@/lib/router';
import { APIError } from '@/lib/api/client';

export default function ConfigPage() {
  const router = useRouter();
  const { buyer, sellers, llmConfig, loadSampleData } = useConfig();
  const { initializeSession: setSession } = useSession();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInitialize = async () => {
    // Validate configuration
    const errors = validateEpisodeConfig(buyer, sellers);
    if (errors.length > 0) {
      setError(`Configuration errors: ${errors.map(e => e.message).join(', ')}`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await initializeSession({
        buyer,
        sellers,
        llm_config: llmConfig,
      });

      setSession(response);
      router.push(ROUTES.NEGOTIATIONS);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to initialize session. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUseSampleData = () => {
    loadSampleData();
    setError(null);
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="container-custom py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push(ROUTES.HOME)}
            className="inline-flex items-center text-sm text-neutral-600 hover:text-neutral-900 mb-4"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Home
          </button>
          <h1 className="text-3xl font-bold text-neutral-900">Episode Configuration</h1>
          <p className="text-neutral-600 mt-2">
            Configure buyer, sellers, and LLM settings to start your simulation
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <ErrorMessage
            message={error}
            onDismiss={() => setError(null)}
            className="mb-6"
          />
        )}

        {/* Configuration Forms */}
        <div className="space-y-6">
          {/* Buyer Configuration */}
          <BuyerConfigForm />

          {/* Sellers Configuration */}
          <SellersConfigForm />

          {/* LLM Configuration */}
          <LLMConfigForm />
        </div>

        {/* Actions */}
        <div className="mt-8 flex items-center justify-between bg-white rounded-lg p-6 shadow-sm border border-neutral-200">
          <Button
            variant="ghost"
            onClick={handleUseSampleData}
            disabled={loading}
          >
            Use Sample Data
          </Button>

          <Button
            size="lg"
            onClick={handleInitialize}
            disabled={loading || buyer.shopping_list.length === 0 || sellers.length === 0}
            loading={loading}
          >
            {loading ? 'Initializing...' : 'Initialize Episode'}
          </Button>
        </div>

        {/* Loading Overlay */}
        {loading && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8">
              <LoadingSpinner size="lg" label="Initializing marketplace..." />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

