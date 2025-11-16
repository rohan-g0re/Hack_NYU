// Enums
export enum SellerPriority {
  CUSTOMER_RETENTION = 'customer_retention',
  MAXIMIZE_PROFIT = 'maximize_profit',
}

export enum SpeakingStyle {
  RUDE = 'rude',
  VERY_SWEET = 'very_sweet',
}

export enum NegotiationStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  NO_SELLERS_AVAILABLE = 'no_sellers_available',
  ABORTED = 'aborted',
}

export enum SessionStatus {
  IDLE = 'idle',
  INITIALIZING = 'initializing',
  ACTIVE = 'active',
  COMPLETED = 'completed',
}

// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;
export const DEFAULT_PROVIDER = (process.env.NEXT_PUBLIC_DEFAULT_PROVIDER || 'lm_studio') as 'openrouter' | 'lm_studio';

// Configuration Defaults
export const MAX_SELLERS = 10;
export const MAX_NEGOTIATION_ROUNDS = 10;
export const DEFAULT_TEMPERATURE = 0.7;
export const DEFAULT_MAX_TOKENS = 500;

// SSE Configuration
export const SSE_HEARTBEAT_INTERVAL = 15000; // 15 seconds
export const SSE_RECONNECT_DELAY_BASE = 1000; // 1 second
export const MAX_RECONNECT_ATTEMPTS = 5;

// Seller Colors (for UI)
export const SELLER_COLORS = [
  '#8B5CF6', // purple
  '#EC4899', // pink
  '#14B8A6', // teal
  '#F59E0B', // amber
  '#EF4444', // red
  '#10B981', // green
  '#6366F1', // indigo
  '#F97316', // orange
  '#06B6D4', // cyan
  '#84CC16', // lime
];

export function getSellerColor(index: number): string {
  return SELLER_COLORS[index % SELLER_COLORS.length];
}

