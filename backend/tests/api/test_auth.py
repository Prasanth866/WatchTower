from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

import api.auth as auth_module
from api.auth import router as auth_router
from core.dependencies import get_current_user, get_db
from core.rate_limiter import limiter


class _FakeDB:
	def __init__(self) -> None:
		self.committed = False
		self.refreshed = False

	async def commit(self) -> None:
		self.committed = True

	async def refresh(self, _obj) -> None:
		self.refreshed = True


def _build_auth_app(*, db: _FakeDB, current_user=None) -> FastAPI:
	app = FastAPI()
	app.include_router(auth_router, prefix="/api/v1/auth")
	app.state.limiter = limiter
	app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
	app.add_middleware(SlowAPIMiddleware)

	async def _get_db_override():
		yield db

	app.dependency_overrides[get_db] = _get_db_override

	if current_user is not None:
		async def _get_current_user_override():
			return current_user

		app.dependency_overrides[get_current_user] = _get_current_user_override

	return app


@pytest.mark.asyncio
async def test_register_rate_limit_enforced(monkeypatch) -> None:
	limiter._storage.reset()
	db = _FakeDB()
	app = _build_auth_app(db=db)

	async def _fake_register_user(*, db, email, password_hash):
		_ = db
		_ = password_hash
		return SimpleNamespace(id=uuid4(), email=email, created_at=datetime.now(timezone.utc))

	monkeypatch.setattr(auth_module, "register_user", _fake_register_user)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		for i in range(5):
			response = await client.post(
				"/api/v1/auth/register",
				json={"email": f"user{i}@watchtower.dev", "password": "StrongPass1!"},
			)
			assert response.status_code == status.HTTP_200_OK

		limited = await client.post(
			"/api/v1/auth/register",
			json={"email": "user5@watchtower.dev", "password": "StrongPass1!"},
		)

	assert limited.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_login_rate_limit_enforced(monkeypatch) -> None:
	limiter._storage.reset()
	db = _FakeDB()
	app = _build_auth_app(db=db)

	async def _fake_authenticate_user(db, email, password):
		_ = db
		_ = email
		_ = password
		return SimpleNamespace(id=uuid4())

	monkeypatch.setattr(auth_module, "authenticate_user", _fake_authenticate_user)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		for _ in range(10):
			response = await client.post(
				"/api/v1/auth/login",
				data={"username": "user@watchtower.dev", "password": "StrongPass1!"},
			)
			assert response.status_code == status.HTTP_200_OK

		limited = await client.post(
			"/api/v1/auth/login",
			data={"username": "user@watchtower.dev", "password": "StrongPass1!"},
		)

	assert limited.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_notifications_patch_updates_preference() -> None:
	limiter._storage.reset()
	db = _FakeDB()
	user = SimpleNamespace(email_notifications=True)
	app = _build_auth_app(db=db, current_user=user)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		response = await client.patch(
			"/api/v1/auth/notifications",
			json={"email_notifications": False},
		)

	assert response.status_code == status.HTTP_200_OK
	assert response.json() == {"email_notifications": False}
	assert db.committed is True
	assert db.refreshed is True
	assert user.email_notifications is False


@pytest.mark.asyncio
async def test_notifications_requires_auth() -> None:
	limiter._storage.reset()
	db = _FakeDB()
	app = _build_auth_app(db=db)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		response = await client.patch(
			"/api/v1/auth/notifications",
			json={"email_notifications": False},
		)

	assert response.status_code == status.HTTP_401_UNAUTHORIZED
