import { SellerPriority, SpeakingStyle, NegotiationStatus, SessionStatus } from './constants';

// Buyer Configuration
export interface ShoppingItem {
  item_id: string;
  item_name: string;
  quantity_needed: number;
  min_price_per_unit: number;
  max_price_per_unit: number;
}

export interface BuyerConfig {
  name: string;
  shopping_list: ShoppingItem[];
}

// Seller Configuration
export interface InventoryItem {
  item_id: string;
  item_name: string;
  cost_price: number;
  selling_price: number;
  least_price: number;
  quantity_available: number;
}

export interface SellerProfile {
  priority: SellerPriority;
  speaking_style: SpeakingStyle;
}

export interface SellerConfig {
  name: string;
  inventory: InventoryItem[];
  profile: SellerProfile;
}

// LLM Configuration
export interface LLMConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  provider?: 'lm_studio' | 'openrouter'; // Optional provider selection
}

// Session
export interface InitializeSessionRequest {
  buyer: BuyerConfig;
  sellers: SellerConfig[];
  llm_config: LLMConfig;
}

export interface SellerParticipant {
  seller_id: string;
  seller_name: string;
}

export interface BuyerConstraints {
  min_price_per_unit: number;
  max_price_per_unit: number;
  quantity_needed?: number; // Optional for compatibility
}

export interface NegotiationRoom {
  room_id: string;
  item_id: string;
  item_name: string;
  quantity_needed: number;
  buyer_constraints: BuyerConstraints;
  participating_sellers: SellerParticipant[];
  status: NegotiationStatus;
  reason?: string;
  current_round?: number; // Current round number
  max_rounds?: number; // Maximum rounds
  final_deal?: {
    seller_name: string;
    price: number;
    quantity: number;
    total_cost: number;
  };
}

export interface InitializeSessionResponse {
  session_id: string;
  created_at: string;
  buyer_id: string;
  seller_ids: string[];
  negotiation_rooms: NegotiationRoom[];
  total_rooms: number;
  skipped_items: string[];
}

// Session Details
export interface SessionDetails {
  session_id: string;
  status: string;
  created_at: string;
  buyer_name: string;
  total_runs: number;
  llm_model: string;
}

// Negotiation
export interface Offer {
  price: number;
  quantity: number;
  timestamp: string;
}

export interface Message {
  message_id: string;
  turn: number;
  timestamp: string;
  sender_type: 'buyer' | 'seller' | 'system';
  sender_id?: string;
  sender_name: string;
  message: string;
  mentioned_agents?: string[];
  updated_offer?: Offer;
}

export interface NegotiationState {
  room_id: string;
  item_name: string;
  status: NegotiationStatus;
  current_round: number;
  max_rounds: number;
  conversation_history: Message[];
  current_offers: Record<string, Offer & { seller_name: string }>;
  buyer_constraints: BuyerConstraints;
}

export interface StartNegotiationResponse {
  status: string;
  stream_url: string;
  run_id: string;
  started_at: string;
}

export interface BuyerDecision {
  selected_seller_id?: string;
  seller_name?: string;
  final_price?: number;
  quantity: number;
  decision_reason: string;
  total_cost?: number;
  timestamp: string;
}

export interface DecisionResponse {
  outcome_id: string;
  decision_type: 'deal' | 'no_deal';
  selected_seller_id?: string;
  final_price?: number;
  quantity?: number;
  total_cost?: number;
  decision_reason?: string;
}

// Summary
export interface NegotiationHighlights {
  best_offer: string;
  turning_points: string[];
  tactics_used: string[];
}

export interface PartyAnalysis {
  what_went_well: string;
  what_to_improve: string;
}

export interface ItemNegotiationSummary {
  narrative: string;
  buyer_analysis: PartyAnalysis;
  seller_analysis: PartyAnalysis;
  highlights: NegotiationHighlights;
  deal_winner: string;
}

export interface PurchaseSummary {
  item_name: string;
  quantity: number;
  selected_seller: string;
  final_price_per_unit: number;
  total_cost: number;
  negotiation_rounds: number;
  duration_seconds: number;
  ai_summary?: ItemNegotiationSummary;
}

export interface FailedItem {
  item_name: string;
  reason: string;
}

export interface TotalCostSummary {
  total_spent: number;
  items_purchased: number;
  average_savings_per_item: number;
}

export interface NegotiationMetrics {
  average_rounds: number;
  average_duration_seconds: number;
  total_messages_exchanged: number;
}

export interface OverallAnalysis {
  performance_insights: string;
  cross_item_comparison: string;
  recommendations: string[];
}

export interface SessionSummary {
  session_id: string;
  buyer_name: string;
  total_items_requested: number;
  completed_purchases: number;
  failed_purchases: number;
  purchases: PurchaseSummary[];
  failed_items: FailedItem[];
  total_cost_summary: TotalCostSummary;
  negotiation_metrics: NegotiationMetrics;
  overall_analysis?: OverallAnalysis;
}

// SSE Events - Matching API_DOCUMENTATION.md event types
export type NegotiationEvent =
  | { type: 'connected'; room_id: string; timestamp: string }
  | { type: 'message'; sender_type: 'buyer' | 'seller'; sender_name: string; content: string; turn_number: number; timestamp: string; sender_id?: string; mentioned_sellers?: string[] }
  | { type: 'buyer_message'; sender_type?: 'buyer'; sender_name: string; content?: string; message?: string; turn_number?: number; round?: number; timestamp: string; sender_id?: string; mentioned_sellers?: string[] }
  | { type: 'seller_response'; sender_type?: 'seller'; seller_id: string; sender_name: string; content?: string; message?: string; offer?: { price: number; quantity: number }; turn_number?: number; round?: number; timestamp: string }
  | { type: 'offer'; seller_id: string; seller_name: string; price_per_unit: number; quantity: number; total_price?: number; timestamp: string }
  | { type: 'decision'; decision?: 'accept' | 'reject' | 'no_deal'; chosen_seller_id?: string; chosen_seller_name?: string; final_price?: number; final_quantity?: number; total_cost?: number; reason?: string; round?: number; timestamp: string }
  | { type: 'round_start'; round_number: number; max_rounds?: number; timestamp: string }
  | { type: 'negotiation_complete'; room_id?: string; outcome?: string; rounds_completed?: number; duration_seconds?: number; selected_seller_name?: string; timestamp: string }
  | { type: 'heartbeat'; timestamp: string; message?: string; round?: number }
  | { type: 'error'; error_code?: string; error?: string; message: string; retry_count?: number; timestamp: string };

// Legacy SSE event type (for backward compatibility)
export type SSEEventType =
  | 'connected'
  | 'buyer_message'
  | 'seller_response'
  | 'negotiation_complete'
  | 'error'
  | 'heartbeat';

export interface SSEEvent {
  event: SSEEventType;
  data: any;
}

// Error
export interface APIErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Array<{
      field: string;
      issue: string;
    }>;
    timestamp: string;
  };
}

// Health
export interface HealthCheckResponse {
  status: string;
  version: string;
  app_name: string;
  components: {
    llm: {
      available: boolean;
      provider: string;
    };
    database: {
      available: boolean;
    };
  };
}

export interface LLMStatusResponse {
  llm: {
    available: boolean;
    base_url?: string;
    models?: string[];
    error?: string | null;
  };
  database: {
    available: boolean;
    url?: string;
    error?: string | null;
  };
}

