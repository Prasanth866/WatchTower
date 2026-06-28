"""API endpoints for paper trading account management, orders, and portfolio tracking."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, cast
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.logger import get_logger
from models.user import User
from models.paper_trading import PaperAccount, Holding, Transaction

router = APIRouter()
log = get_logger(__name__)

# Precision constants
MONEY_PLACES = Decimal("0.01")        # 2 dp for USD amounts
QUANTITY_PLACES = Decimal("0.00000001")  # 8 dp for crypto quantities


def _to_dec(value: float | Decimal | str) -> Decimal:
    """Convert any numeric value to Decimal safely."""
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Cannot convert {value!r} to Decimal")


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _round_qty(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_PLACES, rounding=ROUND_HALF_UP)


class TradeBuyRequest(BaseModel):
    coin: str = Field(..., description="Local coin symbol (e.g. btc, eth)")
    amount: float = Field(..., gt=0.0, description="Amount in USD to spend")


class TradeSellRequest(BaseModel):
    coin: str = Field(..., description="Local coin symbol (e.g. btc, eth)")
    quantity: float = Field(..., gt=0.0, description="Quantity of coin to sell")


# ---------------------------------------------------------------------------
# Price fetching with Redis cache → CoinGecko API (with retry) → mock fallback
# ---------------------------------------------------------------------------

COINGECKO_MAPPING: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ada": "cardano",
    "xrp": "ripple",
    "doge": "dogecoin",
    "dot": "polkadot",
}

# Mock prices are only used as last resort; explicitly labelled so callers know.
_MOCK_PRICES: dict[str, float] = {
    "btc": 60000.0,
    "eth": 3000.0,
    "sol": 140.0,
    "ada": 0.45,
    "xrp": 0.50,
    "doge": 0.12,
    "dot": 6.50,
}

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_COINGECKO_MAX_RETRIES = 2
_COINGECKO_RETRY_DELAY = 1.0  # seconds


async def _fetch_from_coingecko(coin_symbol: str, coin_id: str) -> float:
    """Fetch price from CoinGecko with a simple exponential retry for transient errors."""
    headers = {"User-Agent": "WatchTower/1.0"}
    last_exc: Exception | None = None

    for attempt in range(1, _COINGECKO_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": coin_id, "vs_currencies": "usd"},
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", _COINGECKO_RETRY_DELAY * attempt))
                    log.warning(
                        "CoinGecko rate limited",
                        coin=coin_symbol,
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    last_exc = httpx.HTTPStatusError(
                        f"429 rate limit", request=response.request, response=response
                    )
                    continue
                response.raise_for_status()
                data = response.json()
                return float(data[coin_id]["usd"])
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_exc = exc
            log.warning(
                "CoinGecko transient error, retrying",
                coin=coin_symbol,
                attempt=attempt,
                error=str(exc),
            )
            await asyncio.sleep(_COINGECKO_RETRY_DELAY * attempt)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in _TRANSIENT_STATUS_CODES:
                last_exc = exc
                log.warning(
                    "CoinGecko server error, retrying",
                    coin=coin_symbol,
                    attempt=attempt,
                    status=exc.response.status_code,
                )
                await asyncio.sleep(_COINGECKO_RETRY_DELAY * attempt)
            else:
                # Non-transient HTTP error — don't retry
                raise
        except Exception as exc:
            last_exc = exc
            break

    raise last_exc or RuntimeError("CoinGecko fetch failed with no exception captured")


async def get_latest_price(request: Request, coin_symbol: str) -> tuple[float, str]:
    """
    Return (price, price_source) where price_source is one of:
      'redis_cache' | 'coingecko_api' | 'mock_fallback'
    """
    coin_symbol_clean = coin_symbol.lower().strip()

    # 1. Try Redis cache first (fastest, most up-to-date from the worker)
    redis_client = None
    if hasattr(request.app.state, "manager") and hasattr(request.app.state.manager, "redis"):
        redis_client = request.app.state.manager.redis

    if redis_client is not None:
        try:
            cached = await cast(Any, redis_client).get(f"price:{coin_symbol_clean}")
            if cached:
                return float(cached), "redis_cache"
        except Exception as e:
            log.error("Failed to read price from Redis", coin=coin_symbol_clean, error=str(e))

    # 2. Validate coin before hitting external API
    coin_id = COINGECKO_MAPPING.get(coin_symbol_clean)
    if not coin_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported coin symbol: '{coin_symbol}'. Supported: {list(COINGECKO_MAPPING.keys())}",
        )

    # 3. CoinGecko API with retry
    try:
        price = await _fetch_from_coingecko(coin_symbol_clean, coin_id)
        return price, "coingecko_api"
    except Exception as e:
        log.error("CoinGecko price fetch failed after retries", coin=coin_symbol_clean, error=str(e))

    # 4. Mock fallback — last resort, explicitly warned
    if coin_symbol_clean in _MOCK_PRICES:
        log.warning(
            "Using MOCK price fallback — trades will use stale hardcoded prices",
            coin=coin_symbol_clean,
        )
        return _MOCK_PRICES[coin_symbol_clean], "mock_fallback"

    raise HTTPException(
        status_code=502,
        detail=f"Failed to fetch execution price for coin '{coin_symbol}'",
    )


# ---------------------------------------------------------------------------
# Account helpers
# ---------------------------------------------------------------------------

async def get_or_create_account(db: AsyncSession, user_id: UUID) -> PaperAccount:
    """
    Atomically get or create the paper account for user_id.

    Uses INSERT ... ON CONFLICT DO NOTHING to avoid a TOCTOU race
    where two concurrent first-time requests would both SELECT None
    and both attempt INSERT, causing a UniqueConstraint violation.
    """
    # Attempt upsert-style insert; silently no-ops if the row exists.
    stmt = (
        pg_insert(PaperAccount)
        .values(
            user_id=user_id,
            cash_balance=100000.0,
            initial_balance=100000.0,
        )
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(
        select(PaperAccount).where(PaperAccount.user_id == user_id)
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# PnL calculation using Decimal arithmetic
# ---------------------------------------------------------------------------

def calculate_realized_pnl(transactions: list[Transaction]) -> float:
    """
    FIFO average-cost realized PnL calculation using Decimal arithmetic to
    avoid floating-point accumulation errors over many trades.
    """
    holdings_qty: dict[str, Decimal] = {}
    holdings_cost: dict[str, Decimal] = {}
    realized_pnl = Decimal("0")

    sorted_txs = sorted(transactions, key=lambda t: t.created_at)

    for tx in sorted_txs:
        sym = tx.coin_symbol.lower()
        if tx.type.upper() == "BUY":
            old_qty = holdings_qty.get(sym, Decimal("0"))
            old_avg = holdings_cost.get(sym, Decimal("0"))
            new_qty = _to_dec(tx.quantity)
            new_price = _to_dec(tx.price)

            total_qty = old_qty + new_qty
            if total_qty > 0:
                new_avg = (old_qty * old_avg + new_qty * new_price) / total_qty
            else:
                new_avg = Decimal("0")

            holdings_qty[sym] = total_qty
            holdings_cost[sym] = new_avg

        elif tx.type.upper() == "SELL":
            sell_qty = _to_dec(tx.quantity)
            sell_price = _to_dec(tx.price)
            avg_buy = holdings_cost.get(sym, Decimal("0"))

            realized_pnl += sell_qty * (sell_price - avg_buy)
            holdings_qty[sym] = max(Decimal("0"), holdings_qty.get(sym, Decimal("0")) - sell_qty)

    return float(_round_money(realized_pnl))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def get_account_details(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of the user's paper trading account."""
    account = await get_or_create_account(db, current_user.id)
    return {
        "id": str(account.id),
        "cash_balance": account.cash_balance,
        "initial_balance": account.initial_balance,
        "created_at": account.created_at,
    }


