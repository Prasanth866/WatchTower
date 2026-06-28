# WatchTower

WatchTower is a real-time cryptocurrency portfolio tracking and paper trading simulation system. It streams live market data over WebSockets, caches real-time prices in Redis, proxies historical charts from CoinGecko, and manages virtual trading accounts with database transaction safety.

---

## Key Features

* **Real-time Price Streaming**: WebSockets stream current prices (`btc`, `eth`, `sol`, `ada`, `xrp`, `doge`, `dot`) from CoinGecko feeds via Redis Pub/Sub directly to the client.
* **Low-Latency Price Caching**: The latest price quotes are cached in Redis (`price:{coin}`) for immediate order validation and portfolio calculations.
* **Smart Historical Charting**: Historical charts are proxied from CoinGecko's `/market_chart` API, using Redis caching with strict TTL limits to prevent API throttling:
  - `days=1` -> 1 minute cache
  - `days=7` -> 5 minutes cache
  - `days=30` -> 15 minutes cache
* **ACID Paper Trading Simulation**:
  - Virtual portfolio account with $100,000 cash balance.
  - Buy/Sell trades executed inside database transaction blocks.
  - Dynamic **weighted average cost basis** calculation on purchases:
    $$newAvg = \frac{oldQty \times oldAvg + amount}{totalQty}$$
  - Allocation statistics (e.g. percentage cash vs. coin holdings).
  - Track realized and unrealized gains and losses.
* **Threshold Alert Notifications**: Configure price alert triggers (e.g. BTC > $65k) which automatically queue email alerts when prices cross targets.
* **Resend HTTP Email Service**: Sends queued alert emails asynchronously via the Resend HTTP API, with automatic environment fallbacks.

---

## Tech Stack

* **Core Backend**: FastAPI (Async REST + WebSockets)
* **Databases**: PostgreSQL (User details, Orders, Triggers) + Redis (Real-time prices, Pub/Sub, Chart caches)
* **Migrations**: Alembic
* **Containerization**: Docker & Docker Compose
* **Dependency Manager**: uv

---

## Quick Start

### 1. Copy Environment File

```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-minimum-32-char-secret-key-here
RESEND_API_KEY=re_your_api_key
RESEND_FROM_EMAIL=onboarding@resend.dev
```

### 2. Run with Docker Compose

To start local Redis and Postgres services:
```bash
docker compose --profile local-db up -d
```

To run the full app (FastAPI + Workers) inside Docker:
```bash
docker compose up -d --build
```

---

## Development & Verification

### Running the Python Test Suite

The test suite covers WebSocket auth, Resend HTTP requests, CoinGecko proxy caching, and paper trading orders:

```bash
cd backend
uv sync --group dev
uv run pytest -v
```

### Database Seeding

To seed a default user (`test@watchtower.dev` / `testpass123A!`) and standard triggers:
```bash
uv run python scripts/seed.py
```

### Manual Testing

Refer to [manual_testing_guide.md](file:///Users/prasanth/.gemini/antigravity-ide/brain/7a811463-a0a9-46b3-a1a0-2f635f46c5b3/manual_testing_guide.md) for curl and websocket commands to verify triggers, authentication, charts, and trading flows.
