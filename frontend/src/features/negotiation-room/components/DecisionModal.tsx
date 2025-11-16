'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Modal } from '@/components/Modal';
import { Button } from '@/components/Button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import type { BuyerDecision } from '@/lib/types';
import { formatCurrency, formatDuration } from '@/utils/formatters';
import { ROUTES } from '@/lib/router';

interface DecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  decision: BuyerDecision;
  itemName: string;
  rounds: number;
  duration?: number; // in seconds
}

export function DecisionModal({
  isOpen,
  onClose,
  decision,
  itemName,
  rounds,
  duration,
}: DecisionModalProps) {
  const router = useRouter();
  const [isNavigating, setIsNavigating] = useState(false);

  const handleViewSummary = async () => {
    setIsNavigating(true);
    
    // Wait 2 seconds to ensure backend has saved the decision
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    onClose();
    router.push(ROUTES.SUMMARY);
  };

  const handleNextItem = () => {
    onClose();
    router.push(ROUTES.NEGOTIATIONS);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" showCloseButton={false}>
      <div className="text-center py-6">
        {/* Celebration Icon */}
        <div className="mb-6">
          <div className="w-20 h-20 bg-secondary-100 rounded-full flex items-center justify-center mx-auto animate-pulse">
            <span className="text-4xl">🎉</span>
          </div>
        </div>

        {/* Title */}
        <h2 className="text-3xl font-bold text-neutral-900 mb-2">Decision Made!</h2>
        <p className="text-neutral-600 mb-8">The negotiation for {itemName} is complete</p>

        {/* Decision Details */}
        {decision.selected_seller_id ? (
          <div className="bg-secondary-50 rounded-lg p-6 mb-6 text-left">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-neutral-600 mb-1">Selected Seller</p>
                <p className="text-xl font-bold text-neutral-900">{decision.seller_name}</p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Final Price</p>
                <p className="text-xl font-bold text-secondary-600">
                  {formatCurrency(decision.final_price || 0)}/unit
                </p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Quantity</p>
                <p className="text-lg font-semibold text-neutral-900">{decision.quantity} units</p>
              </div>
              <div>
                <p className="text-sm text-neutral-600 mb-1">Total Cost</p>
                <p className="text-lg font-semibold text-neutral-900">
                  {formatCurrency(decision.total_cost || 0)}
                </p>
              </div>
            </div>

            {/* Decision Reason */}
            {decision.decision_reason && (
              <div className="mt-6 pt-6 border-t border-secondary-200">
                <p className="text-sm text-neutral-600 mb-2">Decision Reason:</p>
                <p className="text-sm text-neutral-800 italic">"{decision.decision_reason}"</p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-danger-50 rounded-lg p-6 mb-6 text-left">
            <div className="flex items-start space-x-3">
              <svg className="w-6 h-6 text-danger-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <p className="font-semibold text-danger-900 mb-1">No Deal</p>
                <p className="text-sm text-danger-700">
                  {decision.decision_reason || 'The buyer decided not to purchase this item.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Negotiation Stats */}
        <div className="bg-neutral-50 rounded-lg p-6 mb-6">
          <h3 className="text-sm font-semibold text-neutral-700 mb-4">Negotiation Stats</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-neutral-600">Rounds</p>
              <p className="text-2xl font-bold text-primary-600">{rounds}</p>
            </div>
            {duration && (
              <div>
                <p className="text-sm text-neutral-600">Duration</p>
                <p className="text-2xl font-bold text-primary-600">{formatDuration(duration)}</p>
              </div>
            )}
            <div>
              <p className="text-sm text-neutral-600">Status</p>
              <p className="text-sm font-semibold text-secondary-600 mt-1">
                {decision.selected_seller_id ? '✓ Completed' : '✗ No Deal'}
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          <Button variant="ghost" onClick={handleNextItem} disabled={isNavigating}>
            Next Item
          </Button>
          <Button onClick={handleViewSummary} disabled={isNavigating}>
            {isNavigating ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Preparing Summary...
              </>
            ) : (
              'View Episode Summary'
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