@router.post("/reset")
async def reset_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset paper trading account balance to initial values, clearing all trades."""
    account = await get_or_create_account(db, current_user.id)

    # Optimized: Execute direct atomic bulk deletes instead of memory-heavy loops
    await db.execute(delete(Holding).where(Holding.account_id == account.id))
    await db.execute(delete(Transaction).where(Transaction.account_id == account.id))

    account.cash_balance = account.initial_balance
    await db.commit()
    return {"message": "Account successfully reset to initial cash balance"}


@router.post("/trade/buy")
async def buy_coin(
    body: TradeBuyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a buy order using virtual cash balance."""
    account = await get_or_create_account(db, current_user.id)
    coin_symbol = body.coin.lower().strip()

    price_raw, price_source = await get_latest_price(request, coin_symbol)

    # Use Decimal for all monetary arithmetic to avoid float drift
    price = _to_dec(price_raw)
    amount = _round_money(_to_dec(body.amount))
    quantity = _round_qty(amount / price)
    balance = _to_dec(account.cash_balance)

    if balance < amount:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient cash balance. "
                f"Required: ${float(amount):.2f}, Available: ${float(balance):.2f}"
            ),
        )

    account.cash_balance = float(_round_money(balance - amount))

    holding_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id, Holding.coin_symbol == coin_symbol)
    )
    holding: Any = holding_query.scalar_one_or_none()

    if holding:
        old_qty = _to_dec(holding.quantity)
        old_avg = _to_dec(holding.average_buy_price)
        total_qty = old_qty + quantity
        # Weighted average: (old_cost + new_cost) / total_qty
        new_avg = _round_money((old_qty * old_avg + amount) / total_qty)

        holding.quantity = float(_round_qty(total_qty))
        holding.average_buy_price = float(new_avg)
        holding.updated_at = datetime.now(timezone.utc)
    else:
        holding = Holding(
            account_id=account.id,
            coin_symbol=coin_symbol,
            quantity=float(quantity),
            average_buy_price=float(_round_money(price)),
        )
        db.add(holding)

    tx = Transaction(
        account_id=account.id,
        coin_symbol=coin_symbol,
        type="BUY",
        quantity=float(quantity),
        price=float(_round_money(price)),
        total=float(amount),
    )
    db.add(tx)

    await db.commit()
    await db.refresh(holding)

    return {
        "message": f"Successfully purchased {float(quantity):.8f} {coin_symbol.upper()}",
        "price": float(_round_money(price)),
        "price_source": price_source,
        "quantity": float(quantity),
        "total_cost": float(amount),
        "remaining_cash": account.cash_balance,
    }


