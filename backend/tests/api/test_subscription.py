from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

import api.subscription as subscription_module
from api.subscription import router as subscription_router
from core.dependencies import get_current_user, get_db


class _FakeDB:
	pass


class _FakeManager:
	def __init__(self) -> None:
		self.disconnected: list[tuple[str, str]] = []

	async def disconnect_user_from_topic(self, user_id: str, topic: str) -> None:
		self.disconnected.append((user_id, topic))


def _build_subscription_app(*, db: _FakeDB, current_user=None, manager=None) -> FastAPI:
	app = FastAPI()
	app.include_router(subscription_router, prefix="/api/v1/subscriptions")

	async def _get_db_override():
		yield db

	app.dependency_overrides[get_db] = _get_db_override
	if current_user is not None:
		async def _get_current_user_override():
			return current_user

		app.dependency_overrides[get_current_user] = _get_current_user_override

	app.state.manager = manager or _FakeManager()
	return app


@pytest.mark.asyncio
async def test_list_subscriptions_returns_current_user_topics(monkeypatch) -> None:
	user_id = uuid4()
	app = _build_subscription_app(
		db=_FakeDB(),
		current_user=SimpleNamespace(id=user_id),
	)

	async def _fake_list_subscriptions(_db, current_user_id):
		assert current_user_id == user_id
		return ["crypto:btc", "basketball:nba"]

	monkeypatch.setattr(subscription_module, "list_subscriptions_for_user", _fake_list_subscriptions)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		response = await client.get("/api/v1/subscriptions/")

	assert response.status_code == status.HTTP_200_OK
	assert response.json() == ["crypto:btc", "basketball:nba"]


@pytest.mark.asyncio
async def test_subscribe_to_topic_returns_created_with_message(monkeypatch) -> None:
	user_id = uuid4()
	app = _build_subscription_app(
		db=_FakeDB(),
		current_user=SimpleNamespace(id=user_id),
	)
	captured: dict[str, object] = {}

	async def _fake_subscribe(_db, current_user_id, topic):
		captured["user_id"] = current_user_id
		captured["topic"] = topic

	monkeypatch.setattr(subscription_module, "subscribe_user_to_topic", _fake_subscribe)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		response = await client.post("/api/v1/subscriptions/crypto:btc")

	assert response.status_code == status.HTTP_201_CREATED
	assert response.json() == {"message": "Subscribed to crypto:btc"}
	assert captured == {"user_id": user_id, "topic": "crypto:btc"}


@pytest.mark.asyncio
async def test_unsubscribe_disconnects_user_topic_and_returns_no_content(monkeypatch) -> None:
	user_id = uuid4()
	manager = _FakeManager()
	app = _build_subscription_app(
		db=_FakeDB(),
		current_user=SimpleNamespace(id=user_id),
		manager=manager,
	)
	captured: dict[str, object] = {}

	async def _fake_unsubscribe(_db, current_user_id, topic):
		captured["user_id"] = current_user_id
		captured["topic"] = topic

	monkeypatch.setattr(subscription_module, "unsubscribe_user_from_topic", _fake_unsubscribe)

	async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
		response = await client.delete("/api/v1/subscriptions/crypto:btc")

	assert response.status_code == status.HTTP_204_NO_CONTENT
	assert captured == {"user_id": user_id, "topic": "crypto:btc"}
	assert manager.disconnected == [(str(user_id), "crypto:btc")]
