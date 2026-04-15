from services.broadcaster import ConnectionManager


class _DummyRedis:
    async def publish(self, *_args, **_kwargs):
        return 1


def test_topic_keys_include_hierarchy_and_root() -> None:
    keys = ConnectionManager._topic_keys("basketball:nba.123.BOS")
    assert keys[0] == "basketball:nba.123.BOS"
    assert "basketball:nba.123" in keys
    assert "basketball:nba" in keys
    assert "basketball" in keys


def test_connection_counts_returns_per_topic_counts() -> None:
    manager = ConnectionManager(_DummyRedis())
    manager._connection = {
        "crypto:btc": {object(): "u1", object(): "u2"},
        "basketball:nba": {object(): "u3"},
    }

    counts = manager.get_connection_counts()
    assert counts == {"crypto:btc": 2, "basketball:nba": 1}


def test_is_user_connected_matches_parent_topic_for_subtopic_event() -> None:
    manager = ConnectionManager(_DummyRedis())
    manager._connection = {
        "basketball:nba": {object(): "u3"},
    }

    assert manager.is_user_connected("u3", "basketball:nba.123.BOS") is True
