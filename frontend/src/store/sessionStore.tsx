'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type {
  InitializeSessionResponse,
  SessionDetails,
  NegotiationRoom,
  BuyerConfig,
  SellerConfig,
  LLMConfig,
} from '@/lib/types';
import { SessionStatus, DEFAULT_PROVIDER } from '@/lib/constants';

interface SessionState {
  sessionId: string | null;
  status: SessionStatus;
  buyer: BuyerConfig | null;
  sellers: SellerConfig[];
  negotiationRooms: NegotiationRoom[];
  llmConfig: LLMConfig | null;
  llmProvider: 'openrouter' | 'lm_studio';
  createdAt: string | null;
}

interface SessionContextValue extends SessionState {
  initializeSession: (response: InitializeSessionResponse) => void;
  updateSessionDetails: (details: SessionDetails) => void;
  updateSessionStatus: (status: SessionStatus) => void;
  updateNegotiationRoomStatus: (roomId: string, status: string) => void;
  updateNegotiationRoom: (roomId: string, updates: Partial<NegotiationRoom>) => void;
  setLLMProvider: (provider: 'openrouter' | 'lm_studio') => void;
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
  llmProvider: DEFAULT_PROVIDER,
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
      status: details.status as SessionStatus,
      buyer: details.buyer_name ? { name: details.buyer_name, shopping_list: [] } : prev.buyer,
      // Note: Session details endpoint doesn't return rooms, so we keep existing rooms
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

  const updateNegotiationRoom = useCallback((roomId: string, updates: Partial<NegotiationRoom>) => {
    console.log(`[sessionStore] Updating room ${roomId}:`, updates);
    setState((prev) => ({
      ...prev,
      negotiationRooms: prev.negotiationRooms.map((room) =>
        room.room_id === roomId ? { ...room, ...updates } : room
      ),
    }));
  }, []);

  const setLLMProvider = useCallback((provider: 'openrouter' | 'lm_studio') => {
    setState((prev) => ({ ...prev, llmProvider: provider }));
    // Persist to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('llmProvider', provider);
    }
  }, []);

  const clearSession = useCallback(() => {
    setState(initialState);
  }, []);

  // Load provider from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('llmProvider') as 'openrouter' | 'lm_studio' | null;
      if (saved && (saved === 'openrouter' || saved === 'lm_studio')) {
        setState((prev) => ({ ...prev, llmProvider: saved }));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value: SessionContextValue = {
    ...state,
    initializeSession,
    updateSessionDetails,
    updateSessionStatus,
    updateNegotiationRoomStatus,
    updateNegotiationRoom,
    setLLMProvider,
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

