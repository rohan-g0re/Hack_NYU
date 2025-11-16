'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/store/sessionStore';
import { Button } from '@/components/Button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import { getSessionSummary } from '@/lib/api/simulation';
import type { SessionSummary } from '@/lib/types';
import { formatCurrency, formatDateTime, formatDuration } from '@/utils/formatters';
import { calculatePercentage } from '@/utils/helpers';
import { ROUTES } from '@/lib/router';

export default function SummaryPage() {
  const router = useRouter();
  const { sessionId, clearSession } = useSession();
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      router.push(ROUTES.HOME);
      return;
    }

    const fetchSummary = async () => {
      try {
        const data = await getSessionSummary(sessionId);
        setSummary(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [sessionId, router]);

  const handleStartNew = () => {
    clearSession();
    router.push(ROUTES.CONFIG);
  };

  const handleHome = () => {
    clearSession();
    router.push(ROUTES.HOME);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <LoadingSpinner size="lg" label="Loading episode summary..." />
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="container-custom py-12">
          <ErrorMessage
            message={error || 'Failed to load summary'}
            onRetry={() => window.location.reload()}
          />
        </div>
      </div>
    );
  }

  const successRate = calculatePercentage(
    summary.completed_purchases,
    summary.total_items_requested
  );

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="container-custom py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-secondary-100 rounded-full mb-4">
            <span className="text-3xl">🎊</span>
          </div>
          <h1 className="text-4xl font-bold text-neutral-900 mb-2">Episode Complete!</h1>
          <p className="text-neutral-600">Your negotiation summary is ready</p>
        </div>

        {/* Episode Summary Card */}
        <Card className="mb-8">
          <div>
            <h2 className="text-2xl font-bold text-neutral-900 mb-6">📋 Episode Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-neutral-600 mb-1">Episode ID</p>
                <p className="font-mono text-sm font-semibold text-neutral-900">
                  {summary.session_id.slice(0, 8)}...
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Buyer</p>
                <p className="font-semibold text-neutral-900">{summary.buyer_name}</p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Items Planned</p>
                <p className="text-2xl font-bold text-neutral-900">{summary.total_items_requested}</p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Items Purchased</p>
                <p className="text-2xl font-bold text-secondary-600">{summary.completed_purchases}</p>
              </div>
            </div>
            {summary.total_cost_summary.total_spent > 0 && (
              <div className="mt-6 pt-6 border-t border-neutral-200">
                <p className="text-sm text-neutral-600 mb-1">Total Spent</p>
                <p className="text-3xl font-bold text-primary-600">
                  {formatCurrency(summary.total_cost_summary.total_spent)}
                </p>
              </div>
            )}
          </div>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {/* Successful Purchases */}
            {summary.purchases.length > 0 && (
              <Card>
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-neutral-900">
                      ✅ Successful Purchases ({summary.purchases.length})
                    </h2>
                  </div>
                  <div className="space-y-4">
                    {summary.purchases.map((purchase, index) => (
                      <div key={index} className="bg-secondary-50 rounded-lg p-4 border border-secondary-200">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="text-lg font-semibold text-neutral-900">
                              {purchase.item_name} x{purchase.quantity}
                            </h3>
                            <p className="text-sm text-neutral-600">From: {purchase.selected_seller}</p>
                          </div>
                          <Badge variant="completed">Completed</Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-neutral-600">Final Price</p>
                            <p className="font-semibold text-neutral-900">
                              {formatCurrency(purchase.final_price_per_unit)}/unit
                            </p>
                          </div>
                          <div>
                            <p className="text-neutral-600">Total Cost</p>
                            <p className="font-semibold text-secondary-600">
                              {formatCurrency(purchase.total_cost)}
                            </p>
                          </div>
                          <div>
                            <p className="text-neutral-600">Negotiation</p>
                            <p className="font-semibold text-neutral-900">
                              {purchase.negotiation_rounds} rounds
                            </p>
                          </div>
                          <div>
                            <p className="text-neutral-600">Duration</p>
                            <p className="font-semibold text-neutral-900">
                              {formatDuration(purchase.duration_seconds)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* Failed Items */}
            {summary.failed_items.length > 0 && (
              <Card>
                <div>
                  <h2 className="text-xl font-bold text-neutral-900 mb-6">
                    ❌ Failed Items ({summary.failed_items.length})
                  </h2>
                  <div className="space-y-3">
                    {summary.failed_items.map((item, index) => (
                      <div key={index} className="bg-danger-50 rounded-lg p-4 border border-danger-200">
                        <div className="flex items-start space-x-3">
                          <svg className="w-5 h-5 text-danger-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                          <div className="flex-1">
                            <h3 className="font-semibold text-danger-900">{item.item_name}</h3>
                            <p className="text-sm text-danger-700 mt-1">{item.reason}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Episode Metrics */}
            <Card>
              <div>
                <h3 className="text-lg font-bold text-neutral-900 mb-4">📊 Episode Metrics</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-neutral-600">Success Rate</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <div className="flex-1 bg-neutral-200 rounded-full h-2">
                        <div
                          className="bg-secondary-500 h-2 rounded-full transition-all"
                          style={{ width: `${successRate}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-secondary-600">{successRate}%</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Avg. Negotiation Rounds</p>
                    <p className="text-xl font-bold text-primary-600">
                      {summary.negotiation_metrics.average_rounds.toFixed(1)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Avg. Duration</p>
                    <p className="text-xl font-bold text-primary-600">
                      {formatDuration(summary.negotiation_metrics.average_duration_seconds)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Total Messages</p>
                    <p className="text-xl font-bold text-primary-600">
                      {summary.negotiation_metrics.total_messages_exchanged}
                    </p>
                  </div>
                  {summary.total_cost_summary.average_savings_per_item > 0 && (
                    <div>
                      <p className="text-sm text-neutral-600">Avg. Savings/Item</p>
                      <p className="text-xl font-bold text-secondary-600">
                        {formatCurrency(summary.total_cost_summary.average_savings_per_item)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Actions */}
            <Card>
              <div className="space-y-3">
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={handleStartNew}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Start New Episode
                </Button>
                <Button variant="ghost" className="w-full" onClick={handleHome}>
                  <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                  </svg>
                  Go to Home
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

