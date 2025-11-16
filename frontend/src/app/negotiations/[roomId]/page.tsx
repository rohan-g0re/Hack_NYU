'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useNegotiation } from '@/store/negotiationStore';
import { useSession } from '@/store/sessionStore';
import { Button } from '@/components/Button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { OffersPanel } from '@/features/negotiation-room/components/OffersPanel';
import { ChatPanel } from '@/features/negotiation-room/components/ChatPanel';
import { DecisionModal } from '@/features/negotiation-room/components/DecisionModal';
import { ForceDecisionModal } from '@/features/negotiation-room/components/ForceDecisionModal';
import { useNegotiationStream } from '@/features/negotiation-room/hooks/useNegotiationStream';
import { startNegotiation, getNegotiationState } from '@/lib/api/negotiation';
import { ROUTES } from '@/lib/router';
import { MAX_NEGOTIATION_ROUNDS, NegotiationStatus } from '@/lib/constants';

export default function NegotiationRoomPage({ params }: { params: { roomId: string } }) {
  const router = useRouter();
  const { roomId } = params;
  const { negotiationRooms, updateNegotiationRoomStatus } = useSession();
  const { initializeRoom, rooms, setActiveRoom, addMessage, updateOffer, setDecision } = useNegotiation();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [showForceDecisionModal, setShowForceDecisionModal] = useState(false);
  const [negotiationStarted, setNegotiationStarted] = useState(false);
  const initAttemptedRef = useRef(false);

  const room = negotiationRooms.find((r) => r.room_id === roomId);
  const negotiationState = rooms[roomId];

  // Initialize room and start negotiation
  useEffect(() => {
    if (!room) {
      router.push(ROUTES.NEGOTIATIONS);
      return;
    }

    // Prevent duplicate initialization (React Strict Mode runs effects twice in dev)
    if (initAttemptedRef.current) {
      return;
    }
    
    initAttemptedRef.current = true;

    const initNegotiation = async () => {
      // Initialize room state
      initializeRoom(roomId, MAX_NEGOTIATION_ROUNDS);
      setActiveRoom(roomId);

      // If the negotiation is already completed, don't start it again - just load the historical data
      if (room.status === NegotiationStatus.COMPLETED) {
        console.log('Negotiation already completed - loading historical data');
        setLoading(true);
        try {
          const state = await getNegotiationState(roomId);
          
          // Load messages into store (API returns conversation_history)
          if (state.conversation_history) {
            state.conversation_history.forEach((message) => {
              addMessage(roomId, message);
            });
          }
          
          // Load offers into store (API returns current_offers with seller_name already included)
          if (state.current_offers) {
            Object.entries(state.current_offers).forEach(([sellerId, offerWithName]) => {
              const { seller_name, ...offer } = offerWithName;
              updateOffer(roomId, sellerId, seller_name, offer);
            });
          }
          
          console.log('Historical data loaded successfully');
        } catch (err: any) {
          console.error('Failed to load historical data:', err);
          setError(err.message || 'Failed to load negotiation history');
        } finally {
          setNegotiationStarted(false); // Don't connect to SSE for completed negotiations
          setLoading(false);
        }
        return;
      }

      // Start negotiation for PENDING or ACTIVE rooms
      setLoading(true);
      try {
        await startNegotiation(roomId);
        console.log('Negotiation started successfully - enabling SSE connection');
        
        // Update status to ACTIVE in session store
        updateNegotiationRoomStatus(roomId, NegotiationStatus.ACTIVE);
        
        // Small delay to ensure backend has fully initialized the room
        await new Promise(resolve => setTimeout(resolve, 100));
        setNegotiationStarted(true); // Signal SSE to connect
      } catch (err: any) {
        // 409 Conflict means negotiation is already active - that's fine!
        if (err.status === 409 || err.code === 'NEGOTIATION_ALREADY_ACTIVE') {
          console.log('Negotiation already active, continuing...');
          updateNegotiationRoomStatus(roomId, NegotiationStatus.ACTIVE);
          await new Promise(resolve => setTimeout(resolve, 100));
          setNegotiationStarted(true); // Still enable SSE
        } else {
          console.error('Failed to start negotiation:', err);
          setError(err.message || 'Failed to start negotiation');
        }
      } finally {
        setLoading(false);
      }
    };

    initNegotiation();
  }, [roomId, room, router, initializeRoom, setActiveRoom, updateNegotiationRoomStatus, addMessage, updateOffer]);

  // Setup SSE stream - ONLY after negotiation has started
  useNegotiationStream({
    roomId,
    enabled: negotiationStarted, // Wait for start to complete
    onError: (err) => setError(err),
    onComplete: () => setShowDecisionModal(true),
  });

  if (!room) {
    return null;
  }

  if (loading) {
    const loadingMessage = room?.status === NegotiationStatus.COMPLETED 
      ? "Loading negotiation history..." 
      : "Starting negotiation...";
    
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <LoadingSpinner size="lg" label={loadingMessage} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="container-custom py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 bg-white rounded-lg p-4 shadow-sm border border-neutral-200">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push(ROUTES.NEGOTIATIONS)}
              className="inline-flex items-center text-sm text-neutral-600 hover:text-neutral-900"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Dashboard
            </button>
            <div className="h-6 w-px bg-neutral-300" />
            <div>
              <h1 className="text-xl font-bold text-neutral-900">{room.item_name} Negotiation</h1>
              <p className="text-sm text-neutral-600">
                Want: {room.quantity_needed} units • Budget: ${room.buyer_constraints.min_price_per_unit} - $
                {room.buyer_constraints.max_price_per_unit} per unit
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-xs text-neutral-600">Round</p>
              <p className="text-lg font-bold text-primary-600">
                {negotiationState?.currentRound || 0}/{negotiationState?.maxRounds || MAX_NEGOTIATION_ROUNDS}
              </p>
            </div>
            {negotiationState?.isStreaming && (
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-secondary-500 rounded-full animate-pulse" />
                <span className="text-sm text-secondary-600 font-medium">Live</span>
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <ErrorMessage message={error} onDismiss={() => setError(null)} className="mb-6" />
        )}

        {/* Split-screen Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Offers Panel (Left - 1/3) */}
          <div className="lg:col-span-1">
            <OffersPanel
              roomId={roomId}
              itemName={room.item_name}
              constraints={room.buyer_constraints}
              sellers={room.participating_sellers}
            />
          </div>

          {/* Chat Panel (Right - 2/3) */}
          <div className="lg:col-span-2">
            <ChatPanel roomId={roomId} />
          </div>
        </div>

        {/* Action Buttons - Hide for completed negotiations */}
        {room.status !== NegotiationStatus.COMPLETED && (
          <div className="mt-6 flex justify-end space-x-4">
            <Button variant="ghost" onClick={() => router.push(ROUTES.NEGOTIATIONS)}>
              Stop
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => setShowForceDecisionModal(true)}
              disabled={negotiationState?.decision !== undefined}
            >
              Force Decision
            </Button>
          </div>
        )}
      </div>

      {/* Decision Modal (Auto-shown on completion) */}
      {showDecisionModal && negotiationState?.decision && (
        <DecisionModal
          isOpen={showDecisionModal}
          onClose={() => {
            setShowDecisionModal(false);
            router.push(ROUTES.NEGOTIATIONS);
          }}
          decision={negotiationState.decision}
          itemName={room.item_name}
          rounds={negotiationState.currentRound}
        />
      )}

      {/* Force Decision Modal (Manual trigger) */}
      {showForceDecisionModal && (
        <ForceDecisionModal
          isOpen={showForceDecisionModal}
          onClose={() => setShowForceDecisionModal(false)}
          roomId={roomId}
          itemName={room.item_name}
          sellers={room.participating_sellers}
          offers={negotiationState?.offers || {}}
          constraints={room.buyer_constraints}
          quantityNeeded={room.quantity_needed}
        />
      )}
    </div>
  );
}

