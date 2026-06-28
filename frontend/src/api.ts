import {
  CoinId,
  CoinInfo,
  CoinHistoryPoint,
  UserProfile,
  Trigger,
  Portfolio,
  Holding,
  Transaction,
  SystemHealth,
} from './types';

// ---------------------------------------------------------------------------
// Static coin metadata (name/symbol/basePrice used in UI labels & fallbacks)
// ---------------------------------------------------------------------------
export const SUPPORTED_COINS: Record<CoinId, { name: string; symbol: string; basePrice: number; cap: number; vol: number }> = {
  btc:  { name: 'Bitcoin',  symbol: 'BTC',  basePrice: 67420,  cap: 1320000000000, vol: 28400000000 },
  eth:  { name: 'Ethereum', symbol: 'ETH',  basePrice: 3480,   cap: 418000000000,  vol: 14200000000 },
  sol:  { name: 'Solana',   symbol: 'SOL',  basePrice: 148.5,  cap: 68000000000,   vol: 3100000000  },
  ada:  { name: 'Cardano',  symbol: 'ADA',  basePrice: 0.38,   cap: 13500000000,   vol: 240000000   },
  xrp:  { name: 'Ripple',   symbol: 'XRP',  basePrice: 0.59,   cap: 33000000000,   vol: 850000000   },
  doge: { name: 'Dogecoin', symbol: 'DOGE', basePrice: 0.124,  cap: 18000000000,   vol: 920000000   },
  dot:  { name: 'Polkadot', symbol: 'DOT',  basePrice: 5.85,   cap: 8300000000,    vol: 110000000   },
};

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------
const TOKEN_KEY = 'watchtower_token';

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
const saveToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------
const BASE = '/api/v1';

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(body !== undefined && !(body instanceof URLSearchParams) ? { 'Content-Type': 'application/json' } : {}),
    ...(body instanceof URLSearchParams ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extraHeaders,
  };

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body instanceof URLSearchParams ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch { /* use default */ }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const get  = <T>(path: string) => request<T>('GET', path);
const post = <T>(path: string, body: unknown) => request<T>('POST', path, body);
const patch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body);
const del  = <T>(path: string) => request<T>('DELETE', path);

// ---------------------------------------------------------------------------
// Live price store — populated by WebSocket events
// Coins start with static base prices so the UI renders immediately.
// ---------------------------------------------------------------------------
let _prices: Record<CoinId, CoinInfo> = (() => {
  const m: Partial<Record<CoinId, CoinInfo>> = {};
  (Object.keys(SUPPORTED_COINS) as CoinId[]).forEach((id) => {
    const c = SUPPORTED_COINS[id];
    m[id] = { id, name: c.name, symbol: c.symbol, price: c.basePrice, change24h: 0, marketCap: c.cap, totalVolume: c.vol };
  });
  return m as Record<CoinId, CoinInfo>;
})();

type PriceSubscription = (prices: Record<CoinId, CoinInfo>, alert?: { topic: string; value: number }) => void;
const _subscribers = new Set<PriceSubscription>();

/** Subscribe to live price updates pushed from the WebSocket stream. */
export const subscribeToPrices = (sub: PriceSubscription): (() => void) => {
  _subscribers.add(sub);
  // Immediately deliver current snapshot so UI doesn't wait for first tick
  sub({ ..._prices });
  return () => _subscribers.delete(sub);
};

function _notifyPriceSubscribers(alert?: { topic: string; value: number }) {
  _subscribers.forEach((s) => s({ ..._prices }, alert));
}

/** Update a single coin's price from a WS event. */
function _applyPriceEvent(topic: string, value: number) {
  const id = topic as CoinId;
  if (!_prices[id]) return;
  const prev = _prices[id].price;
  _prices[id] = { ..._prices[id], price: value, change24h: prev > 0 ? Number((((value - prev) / prev) * 100).toFixed(2)) : 0 };
}

// ---------------------------------------------------------------------------
// WebSocket manager — one persistent connection per selected coin
// Called from App.tsx via connectPriceFeed / disconnectPriceFeed
// ---------------------------------------------------------------------------
let _ws: WebSocket | null = null;
let _wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _wsPingTimer: ReturnType<typeof setInterval> | null = null;
let _currentWsCoin: string | null = null;

export function connectPriceFeed(coin: CoinId, onAlert?: (payload: object) => void): void {
  disconnectPriceFeed();
  _currentWsCoin = coin;

  const token = getToken();
  if (!token) return; // Not authenticated yet

  const url = `/ws/api/v1/ws/${coin}?token=${encodeURIComponent(token)}`;

  const connect = () => {
    _ws = new WebSocket(`${location.origin.replace(/^http/, 'ws')}${url.replace(/^\/ws/, '')}`);

    _ws.onopen = () => {
      _wsPingTimer = setInterval(() => {
        if (_ws?.readyState === WebSocket.OPEN) _ws.send(JSON.stringify({ type: 'ping' }));
      }, 30_000);
    };

    _ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === 'ping') return;
        if (data.type === 'alert') {
          onAlert?.(data);
          _notifyPriceSubscribers({ topic: data.topic, value: data.value });
          return;
        }
        // Price event: { topic, value, unit, ... }
        if (data.topic && typeof data.value === 'number') {
          _applyPriceEvent(data.topic, data.value);
          _notifyPriceSubscribers();
        }
      } catch { /* ignore malformed frames */ }
    };

    _ws.onclose = () => {
      if (_wsPingTimer) clearInterval(_wsPingTimer);
      // Auto-reconnect if still on the same coin
      if (_currentWsCoin === coin) {
        _wsReconnectTimer = setTimeout(connect, 10_000);
      }
    };
  };

  connect();
}

