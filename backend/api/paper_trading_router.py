"""API endpoints for paper trading account management, orders, and portfolio tracking."""
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, cast
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.logger import get_logger
from models.user import User
from models.paper_trading import PaperAccount, Holding, Transaction

router = APIRouter()
log = get_logger(__name__)


class TradeBuyRequest(BaseModel):
    coin: str = Field(..., description="Local coin symbol (e.g. btc, eth)")
    amount: float = Field(..., gt=0.0, description="Amount in USD to spend")


class TradeSellRequest(BaseModel):
    coin: str = Field(..., description="Local coin symbol (e.g. btc, eth)")
    quantity: float = Field(..., gt=0.0, description="Quantity of coin to sell")


async def get_latest_price(request: Request, coin_symbol: str) -> float:
    coin_symbol_clean = coin_symbol.lower().strip()

    redis_client = None
    if hasattr(request.app.state, "manager") and hasattr(request.app.state.manager, "redis"):
        redis_client = request.app.state.manager.redis

    redis = redis_client
    if redis is not None:
        try:
            cached = await cast(Any, redis).get(f"price:{coin_symbol_clean}")
            if cached:
                return float(cached)
        except Exception as e:
            log.error("Failed to read price from Redis", coin=coin_symbol_clean, error=str(e))

    coingecko_mapping = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "ada": "cardano",
        "xrp": "ripple",
        "doge": "dogecoin",
        "dot": "polkadot",
    }
    coin_id = coingecko_mapping.get(coin_symbol_clean)
    if not coin_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported coin symbol: '{coin_symbol}'. Supported: {list(coingecko_mapping.keys())}"
        )

    try:
        headers = {"User-Agent": "WatchTower/1.0"}
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"}
            )
            response.raise_for_status()
            data = response.json()
            return float(data[coin_id]["usd"])
    except Exception as e:
        log.error("CoinGecko price fallback failed", coin=coin_symbol_clean, error=str(e))
        mock_prices = {
            "btc": 60000.0,
            "eth": 3000.0,
            "sol": 140.0,
            "ada": 0.45,
            "xrp": 0.50,
            "doge": 0.12,
            "dot": 6.50,
        }
        if coin_symbol_clean in mock_prices:
            return mock_prices[coin_symbol_clean]
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch execution price for coin '{coin_symbol}'"
        )