@router.post("/trade/sell")
async def sell_coin(
    body: TradeSellRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a sell order to cash out holdings."""
    account = await get_or_create_account(db, current_user.id)
    coin_symbol = body.coin.lower().strip()
    quantity = _round_qty(_to_dec(body.quantity))

    holding_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id, Holding.coin_symbol == coin_symbol)
    )
    holding: Any = holding_query.scalar_one_or_none()

    held_qty = _to_dec(holding.quantity) if holding else Decimal("0")
    if not holding or held_qty < quantity:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient holdings. "
                f"Attempted to sell: {float(quantity):.8f}, "
                f"Available: {float(held_qty):.8f} {coin_symbol.upper()}"
            ),
        )

    price_raw, price_source = await get_latest_price(request, coin_symbol)
    price = _to_dec(price_raw)
    proceeds = _round_money(quantity * price)

    account.cash_balance = float(_round_money(_to_dec(account.cash_balance) + proceeds))

    remaining_qty = _round_qty(held_qty - quantity)
    # Treat anything below 1e-8 (one satoshi) as fully liquidated
    if remaining_qty <= Decimal("0.00000001"):
        await db.delete(holding)
    else:
        holding.quantity = float(remaining_qty)
        holding.updated_at = datetime.now(timezone.utc)

    tx = Transaction(
        account_id=account.id,
        coin_symbol=coin_symbol,
        type="SELL",
        quantity=float(quantity),
        price=float(_round_money(price)),
        total=float(proceeds),
    )
    db.add(tx)

    await db.commit()

    return {
        "message": f"Successfully sold {float(quantity):.8f} {coin_symbol.upper()}",
        "price": float(_round_money(price)),
        "price_source": price_source,
        "quantity": float(quantity),
        "total_proceeds": float(proceeds),
        "remaining_cash": account.cash_balance,
    }


@router.get("/portfolio")
async def get_portfolio_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate the user's paper trading portfolio valuation, performance, and asset allocation."""
    account = await get_or_create_account(db, current_user.id)

    holdings_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id)
    )
    holdings = holdings_query.scalars().all()

    holdings_value = Decimal("0")
    holdings_list = []
    allocation_dict = {}

    for h in holdings:
        price_raw, _ = await get_latest_price(request, h.coin_symbol)
        price = _to_dec(price_raw)
        qty = _to_dec(h.quantity)
        avg_buy = _to_dec(h.average_buy_price)

        market_value = _round_money(qty * price)
        cost_basis = _round_money(qty * avg_buy)
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (
            float(_round_money(unrealized_pnl / cost_basis * Decimal("100")))
            if cost_basis > Decimal("0.01")
            else 0.0
        )

        holdings_value += market_value
        holdings_list.append({
            "coin": h.coin_symbol.upper(),
            "quantity": float(_round_qty(qty)),
            "average_buy_price": float(_round_money(avg_buy)),
            "current_price": float(_round_money(price)),
            "market_value": float(market_value),
            "unrealized_pnl": float(unrealized_pnl),
            "unrealized_pnl_pct": unrealized_pnl_pct,
        })

    cash_balance = _to_dec(account.cash_balance)
    total_value = _round_money(cash_balance + holdings_value)

    if total_value > Decimal("0.01"):
        allocation_dict["CASH"] = float(_round_money(cash_balance / total_value * Decimal("100")))
        for h_item in holdings_list:
            allocation_dict[h_item["coin"]] = float(
                _round_money(_to_dec(h_item["market_value"]) / total_value * Decimal("100"))
            )
    else:
        allocation_dict["CASH"] = 100.0

    tx_query = await db.execute(
        select(Transaction).where(Transaction.account_id == account.id)
    )
    transactions = list(tx_query.scalars().all())
    realized_pnl = calculate_realized_pnl(transactions)

    initial = _to_dec(account.initial_balance)
    total_pnl = float(_round_money(total_value - initial))
    total_pnl_pct = float(_round_money((total_value - initial) / initial * Decimal("100"))) if initial > 0 else 0.0

    return {
        "cash_balance": float(cash_balance),
        "holdings_value": float(holdings_value),
        "total_value": float(total_value),
        "initial_balance": float(initial),
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "realized_pnl": realized_pnl,
        "allocation": allocation_dict,
        "holdings": holdings_list,
    }


