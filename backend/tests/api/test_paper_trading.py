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


def _mock_db_for_account(account: PaperAccount, db: AsyncMock, exists: bool = True) -> None:
    """
    Set up the AsyncMock db to return the given account for
    get_or_create_account's pattern.
    """
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = account
    select_result.scalar_one.return_value = account

    if exists:
        db.execute.side_effect = [select_result]
    else:
        select_result_none = MagicMock()
        select_result_none.scalar_one_or_none.return_value = None
        insert_result = MagicMock()
        db.execute.side_effect = [select_result_none, insert_result, select_result]


@pytest.mark.asyncio
async def test_get_account_details_auto_creates_account() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")

    account = PaperAccount(
        id=uuid4(),
        user_id=user_id,
        cash_balance=100000.0,
        initial_balance=100000.0,
    )

    db = AsyncMock(spec=AsyncSession)
    _mock_db_for_account(account, db, exists=False)

    app = _build_paper_trading_app(current_user=mock_user, db_session=db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cash_balance"] == 100000.0
    assert data["initial_balance"] == 100000.0

    # Verify SELECT (first, returns None) + INSERT + SELECT (returns account) were called
    assert db.execute.call_count == 3
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_buy_coin_success() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")

    account = PaperAccount(
        id=uuid4(),
        user_id=user_id,
        cash_balance=10000.0,
        initial_balance=10000.0,
    )

    db = AsyncMock(spec=AsyncSession)

    # get_or_create_account: SELECT result (finds account)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = account
    select_result.scalar_one.return_value = account

    # Holding select (empty — no existing holding)
    holding_result = MagicMock()
    holding_result.scalar_one_or_none.return_value = None

    db.execute.side_effect = [select_result, holding_result]

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "50000.0"  # BTC price is 50,000

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/buy",
            json={"coin": "btc", "amount": 2000.0},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["quantity"] == pytest.approx(2000.0 / 50000.0, rel=1e-6)
    assert data["price"] == 50000.0
    assert data["remaining_cash"] == pytest.approx(8000.0, rel=1e-6)
    assert "price_source" in data  # New field — must be present

    # commit is called once: only for the trade (none in get_or_create_account since account exists)
    assert db.commit.call_count == 1


@pytest.mark.asyncio
async def test_buy_coin_insufficient_balance() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")

    account = PaperAccount(
        id=uuid4(),
        user_id=user_id,
        cash_balance=100.0,
        initial_balance=100.0,
    )

    db = AsyncMock(spec=AsyncSession)
    _mock_db_for_account(account, db)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "60000.0"

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/buy",
            json={"coin": "btc", "amount": 200.0},
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
        initial_balance=10000.0,
    )
    holding = Holding(
        account_id=account_id,
        coin_symbol="btc",
        quantity=0.04,
        average_buy_price=50000.0,
    )

    db = AsyncMock(spec=AsyncSession)

    # get_or_create_account: SELECT result (finds account)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = account
    select_result.scalar_one.return_value = account

    holding_result = MagicMock()
    holding_result.scalar_one_or_none.return_value = holding

    db.execute.side_effect = [select_result, holding_result]

    mock_redis = AsyncMock()
    mock_redis.get.return_value = "60000.0"  # BTC rose to 60k

    app = _build_paper_trading_app(current_user=mock_user, db_session=db, redis_client=mock_redis)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/paper-trading/trade/sell",
            json={"coin": "btc", "quantity": 0.02},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_proceeds"] == pytest.approx(0.02 * 60000.0, rel=1e-6)
    assert data["remaining_cash"] == pytest.approx(8000.0 + 1200.0, rel=1e-6)
    assert data["price_source"] in ("redis_cache", "coingecko_api", "mock_fallback")
    assert holding.quantity == pytest.approx(0.02, rel=1e-8)  # Remaining

    # commit is called once: only for the trade
    assert db.commit.call_count == 1


@pytest.mark.asyncio
async def test_portfolio_status() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    account_id = uuid4()

    account = PaperAccount(
        id=account_id,
        user_id=user_id,
        cash_balance=8000.0,
        initial_balance=10000.0,
    )

    db = AsyncMock(spec=AsyncSession)

    # get_or_create_account: SELECT result (finds account)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = account
    select_result.scalar_one.return_value = account

    db.execute.side_effect = [select_result]

    app = _build_paper_trading_app(current_user=mock_user, db_session=db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/portfolio")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["cash_balance"] == 8000.0
    assert data["initial_balance"] == 10000.0


@pytest.mark.asyncio
async def test_holdings_status() -> None:
    user_id = uuid4()
    mock_user = User(id=user_id, email="pt@test.com")
    account_id = uuid4()

    account = PaperAccount(
        id=account_id,
        user_id=user_id,
        cash_balance=8000.0,
        initial_balance=10000.0,
    )
    holdings = [
        Holding(
            account_id=account_id,
            coin_symbol="btc",
            quantity=0.02,
            average_buy_price=50000.0,
        )
    ]

    db = AsyncMock(spec=AsyncSession)

    # get_or_create_account: SELECT result (finds account)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = account
    select_result.scalar_one.return_value = account

    # Holdings query
    holdings_result = MagicMock()
    holdings_result.scalars.return_value.all.return_value = holdings

    db.execute.side_effect = [select_result, holdings_result]

    app = _build_paper_trading_app(current_user=mock_user, db_session=db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/paper-trading/holdings")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data) == 1
    assert data[0]["coin"] == "BTC"
    assert data[0]["quantity"] == 0.02
    assert data[0]["average_buy_price"] == 50000.0
