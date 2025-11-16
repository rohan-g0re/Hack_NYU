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
import type { SessionSummary, PurchaseSummary } from '@/lib/types';
import { formatCurrency, formatDateTime, formatDuration } from '@/utils/formatters';
import { calculatePercentage } from '@/utils/helpers';
import { ROUTES } from '@/lib/router';

export default function SummaryPage() {
  const router = useRouter();
  const { sessionId, clearSession } = useSession();
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!sessionId) {
      router.push(ROUTES.HOME);
      return;
    }

    let retryCount = 0;
    const maxRetries = 2;
    
    const fetchSummary = async () => {
      try {
        const data = await getSessionSummary(sessionId);
        
        // If we get 0 purchases but this is the first load, wait and retry once
        // This handles the race condition where we navigate before the decision is saved
        if (data.completed_purchases === 0 && data.total_items_requested > 0 && retryCount < maxRetries) {
          retryCount++;
          console.log(`No purchases found yet, retrying in 1.5s (attempt ${retryCount}/${maxRetries})`);
          setTimeout(fetchSummary, 1500);
          return;
        }
        
        setSummary(data);
        setLoading(false);
      } catch (err: any) {
        setError(err.message || 'Failed to load summary');
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

  const toggleItemExpanded = (index: number) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
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

        {/* Overall Analysis Card - Full Width */}
        {summary.overall_analysis && (
          <Card className="mb-8">
            <div>
              <h2 className="text-2xl font-bold text-neutral-900 mb-4">🤖 AI Analysis</h2>
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700 mb-2">Performance Insights</h3>
                  <p className="text-neutral-900">{summary.overall_analysis.performance_insights}</p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700 mb-2">Cross-Item Comparison</h3>
                  <p className="text-neutral-900">{summary.overall_analysis.cross_item_comparison}</p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-neutral-700 mb-2">Recommendations</h3>
                  <ul className="space-y-2">
                    {summary.overall_analysis.recommendations.map((rec, i) => (
                      <li key={i} className="flex items-start space-x-2">
                        <span className="text-primary-600 font-bold mt-0.5">•</span>
                        <span className="text-neutral-900">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </Card>
        )}

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
                    {summary.purchases.map((purchase, index) => {
                      const isExpanded = expandedItems.has(index);
                      return (
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
                          <div className="grid grid-cols-2 gap-4 text-sm mb-3">
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
                          
                          {/* AI Summary Section */}
                          {purchase.ai_summary && (
                            <div className="mt-4 pt-4 border-t border-secondary-300">
                              <button
                                onClick={() => toggleItemExpanded(index)}
                                className="flex items-center justify-between w-full text-left"
                              >
                                <span className="text-sm font-semibold text-neutral-700">
                                  🤖 AI Negotiation Insights
                                </span>
                                <svg
                                  className={`w-5 h-5 text-neutral-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </button>
                              
                              {isExpanded && (
                                <div className="mt-3 space-y-4 text-sm">
                                  <div>
                                    <p className="text-neutral-900 italic mb-3">"{purchase.ai_summary.narrative}"</p>
                                    <div className="inline-block px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-xs font-semibold">
                                      🏆 {purchase.ai_summary.deal_winner}
                                    </div>
                                  </div>
                                  
                                  {/* Buyer & Seller Analysis Side by Side */}
                                  <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-blue-50 p-3 rounded border border-blue-200">
                                      <p className="font-semibold text-blue-900 mb-2">👤 Buyer Performance</p>
                                      <div className="space-y-2">
                                        <div>
                                          <p className="text-xs font-semibold text-blue-700">✅ What Went Well</p>
                                          <p className="text-xs text-blue-900">{purchase.ai_summary.buyer_analysis.what_went_well}</p>
                                        </div>
                                        <div>
                                          <p className="text-xs font-semibold text-blue-700">💡 Can Improve</p>
                                          <p className="text-xs text-blue-900">{purchase.ai_summary.buyer_analysis.what_to_improve}</p>
                                        </div>
                                      </div>
                                    </div>
                                    
                                    <div className="bg-green-50 p-3 rounded border border-green-200">
                                      <p className="font-semibold text-green-900 mb-2">🏪 Seller Performance</p>
                                      <div className="space-y-2">
                                        <div>
                                          <p className="text-xs font-semibold text-green-700">✅ What Went Well</p>
                                          <p className="text-xs text-green-900">{purchase.ai_summary.seller_analysis.what_went_well}</p>
                                        </div>
                                        <div>
                                          <p className="text-xs font-semibold text-green-700">💡 Can Improve</p>
                                          <p className="text-xs text-green-900">{purchase.ai_summary.seller_analysis.what_to_improve}</p>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                  
                                  <div>
                                    <p className="font-semibold text-neutral-700 mb-1">Best Offer</p>
                                    <p className="text-neutral-900">{purchase.ai_summary.highlights.best_offer}</p>
                                  </div>
                                  
                                  <div>
                                    <p className="font-semibold text-neutral-700 mb-1">Turning Points</p>
                                    <ul className="space-y-1">
                                      {purchase.ai_summary.highlights.turning_points.map((point, i) => (
                                        <li key={i} className="flex items-start space-x-2">
                                          <span className="text-primary-600">→</span>
                                          <span className="text-neutral-900">{point}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                  
                                  <div>
                                    <p className="font-semibold text-neutral-700 mb-1">Tactics Used</p>
                                    <div className="flex flex-wrap gap-2">
                                      {purchase.ai_summary.highlights.tactics_used.map((tactic, i) => (
                                        <span key={i} className="px-2 py-1 bg-white rounded text-xs text-neutral-700 border border-neutral-300">
                                          {tactic}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
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

