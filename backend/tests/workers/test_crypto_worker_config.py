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
        return {
            "bitcoin": {"usd": 61250.5},
            "ethereum": {"usd": 3410.2}
        }


class _FakeClient:
    async def get(self, *_args, **_kwargs):
        return _FakeResponse()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_crypto_worker_fetches_multiple_coins_from_coingecko() -> None:
    worker = CryptoWorker(
        manager=_DummyRedis(),
        interval=15,
    )
    worker.client = _FakeClient()

    events = await worker.fetch()

    assert len(events) == 2
    btc_event = next(e for e in events if e.topic == "crypto:btc")
    assert btc_event.value == 61250.5
    assert btc_event.metadata["coin"] == "bitcoin"
    assert btc_event.metadata["source"] == "coingecko"

    eth_event = next(e for e in events if e.topic == "crypto:eth")
    assert eth_event.value == 3410.2
    assert eth_event.metadata["coin"] == "ethereum"


def test_crypto_topics_are_available_in_valid_topics() -> None:
    assert "crypto:btc" in VALID_TOPICS
    assert "crypto:eth" in VALID_TOPICS
    assert "wiki:recent_changes" not in VALID_TOPICS