export function disconnectPriceFeed(): void {
  _currentWsCoin = null;
  if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null; }
  if (_wsPingTimer)      { clearInterval(_wsPingTimer);     _wsPingTimer = null;      }
  if (_ws) { _ws.onclose = null; _ws.close(); _ws = null; }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
export const api = {

  // ── System Health ──────────────────────────────────────────────────────────
  getHealth: async (): Promise<SystemHealth> => {
    return get<SystemHealth>('/health');
  },

  // ── Auth ───────────────────────────────────────────────────────────────────
  login: async (form: URLSearchParams): Promise<{ access_token: string; token_type: string }> => {
    const res = await post<{ access_token: string; token_type: string }>('/auth/login', form);
    saveToken(res.access_token);
    return res;
  },

  register: async (form: Record<string, string>): Promise<UserProfile> => {
    const { email, password } = form;
    const res = await post<{ id: string; email: string; created_at: string }>('/auth/register', { email, password });
    return { ...res, emailNotifications: true };
  },

  getCurrentUser: async (): Promise<UserProfile | null> => {
    const token = getToken();
    if (!token) return null;
    try {
      const res = await get<{ id: string; email: string; created_at: string }>('/auth/me');
      return { ...res, emailNotifications: true };
    } catch {
      clearToken();
      return null;
    }
  },

  logout: async (): Promise<void> => {
    clearToken();
    disconnectPriceFeed();
  },

  forgotPassword: async (email: string): Promise<{ message: string }> => {
    return post<{ message: string }>('/auth/forgot-password', { email });
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    return post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword,
      confirm_password: newPassword,
    });
  },

  updateNotificationPreferences: async (enabled: boolean): Promise<UserProfile> => {
    await patch<{ email_notifications: boolean }>('/auth/notifications', { email_notifications: enabled });
    // Backend returns only the notification pref; refetch full profile
    const user = await api.getCurrentUser();
    if (!user) throw new Error('Session expired');
    return { ...user, emailNotifications: enabled };
  },

  // ── Coins ──────────────────────────────────────────────────────────────────
  getCoins: async (): Promise<CoinInfo[]> => {
    // Backend returns [{ symbol, name }]. Merge with live prices for full CoinInfo.
    const list = await get<{ symbol: string; name: string }[]>('/coins/');
    return list.map((c) => {
      const id = c.symbol.toLowerCase() as CoinId;
      const live = _prices[id];
      const meta = SUPPORTED_COINS[id];
      return live ?? {
        id,
        name: c.name,
        symbol: c.symbol,
        price: meta?.basePrice ?? 0,
        change24h: 0,
        marketCap: meta?.cap ?? 0,
        totalVolume: meta?.vol ?? 0,
      };
    });
  },

  getCoinHistory: async (coinId: CoinId, period: '1d' | '7d' | '30d'): Promise<CoinHistoryPoint[]> => {
    const days = period === '1d' ? 1 : period === '7d' ? 7 : 30;
    const data = await get<{ prices: [number, number][] }>(`/coins/${coinId}/history?days=${days}`);
    return data.prices.map(([ts, price]) => ({
      timestamp: new Date(ts).toISOString(),
      price,
      volume: 0,
    }));
  },

  // ── Triggers ───────────────────────────────────────────────────────────────
  getTriggers: async (): Promise<Trigger[]> => {
    return get<Trigger[]>('/triggers/');
  },

  createTrigger: async (data: {
    coinId: CoinId;
    direction: 'above' | 'below';
    threshold: number;
    cooldown: number;
    expiration: string | null;
  }): Promise<Trigger> => {
    return post<Trigger>('/triggers/', {
      topic: data.coinId,
      threshold_value: data.threshold,
      threshold_direction: data.direction,
      cooldown_minutes: Math.round(data.cooldown / 60), // UI sends seconds; backend wants minutes
      expires_at: data.expiration ?? null,
    });
  },

  toggleTriggerActive: async (id: string): Promise<Trigger> => {
    // Fetch current state first so we can flip it
    const triggers = await api.getTriggers();
    const current = triggers.find((t) => t.id === id);
    if (!current) throw new Error('Trigger not found');
    return patch<Trigger>(`/triggers/${id}`, { is_active: !current.is_active });
  },

  deleteTrigger: async (id: string): Promise<{ success: boolean }> => {
    await del<void>(`/triggers/${id}`);
    return { success: true };
  },

  // ── Paper Trading ──────────────────────────────────────────────────────────
  getPortfolio: async (): Promise<Portfolio> => {
    return get<Portfolio>('/paper-trading/portfolio');
  },

  getHoldings: async (): Promise<Holding[]> => {
    return get<Holding[]>('/paper-trading/holdings');
  },

  getTransactions: async (): Promise<Transaction[]> => {
    return get<Transaction[]>('/paper-trading/transactions');
  },

  buyAsset: async (coinId: CoinId, usdAmount: number): Promise<{ message: string; quantity: number; price: number; remaining_cash: number }> => {
    return post('/paper-trading/trade/buy', { coin: coinId, amount: usdAmount });
  },

  sellAsset: async (coinId: CoinId, coinQuantity: number): Promise<{ message: string; total_proceeds: number; price: number; remaining_cash: number }> => {
    return post('/paper-trading/trade/sell', { coin: coinId, quantity: coinQuantity });
  },

  resetPaperTrading: async (): Promise<{ message: string }> => {
    return post('/paper-trading/reset', {});
  },
};
