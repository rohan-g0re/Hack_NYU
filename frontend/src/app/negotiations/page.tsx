'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/store/sessionStore';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { ProgressBar } from '@/components/ProgressBar';
import { ItemCard } from '@/features/negotiation-room/components/ItemCard';
import { getSessionDetails } from '@/lib/api/simulation';
import { ROUTES } from '@/lib/router';
import { calculatePercentage } from '@/utils/helpers';
import { NegotiationStatus } from '@/lib/constants';

export default function NegotiationsDashboard() {
  const router = useRouter();
  const { sessionId, negotiationRooms, updateSessionDetails } = useSession();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      router.push(ROUTES.HOME);
      return;
    }

    const fetchDetails = async () => {
      setLoading(true);
      try {
        const details = await getSessionDetails(sessionId);
        updateSessionDetails(details);
      } catch (err) {
        setError('Failed to load session details');
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [sessionId, router, updateSessionDetails]);

  if (!sessionId) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <LoadingSpinner size="lg" label="Loading session..." />
      </div>
    );
  }

  const completedRooms = negotiationRooms.filter(
    (r) => r.status === NegotiationStatus.COMPLETED
  ).length;
  const totalRooms = negotiationRooms.filter(
    (r) => r.status !== NegotiationStatus.NO_SELLERS_AVAILABLE
  ).length;
  const progress = calculatePercentage(completedRooms, totalRooms || 1);

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="container-custom py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => router.push(ROUTES.HOME)}
              className="inline-flex items-center text-sm text-neutral-600 hover:text-neutral-900"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Home
            </button>
            <button
              onClick={() => router.push(ROUTES.SUMMARY)}
              className="inline-flex items-center text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              View Episode Details
              <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          <h1 className="text-3xl font-bold text-neutral-900">
            Episode Dashboard
          </h1>
          <p className="text-neutral-600 mt-2">
            Session ID: <span className="font-mono text-sm">{sessionId.slice(0, 8)}...</span>
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <ErrorMessage message={error} onDismiss={() => setError(null)} className="mb-6" />
        )}

        {/* Progress Widget */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-neutral-200 mb-8">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Purchase Plan Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-neutral-600">Items Planned</p>
              <p className="text-2xl font-bold text-neutral-900">{negotiationRooms.length}</p>
            </div>
            <div>
              <p className="text-sm text-neutral-600">Negotiations Started</p>
              <p className="text-2xl font-bold text-primary-600">
                {negotiationRooms.filter((r) => r.status === NegotiationStatus.ACTIVE).length}
              </p>
            </div>
            <div>
              <p className="text-sm text-neutral-600">Completed</p>
              <p className="text-2xl font-bold text-secondary-600">{completedRooms}</p>
            </div>
            <div>
              <p className="text-sm text-neutral-600">Unfulfillable</p>
              <p className="text-2xl font-bold text-danger-600">
                {negotiationRooms.filter((r) => r.status === NegotiationStatus.NO_SELLERS_AVAILABLE).length}
              </p>
            </div>
          </div>
          <ProgressBar progress={progress} showPercentage label="Overall Progress" />
        </div>

        {/* Items Grid */}
        <div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Items from Purchase Plan ({negotiationRooms.length})
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {negotiationRooms.map((room) => (
              <ItemCard key={room.room_id} room={room} />
            ))}
          </div>

          {negotiationRooms.length === 0 && (
            <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
              <svg className="w-16 h-16 text-neutral-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <h3 className="text-lg font-semibold text-neutral-900 mb-2">No items configured</h3>
              <p className="text-neutral-600 mb-4">
                Your purchase plan is empty. Please configure items to negotiate.
              </p>
              <button
                onClick={() => router.push(ROUTES.CONFIG)}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                Go to Configuration
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

