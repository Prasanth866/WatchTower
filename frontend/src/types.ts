export type CoinId = 'btc' | 'eth' | 'sol' | 'ada' | 'xrp' | 'doge' | 'dot';

// Matches backend GET /api/v1/coins/ list item
export interface CoinInfo {
  id: CoinId;
  name: string;
  symbol: string;
  // Price and 24h change are injected client-side from WS events
  price: number;
  change24h: number;
  marketCap: number;
  totalVolume: number;
}

export interface CoinHistoryPoint {
  timestamp: string;
  price: number;
  volume: number;
}

// Matches backend GET /api/v1/auth/me
export interface UserProfile {
  id: string;
  email: string;
  created_at: string;
  // Derived locally — backend has no username field
  emailNotifications: boolean;
}

// Matches backend TriggerRead schema
export interface Trigger {
  id: string;
  user_id: string;
  topic: CoinId;               // backend field name
  threshold_value: number;     // backend field name
  threshold_direction: 'above' | 'below'; // backend field name
  is_active: boolean;          // backend field name
  current_alert_count: number; // backend field name
  notification_count: number;  // backend field name
  cooldown_minutes: number;    // backend field name (in minutes)
  expires_at: string | null;   // ISO string, backend field name
  last_alert_time: string | null;
  created_at: string;
}

// Matches backend GET /api/v1/paper-trading/portfolio
export interface Portfolio {
  cash_balance: number;
  initial_balance: number;
}

// Matches backend GET /api/v1/paper-trading/holdings
export interface Holding {
  coin: string;               // backend field name (uppercase e.g. "BTC")
  quantity: number;
  average_buy_price: number;  // backend field name
}

// Matches backend GET /api/v1/paper-trading/transactions
export interface Transaction {
  id: string;
  coin: string;                // backend field name (uppercase e.g. "BTC")
  type: 'BUY' | 'SELL';       // backend uses uppercase
  quantity: number;
  price: number;
  total: number;               // backend field name
  created_at: string;          // backend field name
}

export interface SystemHealth {
  api: 'ok' | 'error' | 'down';
  redis: 'ok' | 'error' | 'down';
  postgres: 'ok' | 'error' | 'down';
  workers?: {
    enabled: boolean;
    overall: string;
    workers: Record<string, { status: string; message?: string; updated_at?: string }>;
  };
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'alert';
  title: string;
  message: string;
  timestamp: string;
}

export interface QuantIndicators {
  rsi: number;
  ema20: number;
  ema50: number;
  macd: { value: number; signal: number };
  bollinger: { middle: number; upper: number; lower: number };
  atr: number;
  score: number;
  confidence: number;
  rating: string;
}

export interface CoinHistoryResponse {
  history: CoinHistoryPoint[];
  indicators: QuantIndicators | null;
}
