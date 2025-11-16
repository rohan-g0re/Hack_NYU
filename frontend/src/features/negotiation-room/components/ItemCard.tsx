'use client';

import { useRouter } from 'next/navigation';
import { Card } from '@/components/Card';
import { Badge } from '@/components/Badge';
import { Button } from '@/components/Button';
import type { NegotiationRoom } from '@/lib/types';
import { NegotiationStatus } from '@/lib/constants';
import { formatCurrency } from '@/utils/formatters';
import { getNegotiationRoomPath } from '@/lib/router';

interface ItemCardProps {
  room: NegotiationRoom;
}

export function ItemCard({ room }: ItemCardProps) {
  const router = useRouter();

  const getStatusBadge = () => {
    switch (room.status) {
      case NegotiationStatus.PENDING:
        return <Badge variant="pending">Ready to Negotiate</Badge>;
      case NegotiationStatus.ACTIVE:
        return <Badge variant="active">In Progress</Badge>;
      case NegotiationStatus.COMPLETED:
        return <Badge variant="completed">Completed</Badge>;
      case NegotiationStatus.NO_SELLERS_AVAILABLE:
        return <Badge variant="failed">Unfulfillable</Badge>;
      case NegotiationStatus.ABORTED:
        return <Badge variant="failed">Aborted</Badge>;
      default:
        return <Badge variant="info">Unknown</Badge>;
    }
  };

  const getActionButton = () => {
    switch (room.status) {
      case NegotiationStatus.PENDING:
        return (
          <Button onClick={() => router.push(getNegotiationRoomPath(room.room_id))}>
            Start Negotiation
          </Button>
        );
      case NegotiationStatus.ACTIVE:
        return (
          <Button variant="primary" onClick={() => router.push(getNegotiationRoomPath(room.room_id))}>
            Resume
          </Button>
        );
      case NegotiationStatus.COMPLETED:
        return (
          <Button variant="ghost" onClick={() => router.push(getNegotiationRoomPath(room.room_id))}>
            View Details
          </Button>
        );
      case NegotiationStatus.NO_SELLERS_AVAILABLE:
        return (
          <Button variant="ghost" disabled>
            Skip Item
          </Button>
        );
      default:
        return null;
    }
  };

  const getItemIcon = (itemName: string) => {
    const name = itemName.toLowerCase();
    if (name.includes('laptop') || name.includes('computer')) return '💻';
    if (name.includes('mouse')) return '🖱️';
    if (name.includes('keyboard')) return '⌨️';
    if (name.includes('phone')) return '📱';
    if (name.includes('tablet')) return '📟';
    if (name.includes('watch')) return '⌚';
    if (name.includes('headphone') || name.includes('earphone')) return '🎧';
    if (name.includes('camera')) return '📷';
    if (name.includes('monitor') || name.includes('screen')) return '🖥️';
    return '📦';
  };

  return (
    <Card>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-4xl">{getItemIcon(room.item_name)}</span>
            <div>
              <h3 className="text-lg font-semibold text-neutral-900">{room.item_name}</h3>
              <p className="text-sm text-neutral-600">Quantity: {room.quantity_needed} units</p>
              {room.current_round !== undefined && room.max_rounds !== undefined && (
                <p className="text-xs text-neutral-500 mt-1">
                  Round {room.current_round} / {room.max_rounds}
                </p>
              )}
            </div>
          </div>
          {getStatusBadge()}
        </div>

        {/* Final Deal or Price Constraints */}
        {room.final_deal ? (
          <div className="bg-secondary-50 rounded-lg p-3 border border-secondary-200">
            <p className="text-xs font-medium text-secondary-700 mb-1">Final Deal:</p>
            <p className="text-sm font-semibold text-secondary-900">
              {room.final_deal.seller_name} • {formatCurrency(room.final_deal.price)}/unit • {room.final_deal.quantity} units
            </p>
            <p className="text-xs text-secondary-600 mt-1">
              Total: {formatCurrency(room.final_deal.total_cost)}
            </p>
          </div>
        ) : (
          <div className="bg-neutral-50 rounded-lg p-3 border border-neutral-200">
            <p className="text-xs font-medium text-neutral-600 mb-1">Per-Item Price Constraints:</p>
            <p className="text-sm font-semibold text-neutral-900">
              {formatCurrency(room.buyer_constraints.min_price_per_unit)} -{' '}
              {formatCurrency(room.buyer_constraints.max_price_per_unit)} per unit
            </p>
          </div>
        )}

        {/* Matched Sellers */}
        {room.participating_sellers.length > 0 ? (
          <div>
            <p className="text-sm font-medium text-neutral-700 mb-2">Matched Sellers:</p>
            <div className="flex flex-wrap gap-2">
              {room.participating_sellers.map((seller) => (
                <span
                  key={seller.seller_id}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary-100 text-primary-700 border border-primary-200"
                >
                  {seller.seller_name}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-danger-50 border border-danger-200 rounded-lg p-3">
            <p className="text-sm text-danger-700">
              <span className="font-semibold">No sellers available</span>
              {room.reason && ` - ${room.reason}`}
            </p>
          </div>
        )}

        {/* Action Button */}
        <div className="pt-2">{getActionButton()}</div>
      </div>
    </Card>
  );
}

