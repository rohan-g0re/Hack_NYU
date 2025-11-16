'use client';

import { useMemo } from 'react';
import { useNegotiation } from '@/store/negotiationStore';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import type { BuyerConstraints, SellerParticipant } from '@/lib/types';
import { formatCurrency, formatRelativeTime } from '@/utils/formatters';
import { sortOffersByPrice, isOfferWithinBudget, findBestOffer } from '@/utils/helpers';
import { getSellerColor } from '@/lib/constants';

interface OffersPanelProps {
  roomId: string;
  itemName: string;
  constraints: BuyerConstraints;
  sellers: SellerParticipant[];
}

export function OffersPanel({ roomId, itemName, constraints, sellers }: OffersPanelProps) {
  const { rooms } = useNegotiation();
  const negotiationState = rooms[roomId];

  const offers = useMemo(() => {
    if (!negotiationState?.offers) return [];
    
    return Object.entries(negotiationState.offers).map(([sellerId, offer]) => ({
      sellerId,
      ...offer,
    }));
  }, [negotiationState?.offers]);

  const sortedOffers = useMemo(() => sortOffersByPrice(offers), [offers]);
  const bestOffer = useMemo(() => findBestOffer(offers), [offers]);

  const getOfferBadge = (price: number, sellerId: string) => {
    const isWithinBudget = isOfferWithinBudget(
      price,
      constraints.min_price_per_unit,
      constraints.max_price_per_unit
    );

    if (!isWithinBudget) {
      return <Badge variant="failed">Over Budget</Badge>;
    }

    if (bestOffer && sellerId === bestOffer.sellerId) {
      return <Badge variant="completed">Best Price</Badge>;
    }

    return <Badge variant="active">Within Budget</Badge>;
  };

  const getSellerIndex = (sellerId: string) => {
    return sellers.findIndex((s) => s.seller_id === sellerId);
  };

  return (
    <Card
      header={
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">Current Offers</h2>
          <p className="text-sm text-neutral-600">{itemName}</p>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Item Constraints */}
        <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
          <h3 className="text-sm font-medium text-neutral-700 mb-2">Item Constraints</h3>
          <div className="space-y-1 text-sm">
            <p>
              <span className="text-neutral-600">Wanted Quantity:</span>{' '}
              <span className="font-semibold">{constraints.quantity_needed || 'TBD'} units</span>
            </p>
            <p>
              <span className="text-neutral-600">Min Price:</span>{' '}
              <span className="font-semibold">{formatCurrency(constraints.min_price_per_unit)}/unit</span>
            </p>
            <p>
              <span className="text-neutral-600">Max Price:</span>{' '}
              <span className="font-semibold">{formatCurrency(constraints.max_price_per_unit)}/unit</span>
            </p>
          </div>
        </div>

        {/* Offers List */}
        <div>
          <h3 className="text-sm font-medium text-neutral-700 mb-3">Seller Offers</h3>
          {sortedOffers.length === 0 ? (
            <div className="text-center py-8 text-neutral-500">
              <svg className="w-12 h-12 mx-auto mb-2 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm">Waiting for offers...</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sortedOffers.map((offer) => {
                const sellerIndex = getSellerIndex(offer.sellerId);
                const sellerColor = getSellerColor(sellerIndex);
                
                return (
                  <div
                    key={offer.sellerId}
                    className="border-2 rounded-lg p-4 transition-all hover:shadow-md"
                    style={{ borderColor: sellerColor + '40' }}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: sellerColor }}
                        />
                        <h4 className="font-semibold text-neutral-900">{offer.seller_name}</h4>
                      </div>
                      {getOfferBadge(offer.price, offer.sellerId)}
                    </div>
                    
                    <div className="space-y-1">
                      <p className="text-2xl font-bold text-neutral-900">
                        {formatCurrency(offer.price)}
                        <span className="text-sm font-normal text-neutral-600">/unit</span>
                      </p>
                      <p className="text-sm text-neutral-600">
                        📦 Quantity: {offer.quantity} units
                      </p>
                      <p className="text-xs text-neutral-500">
                        🕐 Updated {formatRelativeTime(offer.timestamp)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

