import { api, API_BASE_URL } from './client';
import type {
  StartNegotiationResponse,
  NegotiationState,
  DecisionResponse,
} from '../types';

const BASE_PATH = '/api/v1/negotiation';

export async function startNegotiation(
  roomId: string
): Promise<StartNegotiationResponse> {
  return api.post<StartNegotiationResponse>(`${BASE_PATH}/${roomId}/start`);
}

export async function getNegotiationState(
  roomId: string,
  agentId?: string,
  agentType?: 'buyer' | 'seller'
): Promise<NegotiationState> {
  const params: Record<string, string> = {};
  if (agentId) params.agent_id = agentId;
  if (agentType) params.agent_type = agentType;

  return api.get<NegotiationState>(`${BASE_PATH}/${roomId}/state`, { params });
}

export async function sendBuyerMessage(
  roomId: string,
  message: string
): Promise<{
  message_id: string;
  timestamp: string;
  mentioned_sellers: string[];
  processing: boolean;
}> {
  return api.post(`${BASE_PATH}/${roomId}/message`, { message });
}

export async function forceDecision(
  roomId: string,
  forceSelectSeller?: string
): Promise<DecisionResponse> {
  const body = forceSelectSeller ? { force_select_seller: forceSelectSeller } : undefined;
  return api.post<DecisionResponse>(`${BASE_PATH}/${roomId}/decide`, body);
}

export function createNegotiationStream(roomId: string): EventSource {
  const url = `${API_BASE_URL}${BASE_PATH}/${roomId}/stream`;
  return new EventSource(url);
}