async def get_or_create_account(db: AsyncSession, user_id: UUID) -> PaperAccount:
    result = await db.execute(
        select(PaperAccount).where(PaperAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        account = PaperAccount(
            user_id=user_id,
            cash_balance=100000.0,
            initial_balance=100000.0
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
    return account


def calculate_realized_pnl(transactions: list[Transaction]) -> float:
    holdings_qty = {}
    holdings_cost = {}
    realized_pnl = 0.0

    sorted_txs = sorted(transactions, key=lambda t: t.created_at)

    for tx in sorted_txs:
        sym = tx.coin_symbol.lower()
        if tx.type.upper() == "BUY":
            old_qty = holdings_qty.get(sym, 0.0)
            old_avg = holdings_cost.get(sym, 0.0)
            new_qty = tx.quantity
            new_price = tx.price

            total_qty = old_qty + new_qty
            if total_qty > 0:
                new_avg = (old_qty * old_avg + new_qty * new_price) / total_qty
            else:
                new_avg = 0.0

            holdings_qty[sym] = total_qty
            holdings_cost[sym] = new_avg
        elif tx.type.upper() == "SELL":
            sell_qty = tx.quantity
            sell_price = tx.price
            avg_buy = holdings_cost.get(sym, 0.0)

            realized_pnl += sell_qty * (sell_price - avg_buy)
            holdings_qty[sym] = max(0.0, holdings_qty.get(sym, 0.0) - sell_qty)

    return realized_pnl


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
        "created_at": account.created_at
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

    # Reset balance cleanly
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
    amount = body.amount

    price = await get_latest_price(request, coin_symbol)
    quantity = amount / price

    if account.cash_balance < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient cash balance. Required: ${amount:.2f}, Available: ${account.cash_balance:.2f}"
        )

    account.cash_balance -= amount

    holding_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id, Holding.coin_symbol == coin_symbol)
    )
    holding: Any = holding_query.scalar_one_or_none()

    if holding:
        old_qty = holding.quantity
        old_avg = holding.average_buy_price
        total_qty = old_qty + quantity
        new_avg = (old_qty * old_avg + amount) / total_qty

        holding.quantity = total_qty
        holding.average_buy_price = new_avg
        holding.updated_at = datetime.now(timezone.utc)
    else:
        holding = Holding(
            account_id=account.id,
            coin_symbol=coin_symbol,
            quantity=quantity,
            average_buy_price=price
        )
        db.add(holding)

    tx = Transaction(
        account_id=account.id,
        coin_symbol=coin_symbol,
        type="BUY",
        quantity=quantity,
        price=price,
        total=amount
    )
    db.add(tx)

    await db.commit()
    await db.refresh(holding)

    return {
        "message": f"Successfully purchased {quantity:.6f} {coin_symbol.upper()}",
        "price": price,
        "quantity": quantity,
        "total_cost": amount,
        "remaining_cash": account.cash_balance
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
    quantity = body.quantity

    holding_query = await db.execute(
        select(Holding).where(Holding.account_id == account.id, Holding.coin_symbol == coin_symbol)
    )
    holding: Any = holding_query.scalar_one_or_none()

    if not holding or holding.quantity < quantity:
        available = holding.quantity if holding else 0.0
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient holdings. Attempted to sell: {quantity:.6f}, Available: {available:.6f} {coin_symbol.upper()}"
        )

    price = await get_latest_price(request, coin_symbol)
    proceeds = quantity * price

    account.cash_balance += proceeds
    holding.quantity -= quantity

    if holding.quantity <= 1e-9:
        await db.delete(holding)
    else:
        holding.updated_at = datetime.now(timezone.utc)

    tx = Transaction(
        account_id=account.id,
        coin_symbol=coin_symbol,
        type="SELL",
        quantity=quantity,
        price=price,
        total=proceeds
    )
    db.add(tx)

    await db.commit()

    return {
        "message": f"Successfully sold {quantity:.6f} {coin_symbol.upper()}",
        "price": price,
        "quantity": quantity,
        "total_proceeds": proceeds,
        "remaining_cash": account.cash_balance
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

    holdings_value = 0.0
    holdings_list = []
    allocation_dict = {}

    for h in holdings:
        price = await get_latest_price(request, h.coin_symbol)
        market_value = h.quantity * price
        cost_basis = h.quantity * h.average_buy_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        holdings_value += market_value
        holdings_list.append({
            "coin": h.coin_symbol.upper(),
            "quantity": h.quantity,
            "average_buy_price": h.average_buy_price,
            "current_price": price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct
        })

    total_value = account.cash_balance + holdings_value

    if total_value > 0:
        allocation_dict["CASH"] = (account.cash_balance / total_value) * 100.0
        for h_item in holdings_list:
            allocation_dict[h_item["coin"]] = (h_item["market_value"] / total_value) * 100.0
    else:
        allocation_dict["CASH"] = 100.0

    tx_query = await db.execute(
        select(Transaction).where(Transaction.account_id == account.id)
    )
    transactions = list(tx_query.scalars().all())
    realized_pnl = calculate_realized_pnl(transactions)

    total_pnl = total_value - account.initial_balance
    total_pnl_pct = (total_pnl / account.initial_balance) * 100.0

    return {
        "cash_balance": account.cash_balance,
        "holdings_value": holdings_value,
        "total_value": total_value,
        "initial_balance": account.initial_balance,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "realized_pnl": realized_pnl,
        "allocation": allocation_dict,
        "holdings": holdings_list
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
        price = await get_latest_price(request, h.coin_symbol)
        market_value = h.quantity * price
        cost_basis = h.quantity * h.average_buy_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        result.append({
            "coin": h.coin_symbol.upper(),
            "quantity": h.quantity,
            "average_buy_price": h.average_buy_price,
            "current_price": price,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "updated_at": h.updated_at
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
            "created_at": tx.created_at
        }
        for tx in transactions
    ]