import asyncio
from datetime import datetime, timezone
from typing import Any


class WorkerStatusRegistry:
    def __init__(self) -> None:
        self._enabled = True
        self._workers: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    async def _set(
        self,
        name: str,
        status: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "status": status,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if details:
            payload["details"] = details
        async with self._lock:
            self._workers[name] = payload

    # ------------------------------------------------------------------
    # Public mark helpers — all async so callers await them.
    # The sync-looking names are kept for back-compat; callers that were
    # previously calling them without await must be updated to `await`.
    # ------------------------------------------------------------------

    async def mark_starting(
        self,
        name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._set(name, "starting", message, details)

    async def mark_healthy(
        self,
        name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._set(name, "ok", message, details)

    async def mark_degraded(
        self,
        name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._set(name, "degraded", message, details)

    async def mark_stopped(
        self,
        name: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self._set(name, "stopped", message, details)

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            workers_copy = dict(self._workers)

        if not self._enabled:
            return {
                "enabled": False,
                "overall": "disabled",
                "workers": workers_copy,
            }

        states = [item.get("status") for item in workers_copy.values()]
        if not states:
            overall = "starting"
        elif any(state == "degraded" for state in states):
            overall = "degraded"
        elif any(state == "starting" for state in states):
            overall = "starting"
        elif all(state == "stopped" for state in states):
            overall = "stopped"
        else:
            overall = "ok"

        return {
            "enabled": True,
            "overall": overall,
            "workers": workers_copy,
        }
