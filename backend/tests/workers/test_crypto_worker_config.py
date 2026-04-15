import pytest

from core.topics import VALID_TOPICS
from workers.crypto import CryptoWorker


class _DummyRedis:
    async def publish(self, *_args, **_kwargs):
        return 1


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"price": "3210.55"}}


class _FakeClient:
    async def get(self, *_args, **_kwargs):
        return _FakeResponse()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_crypto_worker_uses_configured_symbol_and_coin() -> None:
    worker = CryptoWorker(
        manager=_DummyRedis(),
        topic="crypto:ethereum",
        symbol="ETH-USDT",
        coin_name="ethereum",
    )
    worker.client = _FakeClient()

    event = await worker.fetch()

    assert event.topic == "crypto:ethereum"
    assert event.value == 3210.55
    assert event.metadata["coin"] == "ethereum"


def test_ethereum_topic_is_available_for_subscriptions_and_triggers() -> None:
    assert "crypto:ethereum" in VALID_TOPICS