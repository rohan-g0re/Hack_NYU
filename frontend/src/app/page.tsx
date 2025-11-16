'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/Button';
import { ROUTES } from '@/lib/router';

export default function LandingPage() {
  const router = useRouter();

  const handleCreateSession = () => {
    router.push(ROUTES.CONFIG);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
      <div className="container-custom">
        {/* Header/Nav */}
        <header className="py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <span className="text-xl font-bold text-neutral-900">Multi-Agent Marketplace</span>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <main className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] text-center py-12">
          <div className="max-w-4xl mx-auto">
            {/* Title */}
            <h1 className="text-5xl md:text-6xl font-bold text-neutral-900 mb-6">
              Multi-Agent Ecommerce
              <span className="block text-primary-600 mt-2">Marketplace Simulator</span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl md:text-2xl text-neutral-600 mb-8 max-w-2xl mx-auto">
              Simulate ecommerce negotiations with AI-powered buyer & sellers using LangGraph and LM Studio
            </p>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 max-w-3xl mx-auto">
              <div className="bg-white rounded-lg p-6 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">Multi-Agent System</h3>
                <p className="text-sm text-neutral-600">
                  One buyer negotiates with up to 10 seller agents simultaneously
                </p>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-secondary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-secondary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">Real-time Chat</h3>
                <p className="text-sm text-neutral-600">
                  Watch live negotiations with @mentions and streaming responses
                </p>
              </div>

              <div className="bg-white rounded-lg p-6 shadow-sm border border-neutral-200">
                <div className="w-12 h-12 bg-warning-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-warning-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 mb-2">Smart Decisions</h3>
                <p className="text-sm text-neutral-600">
                  LLM-powered buyer makes optimal purchasing decisions
                </p>
              </div>
            </div>

            {/* CTA */}
            <div className="space-y-4">
              <Button
                size="lg"
                onClick={handleCreateSession}
                className="px-8 py-4 text-lg shadow-lg hover:shadow-xl transform hover:scale-105 transition-all"
              >
                <svg className="w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Create New Session
              </Button>
              <p className="text-sm text-neutral-500">
                Configure buyer, sellers, and LLM settings to start your simulation
              </p>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="py-8 border-t border-neutral-200">
          <div className="text-center text-sm text-neutral-600">
            <p className="mb-2">
              Built with Next.js, LangGraph, and LM Studio for{' '}
              <span className="font-semibold text-primary-600">Hack NYU 2025</span>
            </p>
            <p className="text-xs text-neutral-500">
              Powered by local LLM inference • No cloud dependencies
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
}

