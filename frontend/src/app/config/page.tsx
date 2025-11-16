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
    console.log('Initialize button clicked');
    console.log('Buyer:', buyer);
    console.log('Sellers:', sellers);
    console.log('LLM Config:', llmConfig);
    
    // Validate configuration
    const errors = validateEpisodeConfig(buyer, sellers);
    console.log('Validation errors:', errors);
    
    if (errors.length > 0) {
      const errorMsg = `Configuration errors:\n${errors.map(e => `• ${e.field}: ${e.message}`).join('\n')}`;
      console.error(errorMsg);
      setError(errorMsg);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('Calling initializeSession API...');
      console.log('=== REQUEST DATA ===');
      console.log('llmConfig being sent:', llmConfig);
      console.log('Provider in llmConfig:', llmConfig.provider);
      console.log('Full request payload:', JSON.stringify({
        buyer,
        sellers,
        llm_config: llmConfig,
      }, null, 2));
      
      const response = await initializeSession({
        buyer,
        sellers,
        llm_config: llmConfig,
      });

      console.log('=== RESPONSE DATA ===');
      console.log('API Response:', response);
      
      // Check if any negotiation rooms were created
      if (response.total_rooms === 0) {
        const skippedList = response.skipped_items?.join(', ') || 'all items';
        setError(
          `No negotiation rooms created! The following items couldn't be matched with any sellers: ${skippedList}.\n\n` +
          `Please ensure:\n` +
          `• Sellers have inventory items that match the buyer's shopping list (same item names)\n` +
          `• At least one seller has each item the buyer wants`
        );
        return;
      }
      
      setSession(response);
      router.push(ROUTES.NEGOTIATIONS);
    } catch (err) {
      console.error('API Error:', err);
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
          <div className="mb-6 bg-danger-50 border border-danger-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-danger-600 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-danger-800 mb-1">Configuration Error</h3>
                <div className="text-sm text-danger-700 whitespace-pre-line">{error}</div>
              </div>
              <button
                onClick={() => setError(null)}
                className="ml-3 text-danger-400 hover:text-danger-600"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
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
        <div className="mt-8 bg-white rounded-lg p-6 shadow-sm border border-neutral-200">
          <div className="flex items-center justify-between mb-4">
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
          
          {/* Requirements indicator */}
          {(buyer.shopping_list.length === 0 || sellers.length === 0) && (
            <div className="text-sm text-neutral-600 flex items-center">
              <svg className="w-4 h-4 mr-2 text-warning" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>
                Requirements: 
                {buyer.shopping_list.length === 0 && ' Add at least one item to shopping list.'}
                {sellers.length === 0 && ' Add at least one seller.'}
              </span>
            </div>
          )}
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

