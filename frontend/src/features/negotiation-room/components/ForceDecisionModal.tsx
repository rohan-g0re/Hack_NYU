'use client';

import { useState } from 'react';
import { Button } from '@/components/Button';
import { forceDecision } from '@/lib/api/negotiation';
import type { SellerParticipant } from '@/lib/api/types';
import type { Offer } from '@/store/negotiationStore';

interface ForceDecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  roomId: string;
  itemName: string;
  sellers: SellerParticipant[];
  offers: Record<string, Offer>;
  constraints: {
    min_price_per_unit: number;
    max_price_per_unit: number;
  };
  quantityNeeded: number;
}

export function ForceDecisionModal({
  isOpen,
  onClose,
  roomId,
  itemName,
  sellers,
  offers,
  constraints,
  quantityNeeded,
}: ForceDecisionModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decisionType, setDecisionType] = useState<'deal' | 'no_deal'>('deal');
  const [selectedSellerId, setSelectedSellerId] = useState<string>('');
  const [finalPrice, setFinalPrice] = useState<string>('');
  const [quantity, setQuantity] = useState<string>(quantityNeeded.toString());
  const [reason, setReason] = useState<string>('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (decisionType === 'deal') {
        // Validation
        if (!selectedSellerId) {
          throw new Error('Please select a seller');
        }
        if (!finalPrice) {
          throw new Error('Please enter a final price');
        }
        if (!quantity) {
          throw new Error('Please enter a quantity');
        }

        const priceNum = parseFloat(finalPrice);
        const qtyNum = parseInt(quantity);

        if (isNaN(priceNum) || priceNum < constraints.min_price_per_unit || priceNum > constraints.max_price_per_unit) {
          throw new Error(
            `Price must be between $${constraints.min_price_per_unit} and $${constraints.max_price_per_unit}`
          );
        }

        if (isNaN(qtyNum) || qtyNum < 1 || qtyNum > quantityNeeded) {
          throw new Error(`Quantity must be between 1 and ${quantityNeeded}`);
        }

        await forceDecision(roomId, {
          decision_type: 'deal',
          selected_seller_id: selectedSellerId,
          final_price_per_unit: priceNum,
          quantity: qtyNum,
          decision_reason: reason || 'Manual decision by user',
        });
      } else {
        // No deal
        await forceDecision(roomId, {
          decision_type: 'no_deal',
          decision_reason: reason || 'Manual rejection by user',
        });
      }

      // Success - close modal and refresh state
      alert('Decision submitted successfully! The negotiation will end.');
      onClose();
      
      // Refresh the page to see updated state
      window.location.reload();
    } catch (err: any) {
      console.error('Failed to force decision:', err);
      setError(err.message || 'Failed to submit decision');
    } finally {
      setLoading(false);
    }
  };

  // Get seller name from ID
  const getSellerName = (sellerId: string) => {
    return sellers.find((s) => s.seller_id === sellerId)?.seller_name || sellerId;
  };

  // Pre-populate with best offer
  const bestOffer = Object.entries(offers).reduce((best, [sellerId, offer]) => {
    if (!best || offer.price < best.offer.price) {
      return { sellerId, offer };
    }
    return best;
  }, null as { sellerId: string; offer: Offer } | null);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-neutral-900">Force Decision</h2>
              <p className="text-sm text-neutral-600 mt-1">
                Manually end negotiation for {itemName}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-600"
              disabled={loading}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-danger-50 border border-danger-200 rounded-lg">
              <p className="text-sm text-danger-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Decision Type */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-2">Decision Type</label>
              <div className="flex space-x-4">
                <button
                  type="button"
                  onClick={() => setDecisionType('deal')}
                  className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
                    decisionType === 'deal'
                      ? 'border-success-500 bg-success-50 text-success-700'
                      : 'border-neutral-200 hover:border-neutral-300'
                  }`}
                >
                  <span className="font-medium">✅ Accept Deal</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDecisionType('no_deal')}
                  className={`flex-1 py-3 px-4 rounded-lg border-2 transition-colors ${
                    decisionType === 'no_deal'
                      ? 'border-danger-500 bg-danger-50 text-danger-700'
                      : 'border-neutral-200 hover:border-neutral-300'
                  }`}
                >
                  <span className="font-medium">❌ Reject All</span>
                </button>
              </div>
            </div>

            {decisionType === 'deal' && (
              <>
                {/* Seller Selection */}
                <div>
                  <label htmlFor="seller" className="block text-sm font-medium text-neutral-700 mb-2">
                    Select Seller *
                  </label>
                  <select
                    id="seller"
                    value={selectedSellerId}
                    onChange={(e) => {
                      setSelectedSellerId(e.target.value);
                      // Auto-populate price and quantity from offer if available
                      const offer = offers[e.target.value];
                      if (offer) {
                        setFinalPrice(offer.price.toString());
                        setQuantity(offer.quantity.toString());
                      }
                    }}
                    className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    required
                  >
                    <option value="">Choose a seller...</option>
                    {sellers.map((seller) => {
                      const offer = offers[seller.seller_id];
                      return (
                        <option key={seller.seller_id} value={seller.seller_id}>
                          {seller.seller_name}
                          {offer && ` - $${offer.price}/unit × ${offer.quantity} = $${offer.price * offer.quantity}`}
                        </option>
                      );
                    })}
                  </select>
                  {bestOffer && (
                    <p className="mt-1 text-xs text-neutral-600">
                      💡 Best offer: {getSellerName(bestOffer.sellerId)} at ${bestOffer.offer.price}/unit
                    </p>
                  )}
                </div>

                {/* Price */}
                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-neutral-700 mb-2">
                    Final Price per Unit * (${constraints.min_price_per_unit} - ${constraints.max_price_per_unit})
                  </label>
                  <input
                    id="price"
                    type="number"
                    step="0.01"
                    min={constraints.min_price_per_unit}
                    max={constraints.max_price_per_unit}
                    value={finalPrice}
                    onChange={(e) => setFinalPrice(e.target.value)}
                    className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="Enter price per unit"
                    required
                  />
                </div>

                {/* Quantity */}
                <div>
                  <label htmlFor="quantity" className="block text-sm font-medium text-neutral-700 mb-2">
                    Quantity * (1 - {quantityNeeded})
                  </label>
                  <input
                    id="quantity"
                    type="number"
                    min={1}
                    max={quantityNeeded}
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="Enter quantity"
                    required
                  />
                </div>

                {/* Total Cost Preview */}
                {finalPrice && quantity && (
                  <div className="p-4 bg-primary-50 border border-primary-200 rounded-lg">
                    <p className="text-sm font-medium text-primary-900">
                      Total Cost: ${(parseFloat(finalPrice) * parseInt(quantity)).toFixed(2)}
                    </p>
                  </div>
                )}
              </>
            )}

            {/* Reason */}
            <div>
              <label htmlFor="reason" className="block text-sm font-medium text-neutral-700 mb-2">
                Decision Reason (optional)
              </label>
              <textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={3}
                className="w-full px-4 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Why are you making this decision?"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3 pt-4 border-t border-neutral-200">
              <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant={decisionType === 'deal' ? 'primary' : 'danger'}
                loading={loading}
              >
                {decisionType === 'deal' ? 'Accept Deal' : 'Reject All Offers'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

