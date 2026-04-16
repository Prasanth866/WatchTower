"""Helpers for normalizing PostgreSQL URLs across runtime and migrations."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def to_asyncpg_database_url(database_url: str) -> str:
    """Convert incoming PostgreSQL URL into an asyncpg-compatible SQLAlchemy URL.

    Cloud providers often append libpq-specific params (for example `sslmode`
    and `channel_binding`). SQLAlchemy forwards query args to asyncpg as keyword
    arguments, so we normalize unsupported keys here.
    """

    normalized = database_url.strip()
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

    split = urlsplit(normalized)
    query_items = parse_qsl(split.query, keep_blank_values=True)

    has_ssl_key = any(key.lower() == "ssl" for key, _ in query_items)
    rebuilt_query: list[tuple[str, str]] = []

    for key, value in query_items:
        lowered = key.lower()

        if lowered == "channel_binding":
            continue

        if lowered == "sslmode":
            if not has_ssl_key:
                rebuilt_query.append(("ssl", value))
            continue

        rebuilt_query.append((key, value))

    return urlunsplit(
        (split.scheme, split.netloc, split.path, urlencode(rebuilt_query, doseq=True), split.fragment)
    )


def to_sync_database_url(database_url: str) -> str:
    """Convert async SQLAlchemy PostgreSQL URL to sync-style URL."""

    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