@router.get("/holdings")
async def get_holdings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve active coin holdings in user's portfolio."""
    account = await get_or_create_account(db, current_user.id)
    holdings_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id)
    )
    holdings = holdings_query.scalars().all()

    result = []
    for h in holdings:
        price_raw, _ = await get_latest_price(request, h.coin_symbol)
        price = _to_dec(price_raw)
        qty = _to_dec(h.quantity)
        avg_buy = _to_dec(h.average_buy_price)

        market_value = _round_money(qty * price)
        cost_basis = _round_money(qty * avg_buy)
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (
            float(_round_money(unrealized_pnl / cost_basis * Decimal("100")))
            if cost_basis > Decimal("0.01")
            else 0.0
        )

        result.append({
            "coin": h.coin_symbol.upper(),
            "quantity": float(_round_qty(qty)),
            "average_buy_price": float(_round_money(avg_buy)),
            "current_price": float(_round_money(price)),
            "market_value": float(market_value),
            "unrealized_pnl": float(unrealized_pnl),
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "updated_at": h.updated_at,
        })
    return result


@router.get("/transactions")
async def get_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full chronological transaction trading logs."""
    account = await get_or_create_account(db, current_user.id)
    tx_query = await db.execute(
        select(Transaction)
        .where(Transaction.account_id == account.id)
        .order_by(Transaction.created_at.desc())
    )
    transactions = tx_query.scalars().all()
    return [
        {
            "id": str(tx.id),
            "coin": tx.coin_symbol.upper(),
            "type": tx.type,
            "quantity": tx.quantity,
            "price": tx.price,
            "total": tx.total,
            "created_at": tx.created_at,
        }
        for tx in transactions
    ]