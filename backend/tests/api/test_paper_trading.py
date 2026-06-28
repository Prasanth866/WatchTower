import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.paper_trading_router import router as paper_trading_router
from core.dependencies import get_current_user, get_db
from models.user import User
from models.paper_trading import PaperAccount, Holding, Transaction


class _FakeManager:
    def __init__(self, redis) -> None:
        self.redis = redis


def _build_paper_trading_app(*, current_user=None, db_session=None, redis_client=None) -> FastAPI:
    app = FastAPI()
    app.include_router(paper_trading_router, prefix="/api/v1/paper-trading")

    if current_user is not None:
        async def _get_current_user_override():
            return current_user
        app.dependency_overrides[get_current_user] = _get_current_user_override

    if db_session is not None:
        async def _get_db_override():
            yield db_session
        app.dependency_overrides[get_db] = _get_db_override

    app.state.manager = _FakeManager(redis_client)
    return app


@pytest.mark.asyncio
async def test_get_account_details_auto_creates_account() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    
    # Mock DB returns no account initially, then returns the created account
    db = AsyncMock(spec=AsyncSession)
    
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    db.execute.return_value = db_result

    app = _build_paper_trading_app(current_user=mock_user, db_session=db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cash_balance"] == 100000.0
    assert data["initial_balance"] == 100000.0
    
    # Verify account was added to DB and committed
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_buy_coin_success() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    
    account = PaperAccount(
        id=uuid4(),
        user_id=user_id,
        cash_balance=10000.0,
        initial_balance=10000.0
    )

    db = AsyncMock(spec=AsyncSession)
    
    # Mocking Account select, then Holding select (empty)
    mock_account_result = MagicMock()
    mock_account_result.scalar_one_or_none.return_value = account
    
    mock_holding_result = MagicMock()
    mock_holding_result.scalar_one_or_none.return_value = None
    
    db.execute.side_effect = [mock_account_result, mock_holding_result]

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "50000.0"  # BTC price is 50,000

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/buy",
            json={"coin": "btc", "amount": 2000.0}
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["quantity"] == 2000.0 / 50000.0
    assert data["price"] == 50000.0
    assert data["remaining_cash"] == 8000.0

    # Ensure details were committed to db
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_buy_coin_insufficient_balance() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    
    account = PaperAccount(
        id=uuid4(),
        user_id=user_id,
        cash_balance=100.0,
        initial_balance=100.0
    )

    db = AsyncMock(spec=AsyncSession)
    mock_account_result = MagicMock()
    mock_account_result.scalar_one_or_none.return_value = account
    db.execute.return_value = mock_account_result

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "60000.0"

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/buy",
            json={"coin": "btc", "amount": 200.0}
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Insufficient cash balance" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sell_coin_success() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    account_id = uuid4()
    
    account = PaperAccount(
        id=account_id,
        user_id=user_id,
        cash_balance=8000.0,
        initial_balance=10000.0
    )
    holding = Holding(
        account_id=account_id,
        coin_symbol="btc",
        quantity=0.04,
        average_buy_price=50000.0
    )

    db = AsyncMock(spec=AsyncSession)
    
    mock_account_result = MagicMock()
    mock_account_result.scalar_one_or_none.return_value = account
    
    mock_holding_result = MagicMock()
    mock_holding_result.scalar_one_or_none.return_value = holding
    
    db.execute.side_effect = [mock_account_result, mock_holding_result]

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "60000.0"  # BTC rose to 60k

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/sell",
            json={"coin": "btc", "quantity": 0.02}
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_proceeds"] == 0.02 * 60000.0
    assert data["remaining_cash"] == 8000.0 + 1200.0
    assert holding.quantity == 0.02  # Remaining

    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_portfolio_valuation() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    account_id = uuid4()
    
    account = PaperAccount(
        id=account_id,
        user_id=user_id,
        cash_balance=8000.0,
        initial_balance=10000.0
    )
    holdings = [
        Holding(
            account_id=account_id,
            coin_symbol="btc",
            quantity=0.02,
            average_buy_price=50000.0
        )
    ]
    transactions = [
        Transaction(
            account_id=account_id,
            coin_symbol="btc",
            type="BUY",
            quantity=0.02,
            price=50000.0,
            total=1000.0
        )
    ]

    db = AsyncMock(spec=AsyncSession)
    
    # 1. get_or_create_account select
    mock_account_result = MagicMock()
    mock_account_result.scalar_one_or_none.return_value = account
    
    # 2. Holdings query
    mock_holdings_result = MagicMock()
    mock_holdings_result.scalars.return_value.all.return_value = holdings
    
    # 3. Transactions query
    mock_txs_result = MagicMock()
    mock_txs_result.scalars.return_value.all.return_value = transactions
    
    db.execute.side_effect = [mock_account_result, mock_holdings_result, mock_txs_result]

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "60000.0"  # BTC is 60k

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/portfolio")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # 8000 (cash) + 0.02 * 60000 (1200) = 9200
    assert data["total_value"] == 9200.0
    assert data["total_pnl"] == -800.0  # initial was 10000
    assert data["holdings"][0]["unrealized_pnl"] == 200.0  # 1200 (market) - 1000 (cost)
