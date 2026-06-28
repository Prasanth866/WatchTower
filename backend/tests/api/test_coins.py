import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from api.coins_router import router as coins_router
from core.dependencies import get_current_user


class _FakeManager:
    def __init__(self, redis) -> None:
        self.redis = redis


def _build_coins_app(*, current_user=None, redis_client=None) -> FastAPI:
    app = FastAPI()
    app.include_router(coins_router, prefix="/api/v1/coins")

    if current_user is not None:
        async def _get_current_user_override():
            return current_user
        app.dependency_overrides[get_current_user] = _get_current_user_override

    # Attach manager to app.state
    app.state.manager = _FakeManager(redis_client)
    return app


@pytest.mark.asyncio
async def test_list_coins_returns_available_coins() -> None:
    app = _build_coins_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/coins/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert data[0]["symbol"] == "btc"


@pytest.mark.asyncio
async def test_get_coin_history_cache_hit() -> None:
    # Set up mock Redis return value (JSON string representation of price chart)
    mock_redis = AsyncMock()
    mock_redis.get.return_value = '{"prices": [[1000, 60000.0]]}'

    app = _build_coins_app(current_user=MagicMock(), redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/coins/btc/history?days=7")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"prices": [[1000, 60000.0]]}
    mock_redis.get.assert_called_once_with("history:bitcoin:7")


@pytest.mark.asyncio
async def test_get_coin_history_cache_miss_calls_coingecko_and_caches() -> None:
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss

    app = _build_coins_app(current_user=MagicMock(), redis_client=mock_redis)

    # Mock Response from CoinGecko
    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = {"prices": [[2000, 61000.0]]}
    mock_http_response.raise_for_status = MagicMock()

    original_get = httpx.AsyncClient.get
    mock_calls = []

    async def mock_get_fn(self, url, *args, **kwargs):
        if "coingecko.com" in str(url):
            mock_calls.append((url, kwargs))
            return mock_http_response
        return await original_get(self, url, *args, **kwargs)

    with patch("httpx.AsyncClient.get", new=mock_get_fn):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/coins/btc/history?days=7")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"prices": [[2000, 61000.0]]}
        
        # Check HTTP GET parameters
        assert len(mock_calls) == 1
        url_called, kwargs_called = mock_calls[0]
        assert url_called == "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        assert kwargs_called["params"] == {"vs_currency": "usd", "days": "7"}

        # Check Redis set cache call (TTL = 300 for days=7)
        mock_redis.set.assert_called_once_with(
            "history:bitcoin:7",
            '{"prices": [[2000, 61000.0]]}',
            ex=300
        )


@pytest.mark.asyncio
async def test_get_coin_history_unsupported_symbol_returns_404() -> None:
    app = _build_coins_app(current_user=MagicMock())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/coins/unsupported/history?days=7")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not supported" in response.json()["detail"]
