import { api } from './client';
import type { HealthCheckResponse, LLMStatusResponse } from '../types';

const BASE_PATH = '/api/v1';

export async function healthCheck(): Promise<HealthCheckResponse> {
  return api.get<HealthCheckResponse>(`${BASE_PATH}/health`);
}

export async function getLLMStatus(): Promise<LLMStatusResponse> {
  return api.get<LLMStatusResponse>(`${BASE_PATH}/llm/status`);
}

