from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from api.admin import router as admin_router
from core.dependencies import get_admin_user, get_current_user, get_db


class _StatsDB:
    def __init__(self, values: list[int]):
        self._values = iter(values)

    async def scalar(self, _query):
        return next(self._values)


class _UserDB:
    def __init__(self, users: dict):
        self.users = users
        self.committed = False
        self.refreshed = False

    async def get(self, _model, user_id):
        return self.users.get(user_id)

    async def commit(self):
        self.committed = True

    async def refresh(self, _user):
        self.refreshed = True


def _build_app(fake_db, admin_user, manager=None) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1/admin")

    async def _get_db_override():
        yield fake_db

    async def _get_admin_override():
        return admin_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_admin_user] = _get_admin_override
    app.state.manager = manager or SimpleNamespace(get_connection_counts=lambda: {})
    return app


@pytest.mark.asyncio
async def test_get_admin_user_denies_non_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_admin_user(current_user=SimpleNamespace(is_admin=False))
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_get_admin_user_allows_admin() -> None:
    user = SimpleNamespace(is_admin=True)
    result = await get_admin_user(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_admin_stats_returns_403_for_non_admin_user() -> None:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1/admin")

    async def _get_db_override():
        yield _StatsDB([0, 0, 0, 0, 0])

    async def _get_current_user_override():
        return SimpleNamespace(id=uuid4(), is_admin=False)

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override
    app.state.manager = SimpleNamespace(get_connection_counts=lambda: {})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/stats")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Admin access required"


@pytest_asyncio.fixture
async def stats_client():
    app = _build_app(
        fake_db=_StatsDB([10, 20, 30, 15, 2]),
        admin_user=SimpleNamespace(id=uuid4(), is_admin=True),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_admin_stats_returns_counts(stats_client: AsyncClient) -> None:
    response = await stats_client.get("/api/v1/admin/stats")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "total_users": 10,
        "total_subscriptions": 20,
        "total_triggers": 30,
        "active_triggers": 15,
        "pending_emails": 2,
    }


@pytest.mark.asyncio
async def test_admin_connections_returns_manager_counts() -> None:
    manager = SimpleNamespace(get_connection_counts=lambda: {"crypto:btc": 3, "basketball:nba": 1})
    app = _build_app(
        fake_db=_StatsDB([0, 0, 0, 0, 0]),
        admin_user=SimpleNamespace(id=uuid4(), is_admin=True),
        manager=manager,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/connections")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"crypto:btc": 3, "basketball:nba": 1}


@pytest.mark.asyncio
async def test_toggle_admin_rejects_self_modification() -> None:
    admin_id = uuid4()
    app = _build_app(
        fake_db=_UserDB({}),
        admin_user=SimpleNamespace(id=admin_id, is_admin=True),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/api/v1/admin/users/{admin_id}/toggle-admin")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Cannot modify your own admin status"


@pytest.mark.asyncio
async def test_toggle_admin_flips_flag_and_commits() -> None:
    admin_id = uuid4()
    target_id = uuid4()
    target_user = SimpleNamespace(
        id=target_id,
        is_admin=False,
        email="user@test.dev",
        email_notifications=True,
        created_at=datetime.now(timezone.utc),
    )
    fake_db = _UserDB({target_id: target_user})
    app = _build_app(
        fake_db=fake_db,
        admin_user=SimpleNamespace(id=admin_id, is_admin=True),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(f"/api/v1/admin/users/{target_id}/toggle-admin")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_admin"] is True
    assert fake_db.committed is True
    assert fake_db.refreshed is True