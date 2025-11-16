'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import type {
  InitializeSessionResponse,
  SessionDetails,
  NegotiationRoom,
  BuyerConfig,
  SellerConfig,
  LLMConfig,
} from '@/lib/types';
import { SessionStatus } from '@/lib/constants';

interface SessionState {
  sessionId: string | null;
  status: SessionStatus;
  buyer: BuyerConfig | null;
  sellers: SellerConfig[];
  negotiationRooms: NegotiationRoom[];
  llmConfig: LLMConfig | null;
  createdAt: string | null;
}

interface SessionContextValue extends SessionState {
  initializeSession: (response: InitializeSessionResponse) => void;
  updateSessionDetails: (details: SessionDetails) => void;
  updateSessionStatus: (status: SessionStatus) => void;
  updateNegotiationRoomStatus: (roomId: string, status: string) => void;
  clearSession: () => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

const initialState: SessionState = {
  sessionId: null,
  status: SessionStatus.IDLE,
  buyer: null,
  sellers: [],
  negotiationRooms: [],
  llmConfig: null,
  createdAt: null,
};

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>(initialState);

  const initializeSession = useCallback((response: InitializeSessionResponse) => {
    setState({
      sessionId: response.session_id,
      status: SessionStatus.ACTIVE,
      buyer: null, // Will be populated from config
      sellers: [],
      negotiationRooms: response.negotiation_rooms,
      llmConfig: null,
      createdAt: response.created_at,
    });
  }, []);

  const updateSessionDetails = useCallback((details: SessionDetails) => {
    setState((prev) => ({
      ...prev,
      status: details.status,
      buyer: details.buyer.name ? { name: details.buyer.name, shopping_list: [] } : prev.buyer,
      negotiationRooms: details.negotiation_rooms.map((room) => {
        const existing = prev.negotiationRooms.find((r) => r.room_id === room.room_id);
        return existing || ({
          room_id: room.room_id,
          item_id: '',
          item_name: room.item_name,
          quantity_needed: 0,
          buyer_constraints: { min_price_per_unit: 0, max_price_per_unit: 0 },
          participating_sellers: [],
          status: room.status,
        } as NegotiationRoom);
      }),
    }));
  }, []);

  const updateSessionStatus = useCallback((status: SessionStatus) => {
    setState((prev) => ({ ...prev, status }));
  }, []);

  const updateNegotiationRoomStatus = useCallback((roomId: string, status: string) => {
    setState((prev) => ({
      ...prev,
      negotiationRooms: prev.negotiationRooms.map((room) =>
        room.room_id === roomId ? { ...room, status: status as any } : room
      ),
    }));
  }, []);

  const clearSession = useCallback(() => {
    setState(initialState);
  }, []);

  const value: SessionContextValue = {
    ...state,
    initializeSession,
    updateSessionDetails,
    updateSessionStatus,
    updateNegotiationRoomStatus,
    clearSession,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}

