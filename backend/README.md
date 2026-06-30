# WatchTower — Backend API Reference

WatchTower is a real-time cryptocurrency price monitoring platform. This document covers every REST endpoint and the WebSocket feed.

**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Docs:** `http://localhost:8000/docs`

---

## Authentication

Most endpoints require a Bearer token. Obtain it from [`POST /auth/login`](#post-authlogin).

Add to every protected request:
```
Authorization: Bearer <access_token>
```

---

## Table of Contents

- [Health](#health)
- [Auth](#auth)
- [Coins](#coins)
- [Triggers](#triggers)
- [Paper Trading](#paper-trading)
- [WebSocket](#websocket)

---

## Health

### `GET /health`

Check the live status of the API and all its dependencies.

**Auth required:** No

**Response `200`**
```json
{
  "api": "ok",
  "redis": "ok",
  "postgres": "ok",
  "workers": {
    "enabled": true,
    "overall": "ok",
    "workers": {
      "all": { "status": "ok", "updated_at": "2026-06-28T15:00:00Z" },
      "email:queue": { "status": "ok", "updated_at": "2026-06-28T15:00:00Z" }
    }
  },
  "side_effects": {
    "active_tasks": 0,
    "queue_size": 0,
    "dropped_events": 0
  }
}
```

---

## Auth

### `POST /auth/register`

Create a new user account.

**Auth required:** No  
**Rate limit:** 5 requests / minute

**Request body**
```json
{
  "email": "user@example.com",
  "password": "Secure@123"
}
```

| Field | Type | Rules |
|---|---|---|
| `email` | string | Valid email, must be unique |
| `password` | string | 8–72 chars, must include: uppercase, lowercase, number, special char (`!@#$%^&*...`) |

**Response `200`**
```json
{
  "id": "177bba17-8e16-4049-bea7-bbc5670cf7a5",
  "email": "user@example.com",
  "created_at": "2026-06-28T15:00:00Z"
}
```

---

### `POST /auth/login`

Log in and receive a JWT access token.

**Auth required:** No  
**Rate limit:** 10 requests / minute  
**Content-Type:** `application/x-www-form-urlencoded`

**Request body (form fields)**
```
username=user@example.com
password=Secure@123
```

**Response `200`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error `401`** — Invalid credentials

---

### `GET /auth/me`

Return the currently authenticated user's profile.

**Auth required:** Yes

**Response `200`**
```json
{
  "id": "177bba17-8e16-4049-bea7-bbc5670cf7a5",
  "email": "user@example.com",
  "created_at": "2026-06-28T15:00:00Z"
}
```

---

### `POST /auth/forgot-password`

Send a password reset link to the user's email.

**Auth required:** No

**Request body**
```json
{
  "email": "user@example.com"
}
```

**Response `200`** *(always returns success to prevent email enumeration)*
```json
{
  "message": "If that email exists, a reset link has been sent"
}
```

---

### `POST /auth/reset-password`

Reset the user's password using the token from the reset email.

**Auth required:** No

**Request body**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecure@456",
  "confirm_password": "NewSecure@456"
}
```

| Field | Type | Rules |
|---|---|---|
| `token` | string | Token from the reset email link |
| `new_password` | string | Same complexity rules as registration |
| `confirm_password` | string | Must match `new_password` |

**Response `200`**
```json
{
  "message": "Password reset successfully. Please log in."
}
```

---

### `PATCH /auth/notifications`

Toggle email notification preferences.

**Auth required:** Yes

**Request body**
```json
{
  "email_notifications": false
}
```

**Response `200`**
```json
{
  "email_notifications": false
}
```

---

## Coins

### `GET /coins/`

List all supported cryptocurrency coins.

**Auth required:** No

**Response `200`**
```json
[
  { "symbol": "btc", "name": "Bitcoin" },
  { "symbol": "eth", "name": "Ethereum" },
  { "symbol": "sol", "name": "Solana" },
  { "symbol": "ada", "name": "Cardano" },
  { "symbol": "xrp", "name": "Ripple" },
  { "symbol": "doge", "name": "Dogecoin" },
  { "symbol": "dot", "name": "Polkadot" }
]
```

---

### `GET /coins/{coin}/history`

Get historical price chart data for a coin. Results are cached in Redis.

**Auth required:** Yes

**Path parameter**

| Param | Example | Description |
|---|---|---|
| `coin` | `btc` | Coin symbol (see list above) |

**Query parameter**

| Param | Type | Default | Range | Description |
|---|---|---|---|---|
| `days` | integer | `7` | 1 – 365 | Number of days of history to return |

**Cache TTL**
- 1 day → 60 seconds
- 7 days → 5 minutes
- 30 days → 15 minutes
- Other → 5 minutes

**Response `200`**
```json
{
  "prices": [[1719561600000, 61345.12], [1719565200000, 61200.55], "..."],
  "market_caps": [[1719561600000, 1209876543210], "..."],
  "total_volumes": [[1719561600000, 29876543210], "..."]
}
```

**Error `404`** — Unsupported coin symbol  
**Error `502`** — CoinGecko API unavailable

---

## Triggers

Triggers fire alerts (on-screen via WebSocket, or email) when a coin price crosses a defined threshold.

### `GET /triggers/`

List all triggers for the authenticated user.

**Auth required:** Yes

**Response `200`**
```json
[
  {
    "id": "a1b2c3d4-...",
    "user_id": "177bba17-...",
    "topic": "btc",
    "threshold_value": 70000.0,
    "threshold_direction": "above",
    "is_active": true,
    "notification_count": 5,
    "current_alert_count": 1,
    "cooldown_minutes": 60,
    "last_alert_time": "2026-06-28T14:00:00Z",
    "created_at": "2026-06-28T10:00:00Z",
    "expires_at": null
  }
]
```

---

### `POST /triggers/`

Create a new price alert trigger.

**Auth required:** Yes

**Request body**
```json
{
  "topic": "btc",
  "threshold_value": 70000.0,
  "threshold_direction": "above",
  "is_active": true,
  "notification_count": 3,
  "cooldown_minutes": 60,
  "expires_at": null
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `topic` | string | yes | — | Coin symbol (`btc`, `eth`, `sol`, `ada`, `xrp`, `doge`, `dot`) |
| `threshold_value` | float | yes | — | Price level to watch |
| `threshold_direction` | string | yes | — | `"above"` or `"below"` |
| `is_active` | bool | no | `true` | Whether the trigger is active |
| `notification_count` | int | no | `5` | Max alerts to send (1–5) |
| `cooldown_minutes` | int | no | `60` | Minutes between repeated alerts (≥ 0) |
| `expires_at` | datetime | no | `null` | ISO 8601 datetime after which the trigger stops firing |

**Response `201`** — Returns the full `TriggerRead` object (same as GET)

**Error `400`** — Invalid coin symbol or `expires_at` in the past

---

### `PATCH /triggers/{trigger_id}`

Update an existing trigger. All fields are optional — only send what you want to change.

**Auth required:** Yes

**Path parameter:** `trigger_id` (UUID)

**Request body** *(all optional)*
```json
{
  "threshold_value": 65000.0,
  "is_active": false
}
```

**Response `200`** — Returns the updated `TriggerRead` object

**Error `404`** — Trigger not found  
**Error `401`** — Trigger belongs to another user

---

### `DELETE /triggers/{trigger_id}`

Delete a trigger permanently.

**Auth required:** Yes

**Path parameter:** `trigger_id` (UUID)

**Response `204`** — No content

**Error `404`** — Trigger not found  
**Error `401`** — Trigger belongs to another user

---

## Paper Trading

Virtual portfolio trading with real-time prices. All accounts start with **$100,000 USD** virtual cash.

> **Price Source** — every trade response includes a `price_source` field: `redis_cache` (live price from worker), `coingecko_api` (direct API call), or `mock_fallback` (static price used only when API is unavailable).

---

### `GET /paper-trading/`

Get account summary.

**Auth required:** Yes

**Response `200`**
```json
{
  "id": "acc-uuid",
  "cash_balance": 95000.0,
  "initial_balance": 100000.0,
  "created_at": "2026-06-28T10:00:00Z"
}
```

---

### `POST /paper-trading/reset`

Reset the account to its initial $100,000 balance, deleting all holdings and transactions.

**Auth required:** Yes

**Response `200`**
```json
{
  "message": "Account successfully reset to initial cash balance"
}
```

---

### `POST /paper-trading/trade/buy`

Buy a coin using virtual cash balance.

**Auth required:** Yes

**Request body**
```json
{
  "coin": "btc",
  "amount": 5000.0
}
```

| Field | Type | Rules | Description |
|---|---|---|---|
| `coin` | string | Supported symbol | Coin to buy |
| `amount` | float | > 0 | USD amount to spend |

**Response `200`**
```json
{
  "message": "Successfully purchased 0.08339588 BTC",
  "price": 59955.0,
  "price_source": "redis_cache",
  "quantity": 0.08339588,
  "total_cost": 5000.0,
  "remaining_cash": 95000.0
}
```

**Error `400`** — Insufficient cash balance or unsupported coin  
**Error `502`** — Could not fetch live price

---

### `POST /paper-trading/trade/sell`

Sell a quantity of a held coin.

**Auth required:** Yes

**Request body**
```json
{
  "coin": "btc",
  "quantity": 0.04
}
```

| Field | Type | Rules | Description |
|---|---|---|---|
| `coin` | string | Supported symbol | Coin to sell |
| `quantity` | float | > 0 | Coin quantity to sell |

**Response `200`**
```json
{
  "message": "Successfully sold 0.04000000 BTC",
  "price": 61200.0,
  "price_source": "redis_cache",
  "quantity": 0.04,
  "total_proceeds": 2448.0,
  "remaining_cash": 97448.0
}
```

**Error `400`** — Insufficient holdings or unsupported coin

---

### `GET /paper-trading/portfolio`

Full portfolio snapshot with valuation, PnL, and allocation breakdown.

**Auth required:** Yes

**Response `200`**
```json
{
  "cash_balance": 95000.0,
  "holdings_value": 4896.0,
  "total_value": 99896.0,
  "initial_balance": 100000.0,
  "total_pnl": -104.0,
  "total_pnl_pct": -0.10,
  "realized_pnl": 0.0,
  "allocation": {
    "CASH": 95.09,
    "BTC": 4.91
  },
  "holdings": [
    {
      "coin": "BTC",
      "quantity": 0.08339588,
      "average_buy_price": 59955.0,
      "current_price": 58722.0,
      "market_value": 4896.0,
      "unrealized_pnl": -104.0,
      "unrealized_pnl_pct": -2.06
    }
  ]
}
```

---

### `GET /paper-trading/holdings`

List current coin holdings with live valuations.

**Auth required:** Yes

**Response `200`**
```json
[
  {
    "coin": "BTC",
    "quantity": 0.08339588,
    "average_buy_price": 59955.0,
    "current_price": 58722.0,
    "market_value": 4896.0,
    "unrealized_pnl": -104.0,
    "unrealized_pnl_pct": -2.06,
    "updated_at": "2026-06-28T15:30:00Z"
  }
]
```

---

### `GET /paper-trading/transactions`

Full transaction history, newest first.

**Auth required:** Yes

**Response `200`**
```json
[
  {
    "id": "tx-uuid",
    "coin": "BTC",
    "type": "BUY",
    "quantity": 0.08339588,
    "price": 59955.0,
    "total": 5000.0,
    "created_at": "2026-06-28T15:00:00Z"
  }
]
```

---

## WebSocket

### `WS /ws/{coin}`

Subscribe to real-time price updates for a coin. Requires authentication via a query-param or message-based token (see `websocket_service.py`).

**Path parameter**

| Param | Example | Description |
|---|---|---|
| `coin` | `btc` | Coin symbol to subscribe to |

**Price update message** (server → client, every ~15 seconds)
```json
{
  "topic": "btc",
  "value": 61200.55,
  "unit": "USD",
  "timestamp": "2026-06-28T15:00:00Z",
  "metadata": {
    "coin": "bitcoin",
    "source": "coingecko"
  }
}
```

**Alert message** (server → client, when a trigger fires)
```json
{
  "type": "alert",
  "trigger_id": "a1b2c3d4-...",
  "topic": "btc",
  "value": 71500.0,
  "unit": "USD",
  "threshold_direction": "above",
  "threshold_value": 70000.0,
  "timestamp": "2026-06-28T15:05:00Z"
}
```

**Ping message** (server → client, every 60 seconds for connection keepalive)
```json
{ "type": "ping" }
```

---

## Supported Coins

| Symbol | Name |
|---|---|
| `btc` | Bitcoin |
| `eth` | Ethereum |
| `sol` | Solana |
| `ada` | Cardano |
| `xrp` | Ripple (XRP) |
| `doge` | Dogecoin |
| `dot` | Polkadot |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `REDIS_URL` | yes | Redis connection string |
| `SECRET_KEY` | yes | JWT signing key (min 32 chars) |
| `ALGORITHM` | no | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Token lifetime (default: `30`) |
| `BREVO_API_KEY` | no | Brevo API key for email alerts |
| `BREVO_FROM_EMAIL` | no | Verified sender email address |
| `BREVO_SENDER_NAME` | no | Sender name display (default: `WatchTower`) |
| `FRONTEND_URL` | no | Frontend URL (default: `http://localhost:5173`) |
| `CORS_ALLOWED_ORIGINS` | no | Comma-separated or JSON list of allowed origins |
| `ENABLE_WORKERS` | no | Enable price/email workers (default: `true`) |

---

## Running Locally

```bash
# Install dependencies
uv sync

# Run dev server
uv run fastapi dev main.py
```

Server starts at `http://localhost:8000`.
