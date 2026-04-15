# WatchTower

WatchTower is a real-time event monitoring platform that streams market and sports data to clients over WebSockets, supports user subscriptions, and delivers threshold-based alerts.

## Features

- JWT-based authentication with password reset flow
- Topic subscriptions and trigger-based alerting
- Redis pub/sub fanout to WebSocket clients
- Event persistence for historical charting
- Background workers for crypto, basketball, and queued email delivery
- Admin APIs for user and system visibility

## Tech Stack

- FastAPI (async API + WebSocket)
- PostgreSQL + SQLAlchemy (async)
- Redis pub/sub
- Alembic migrations
- Docker Compose

## Quick Start

1. Copy env file:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up -d --build
```

3. Apply DB migrations:

```bash
docker exec -it fastapi_app alembic upgrade head
```

4. API base URL:

```text
http://localhost:8000/api/v1
```

## Development

Run backend tests:

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

## Event Pipeline

1. Workers fetch external data and publish events to Redis.
2. Connection manager listens to Redis and broadcasts to WebSocket clients.
3. Event side-effects are processed asynchronously: event logs persisted and alerts evaluated.
4. Email worker sends queued notifications.

## Deployment Notes

- Run migrations before app startup in production.
- Use `ENABLE_WORKERS=false` for API-only replicas in multi-replica deployments.
- Configure `CORS_ALLOWED_ORIGINS` explicitly for your environments.
