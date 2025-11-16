'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useNegotiation } from '@/store/negotiationStore';
import { openNegotiationStream } from '@/lib/api/sse';
import type { Message, Offer, NegotiationEvent } from '@/lib/types';
import { SSE_RECONNECT_DELAY_BASE, MAX_RECONNECT_ATTEMPTS } from '@/lib/constants';

interface UseNegotiationStreamOptions {
  roomId: string;
  enabled?: boolean; // Only connect when true
  onError?: (error: string) => void;
  onComplete?: (data: any) => void;
}

export function useNegotiationStream({
  roomId,
  enabled = true,
  onError,
  onComplete,
}: UseNegotiationStreamOptions) {
  const {
    addMessage,
    updateOffer,
    updateRound,
    setDecision,
    setStreaming,
    connectStream,
    disconnectStream,
  } = useNegotiation();

  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleEvent = useCallback(
    (event: NegotiationEvent) => {
      switch (event.type) {
        case 'connected':
          console.log('SSE Connected:', event.room_id);
          reconnectAttemptsRef.current = 0;
          setStreaming(roomId, true);
          break;

        case 'message':
          const message: Message = {
            message_id: `msg_${Date.now()}_${Math.random()}`,
            turn: event.turn_number,
            timestamp: event.timestamp,
            sender_type: event.sender_type,
            sender_id: event.sender_id,
            sender_name: event.sender_name,
            message: event.content,
            mentioned_agents: [],
          };
          addMessage(roomId, message);
          break;

        case 'offer':
          const offer: Offer = {
            price: event.price_per_unit,
            quantity: event.quantity,
            timestamp: event.timestamp,
          };
          updateOffer(roomId, event.seller_id, event.seller_name, offer);
          break;

        case 'decision':
          setDecision(roomId, {
            selected_seller_id: event.chosen_seller_id,
            seller_name: event.chosen_seller_name,
            final_price: event.final_price,
            quantity: event.final_quantity || 0,
            decision_reason: event.reason || '',
            total_cost: event.total_cost,
            timestamp: event.timestamp,
          });
          break;

        case 'round_start':
          updateRound(roomId, event.round_number);
          break;

        case 'negotiation_complete':
          setStreaming(roomId, false);
          if (onComplete) {
            onComplete(event);
          }
          break;

        case 'error':
          console.error('SSE Error:', event);
          if (onError) {
            onError(event.message);
          }
          // Try to reconnect unless it's a fatal error
          if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(
              SSE_RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttemptsRef.current),
              30000
            );
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectAttemptsRef.current++;
              connect();
            }, delay);
          } else {
            setStreaming(roomId, false);
          }
          break;

        case 'heartbeat':
          // Heartbeat received, connection is alive
          break;
      }
    },
    [roomId, addMessage, updateOffer, updateRound, setDecision, setStreaming, onComplete, onError]
  );

  const cleanupRef = useRef<(() => void) | null>(null);

  const connect = useCallback(() => {
    try {
      const cleanup = openNegotiationStream(roomId, handleEvent);
      cleanupRef.current = cleanup;
    } catch (error) {
      console.error('Failed to create event source:', error);
      if (onError) {
        onError('Failed to establish connection');
      }
    }
  }, [roomId, handleEvent, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }
    disconnectStream(roomId);
    setStreaming(roomId, false);
  }, [roomId, disconnectStream, setStreaming]);

  // Connect when enabled
  useEffect(() => {
    if (!enabled) {
      console.log('SSE connection waiting for negotiation to start...');
      return;
    }

    console.log('Negotiation started, connecting to SSE stream...');
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    connect,
    disconnect,
  };
}

