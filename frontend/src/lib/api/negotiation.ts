import { api } from './client';
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
  params: {
    decision_type: 'deal' | 'no_deal';
    selected_seller_id?: string;
    final_price_per_unit?: number;
    quantity?: number;
    decision_reason?: string;
  }
): Promise<DecisionResponse> {
  const queryParams = new URLSearchParams();
  queryParams.set('decision_type', params.decision_type);
  if (params.selected_seller_id) queryParams.set('selected_seller_id', params.selected_seller_id);
  if (params.final_price_per_unit !== undefined) queryParams.set('final_price_per_unit', params.final_price_per_unit.toString());
  if (params.quantity !== undefined) queryParams.set('quantity', params.quantity.toString());
  if (params.decision_reason) queryParams.set('decision_reason', params.decision_reason);

  return api.post<DecisionResponse>(`${BASE_PATH}/${roomId}/decide?${queryParams.toString()}`);
}

