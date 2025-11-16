'use client';

import { useState } from 'react';
import { useConfig } from '@/store/configStore';
import { Card } from '@/components/Card';
import { Select } from '@/components/Select';
import { Input } from '@/components/Input';
import { DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS } from '@/lib/constants';

const LLM_MODELS = [
  { value: 'llama-3-8b-instruct', label: 'Llama 3 8B Instruct' },
  { value: 'llama-3-70b-instruct', label: 'Llama 3 70B Instruct' },
  { value: 'mistral-7b-instruct', label: 'Mistral 7B Instruct' },
  { value: 'mixtral-8x7b-instruct', label: 'Mixtral 8x7B Instruct' },
];

export function LLMConfigForm() {
  const { llmConfig, updateLLMConfig } = useConfig();
  const [isExpanded, setIsExpanded] = useState(true);

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
              <p className="text-sm text-neutral-600">LM Studio settings for all agents</p>
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
          {/* Model Selection */}
          <Select
            label="Model"
            value={llmConfig.model}
            onChange={(e) => updateLLMConfig({ model: e.target.value })}
            options={LLM_MODELS}
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
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="text-sm font-medium text-blue-900 mb-1">LM Studio Required</h4>
                <p className="text-sm text-blue-700">
                  All agents use LM Studio for local inference. Make sure LM Studio is running on{' '}
                  <code className="bg-blue-100 px-1 rounded">http://localhost:1234</code> with the selected model loaded.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

