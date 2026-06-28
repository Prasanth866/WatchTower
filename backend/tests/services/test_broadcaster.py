import pytest
from services.broadcaster import ConnectionManager


class _DummyRedis:
    async def publish(self, *_args, **_kwargs):
        return 1


def test_topic_keys_include_hierarchy_and_root() -> None:
    keys = ConnectionManager._topic_keys("crypto:eth.price")
    assert keys[0] == "crypto:eth.price"
    assert "crypto:eth" in keys
    assert "crypto" in keys


def test_connection_counts_returns_per_topic_counts() -> None:
    manager = ConnectionManager(_DummyRedis())
    manager._connection = {
        "crypto:btc": {object(): "u1", object(): "u2"},
        "crypto:eth": {object(): "u3"},
    }

    counts = manager.get_connection_counts()
    assert counts == {"crypto:btc": 2, "crypto:eth": 1}


@pytest.mark.asyncio
async def test_is_user_connected_matches_parent_topic_for_subtopic_event() -> None:
    manager = ConnectionManager(_DummyRedis())
    manager._connection = {
        "crypto:eth": {object(): "u3"},
    }

    assert await manager.is_user_connected("u3", "crypto:eth.price") is True


def test_side_effect_runtime_reports_writer_stats() -> None:
    class _Writer:
        queue_size = 12
        dropped_events = 3

    manager = ConnectionManager(_DummyRedis(), event_log_writer=_Writer())

    stats = manager.side_effect_runtime()

    assert stats["active_tasks"] == 0
    assert stats["queue_size"] == 12
    assert stats["dropped_events"] == 3


@pytest.mark.asyncio
async def test_is_user_connected_checks_redis_fallback() -> None:
    class _MockRedis:
        async def hgetall(self, key):
            if key == "watchtower:user:u4:topics":
                return {"crypto:eth": "1"}
            return {}

    manager = ConnectionManager(_MockRedis())
    manager._connection = {}
    
    assert await manager.is_user_connected("u4", "crypto:eth.price") is True
    assert await manager.is_user_connected("u4", "crypto:btc") is False


@pytest.mark.asyncio
async def test_send_user_alert_sends_to_ws() -> None:
    class _MockWS:
        def __init__(self):
            self.sent_payloads = []
            
        async def send_json(self, payload):
            self.sent_payloads.append(payload)

    ws1 = _MockWS()
    ws2 = _MockWS()
    
    manager = ConnectionManager(_DummyRedis())
    manager._connection = {
        "crypto:eth": {ws1: "u1"},
        "crypto:btc": {ws2: "u2"}
    }
    
    payload = {"type": "alert", "trigger_id": "t1"}
    await manager.send_user_alert("u1", "crypto:eth", payload)
    
    assert len(ws1.sent_payloads) == 1
    assert ws1.sent_payloads[0] == payload
    assert len(ws2.sent_payloads) == 0
