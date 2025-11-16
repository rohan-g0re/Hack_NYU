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
  status: SessionStatus;
  created_at: string;
  buyer: {
    id: string;
    name: string;
  };
  sellers: Array<{
    id: string;
    name: string;
  }>;
  negotiation_rooms: Array<{
    room_id: string;
    item_name: string;
    status: NegotiationStatus;
    current_round: number;
    participating_sellers_count: number;
  }>;
  llm_provider: string;
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
  room_id: string;
  status: string;
  item_name: string;
  participating_sellers: string[];
  buyer_opening_message: string;
  stream_url: string;
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
  room_id: string;
  decision_made: boolean;
  selected_seller?: {
    seller_id: string;
    seller_name: string;
    final_price: number;
    quantity: number;
  };
  decision_reason: string;
  total_rounds: number;
  negotiation_duration_seconds: number;
}

// Summary
export interface PurchaseSummary {
  item_name: string;
  quantity: number;
  selected_seller: string;
  final_price_per_unit: number;
  total_cost: number;
  negotiation_rounds: number;
  duration_seconds: number;
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
}

// SSE Events
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
  timestamp: string;
  version: string;
  database: {
    status: string;
    url: string;
  };
  llm_provider: {
    lm_studio: string;
  };
}

export interface LLMStatusResponse {
  lm_studio: {
    available: boolean;
    base_url: string;
    models: string[];
  };
  database: {
    connected: boolean;
    total_sessions: number;
    total_negotiations: number;
  };
}

