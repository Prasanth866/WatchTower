from datetime import datetime, timezone
import httpx
from core.worker_status import WorkerStatusRegistry
from schemas.event import Event
from workers.base import AbstractWorker
from services.broadcaster import ConnectionManager
from core.config import get_settings

class BasketballWorker(AbstractWorker):
    def __init__(
        self,
        manager: ConnectionManager,
        topic: str,
        interval: int = 60,
        status_registry: WorkerStatusRegistry | None = None,
    ):
        self.api_key = get_settings().BASKETBALL_API_KEY
        self.url = "https://api.balldontlie.io/v1/games"
        super().__init__(manager, topic, interval, status_registry=status_registry)


    async def fetch(self) -> list[Event]:
        today = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
        headers = {"Authorization": self.api_key}
        params = {"dates[]": today}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.url, headers=headers, params=params, timeout=10)
                if response.status_code == 429:
                    raise Exception("API rate limit exceeded")
                response.raise_for_status()
                data = response.json().get("data", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching basketball data: {e}")
        live_games = [
            game
            for game in data
            if "Qtr" in (game.get("status") or "") or "Half" in (game.get("status") or "")
        ]
        all_events = []
        for game in live_games:
            home_team = game.get("home_team") or {}
            visitor_team = game.get("visitor_team") or {}
            game_id = game.get("id")
            if game_id is None:
                continue

            home_score = game.get("home_team_score")
            visitor_score = game.get("visitor_team_score")

            try:
                home_value = float(home_score if home_score is not None else 0)
                visitor_value = float(visitor_score if visitor_score is not None else 0)
            except (TypeError, ValueError):
                continue

            all_events.append(Event(
                        topic=f"{self.topic}.{game_id}.{home_team.get('abbreviation', 'HOME')}",
                        value=home_value,
                        unit="points", 
                        metadata={
                            "team": home_team.get("full_name", "Unknown Team"),
                            "opponent": visitor_team.get("full_name", "Unknown Team"),
                            "opponent_score": visitor_score if visitor_score is not None else 0,
                            "status": game.get("status", "Unknown"),
                            "game_id": game_id
                        }
                    ))
            all_events.append(Event(
                        topic=f"{self.topic}.{game_id}.{visitor_team.get('abbreviation', 'AWAY')}",
                        value=visitor_value,
                        unit='points', 
                        metadata={
                            "team": visitor_team.get("full_name", "Unknown Team"),
                            "opponent": home_team.get("full_name", "Unknown Team"),
                            "opponent_score": home_score if home_score is not None else 0,
                            "status": game.get("status", "Unknown"),
                            "game_id": game_id
                        }
                    ))
        return all_events