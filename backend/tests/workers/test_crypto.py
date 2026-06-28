import pytest
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
            "ethereum": {"usd": 3410.2},
            "solana": {"usd": 140.55},
        }


class _FakeClient:
    async def get(self, *_args, **_kwargs):
        return _FakeResponse()

    async def aclose(self):
        return None


@pytest.mark.asyncio
async def test_coingecko_fetch_maps_all_coins() -> None:
    worker = CryptoWorker(
        manager=_DummyRedis(),
        interval=15,
    )
    worker.client = _FakeClient()

    events = await worker.fetch()

    # The mapping has 7 coins defined. 3 of them are mock-returned here.
    assert len(events) == 3

    btc = next(e for e in events if e.topic == "crypto:btc")
    assert btc.value == 61250.5
    assert btc.metadata["coin"] == "bitcoin"

    sol = next(e for e in events if e.topic == "crypto:sol")
    assert sol.value == 140.55
    assert sol.metadata["coin"] == "solana"
