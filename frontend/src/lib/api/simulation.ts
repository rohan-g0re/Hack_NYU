import { api } from './client';
import type {
  InitializeSessionRequest,
  InitializeSessionResponse,
  SessionDetails,
  SessionSummary,
} from '../types';

const BASE_PATH = '/api/v1/simulation';

export async function initializeSession(
  config: InitializeSessionRequest
): Promise<InitializeSessionResponse> {
  return api.post<InitializeSessionResponse>(`${BASE_PATH}/initialize`, config);
}

export async function getSessionDetails(
  sessionId: string
): Promise<SessionDetails> {
  return api.get<SessionDetails>(`${BASE_PATH}/${sessionId}`);
}

export async function getSessionSummary(
  sessionId: string
): Promise<SessionSummary> {
  return api.get<SessionSummary>(`${BASE_PATH}/${sessionId}/summary`);
}

export async function deleteSession(sessionId: string): Promise<{
  message: string;
  session_id: string;
  logs_saved: boolean;
  log_path?: string;
}> {
  return api.delete(`${BASE_PATH}/${sessionId}`);
}

