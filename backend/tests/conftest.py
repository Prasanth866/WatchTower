import os
from unittest.mock import AsyncMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/watchtower_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_pytest_1234567890")
os.environ.setdefault("BASKETBALL_API_KEY", "test_key")


@pytest_asyncio.fixture
async def client():
	from main import app

	async with AsyncClient(
		transport=ASGITransport(app=app, lifespan="off"),
		base_url="http://test",
	) as test_client:
		yield test_client


@pytest_asyncio.fixture
def mock_redis():
	redis = AsyncMock()
	redis.ping = AsyncMock(return_value=True)
	redis.publish = AsyncMock()
	return redis
