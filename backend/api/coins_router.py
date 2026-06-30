"""API endpoints for listing available coins and proxying their historical charts from CoinGecko."""
import json
import httpx
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from typing import Any, cast
from core.dependencies import get_current_user
from core.coins import AVAILABLE_COINS, CoinInfo
from core.logger import get_logger
from models.user import User
from services.indicators import IndicatorService

router = APIRouter()
log = get_logger(__name__)

# Map local coin symbols to CoinGecko coin IDs
COINGECKO_MAPPING = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ada": "cardano",
    "xrp": "ripple",
    "doge": "dogecoin",
    "dot": "polkadot",
}


@router.get("/", response_model=list[CoinInfo])
async def list_coins(request: Request):
    """Return all available cryptocurrency coins with their live prices/stats from Redis."""
    redis = None
    if hasattr(request.app.state, "manager") and hasattr(request.app.state.manager, "redis"):
        redis = request.app.state.manager.redis

    results = []
    for coin in AVAILABLE_COINS:
        coin_copy = coin.model_copy()
        if redis is not None:
            try:
                cached_event_str = await cast(Any, redis).get(f"price_event:{coin.symbol}")
                if cached_event_str:
                    event_data = json.loads(cached_event_str)
                    coin_copy.price = event_data.get("value")
                    meta = event_data.get("metadata", {})
                    coin_copy.marketCap = meta.get("market_cap")
                    coin_copy.totalVolume = meta.get("total_volume")
                    coin_copy.change24h = meta.get("change_24h")
            except Exception as e:
                log.error("Failed to read price event cache", coin=coin.symbol, error=str(e))
        results.append(coin_copy)
    return results


@router.get("/{coin}/history")
async def get_coin_history(
    coin: str,
    request: Request,
    days: int = Query(default=7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
):
    """Proxy coin historical chart data from CoinGecko, cached in Redis."""
    _ = current_user
    coin_id = COINGECKO_MAPPING.get(coin.lower())
    if not coin_id:
        raise HTTPException(
            status_code=404,
            detail=f"Coin symbol '{coin}' is not supported. Supported: {list(COINGECKO_MAPPING.keys())}"
        )

    redis = None
    if hasattr(request.app.state, "manager") and hasattr(request.app.state.manager, "redis"):
        redis = request.app.state.manager.redis

    cache_key = f"history:{coin_id}:{days}"

    if redis is not None:
        try:
            cached_data_str = await cast(Any, redis).get(cache_key)
            if cached_data_str:
                cached_data = json.loads(cached_data_str)
                if "indicators" not in cached_data or not cached_data["indicators"]:
                    cached_data["indicators"] = IndicatorService.compute_all(cached_data.get("prices", []))
                    try:
                        await cast(Any, redis).set(cache_key, json.dumps(cached_data), ex=300)
                    except Exception:
                        pass
                return cached_data
        except Exception as e:
            log.error("Redis cache read failed", error=str(e))

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": str(days)
    }

    try:
        headers = {"User-Agent": "WatchTower/1.0"}
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        log.error("CoinGecko API request failed", error=str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch history from CoinGecko: {str(e)}"
        )

    # Compute technical indicators and inject them into response payload
    data["indicators"] = IndicatorService.compute_all(data.get("prices", []))

    if redis is not None:
        if days == 1:
            ttl = 60
        elif days == 7:
            ttl = 300
        elif days == 30:
            ttl = 900
        else:
            ttl = 300

        try:
            await cast(Any, redis).set(cache_key, json.dumps(data), ex=ttl)
        except Exception as e:
            log.error("Redis cache write failed", error=str(e))

    return data
