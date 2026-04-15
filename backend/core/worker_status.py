from datetime import datetime, timezone
from typing import Any


class WorkerStatusRegistry:
    def __init__(self) -> None:
        self._enabled = True
        self._workers: dict[str, dict[str, Any]] = {}

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _set(self, name: str, status: str, message: str | None = None) -> None:
        self._workers[name] = {
            "status": status,
            "message": message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def mark_starting(self, name: str, message: str | None = None) -> None:
        self._set(name, "starting", message)

    def mark_healthy(self, name: str, message: str | None = None) -> None:
        self._set(name, "ok", message)

    def mark_degraded(self, name: str, message: str | None = None) -> None:
        self._set(name, "degraded", message)

    def mark_stopped(self, name: str, message: str | None = None) -> None:
        self._set(name, "stopped", message)

    def snapshot(self) -> dict[str, Any]:
        if not self._enabled:
            return {
                "enabled": False,
                "overall": "disabled",
                "workers": dict(self._workers),
            }

        states = [item.get("status") for item in self._workers.values()]
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
            "workers": dict(self._workers),
        }
