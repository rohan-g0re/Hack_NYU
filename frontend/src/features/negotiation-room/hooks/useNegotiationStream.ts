'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useNegotiation } from '@/store/negotiationStore';
import { createNegotiationStream } from '@/lib/api/negotiation';
import type { Message, Offer, SSEEventType } from '@/lib/types';
import { SSE_RECONNECT_DELAY_BASE, MAX_RECONNECT_ATTEMPTS } from '@/lib/constants';

interface UseNegotiationStreamOptions {
  roomId: string;
  onError?: (error: string) => void;
  onComplete?: (data: any) => void;
}

export function useNegotiationStream({
  roomId,
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

  const handleBuyerMessage = useCallback(
    (data: any) => {
      const message: Message = {
        message_id: data.message_id || `msg_${Date.now()}`,
        turn: data.turn || 0,
        timestamp: data.timestamp || new Date().toISOString(),
        sender_type: 'buyer',
        sender_name: data.sender || 'Buyer',
        message: data.message,
        mentioned_agents: data.mentioned_sellers || [],
      };
      addMessage(roomId, message);
    },
    [roomId, addMessage]
  );

  const handleSellerResponse = useCallback(
    (data: any) => {
      const message: Message = {
        message_id: data.message_id || `msg_${Date.now()}`,
        turn: data.turn || 0,
        timestamp: data.timestamp || new Date().toISOString(),
        sender_type: 'seller',
        sender_id: data.sender_id || data.sender,
        sender_name: data.seller_name || 'Seller',
        message: data.message,
        updated_offer: data.updated_offer,
      };
      addMessage(roomId, message);

      // Update offer if provided
      if (data.updated_offer && data.sender_id) {
        const offer: Offer = {
          price: data.updated_offer.price,
          quantity: data.updated_offer.quantity,
          timestamp: data.timestamp || new Date().toISOString(),
        };
        updateOffer(roomId, data.sender_id, data.seller_name || 'Seller', offer);
      }
    },
    [roomId, addMessage, updateOffer]
  );

  const handleNegotiationComplete = useCallback(
    (data: any) => {
      // Add system message
      const message: Message = {
        message_id: `msg_complete_${Date.now()}`,
        turn: data.turn || 0,
        timestamp: new Date().toISOString(),
        sender_type: 'system',
        sender_name: 'System',
        message: '🎉 Negotiation Complete!',
      };
      addMessage(roomId, message);

      // Set decision
      if (data.selected_seller) {
        setDecision(roomId, {
          selected_seller_id: data.selected_seller,
          seller_name: data.seller_name,
          final_price: data.final_price,
          quantity: data.quantity || 0,
          decision_reason: data.reason || '',
          total_cost: data.final_price ? data.final_price * (data.quantity || 0) : undefined,
          timestamp: new Date().toISOString(),
        });
      }

      setStreaming(roomId, false);
      
      if (onComplete) {
        onComplete(data);
      }
    },
    [roomId, addMessage, setDecision, setStreaming, onComplete]
  );

  const handleError = useCallback(
    (data: any) => {
      console.error('SSE Error:', data);
      if (onError) {
        onError(data.error || 'Stream error occurred');
      }

      // Try to reconnect unless it's a fatal error
      if (!data.fatal && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          SSE_RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttemptsRef.current),
          30000
        );
        
        console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current++;
          connect();
        }, delay);
      } else {
        setStreaming(roomId, false);
      }
    },
    [roomId, onError, setStreaming]
  );

  const handleHeartbeat = useCallback((data: any) => {
    // Update round if provided
    if (data.current_round !== undefined) {
      updateRound(roomId, data.current_round);
    }
  }, [roomId, updateRound]);

  const connect = useCallback(() => {
    try {
      const eventSource = createNegotiationStream(roomId);

      // Connected event
      eventSource.addEventListener('connected', (event: MessageEvent) => {
        console.log('SSE Connected:', event.data);
        reconnectAttemptsRef.current = 0; // Reset on successful connection
        setStreaming(roomId, true);
      });

      // Buyer message event
      eventSource.addEventListener('buyer_message', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        handleBuyerMessage(data);
      });

      // Seller response event
      eventSource.addEventListener('seller_response', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        handleSellerResponse(data);
      });

      // Negotiation complete event
      eventSource.addEventListener('negotiation_complete', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        handleNegotiationComplete(data);
        eventSource.close();
      });

      // Error event
      eventSource.addEventListener('error', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          handleError(data);
        } catch {
          // Network error or connection lost
          if (eventSource.readyState === EventSource.CLOSED) {
            handleError({ error: 'Connection closed', fatal: false });
          }
        }
      });

      // Heartbeat event
      eventSource.addEventListener('heartbeat', (event: MessageEvent) => {
        const data = JSON.parse(event.data);
        handleHeartbeat(data);
      });

      // Browser's onerror handler (for connection failures)
      eventSource.onerror = () => {
        if (eventSource.readyState === EventSource.CLOSED) {
          handleError({ error: 'Connection failed', fatal: false });
        }
      };

      connectStream(roomId, eventSource);
    } catch (error) {
      console.error('Failed to create event source:', error);
      if (onError) {
        onError('Failed to establish connection');
      }
    }
  }, [
    roomId,
    connectStream,
    setStreaming,
    handleBuyerMessage,
    handleSellerResponse,
    handleNegotiationComplete,
    handleError,
    handleHeartbeat,
    onError,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    disconnectStream(roomId);
    setStreaming(roomId, false);
  }, [roomId, disconnectStream, setStreaming]);

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, []);

  return {
    connect,
    disconnect,
  };
}

