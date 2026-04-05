from datetime import datetime, timezone
import httpx
from schemas.event import Event
from workers.base import AbstractWorker
from services.broadcaster import ConnectionManager
from core.config import get_settings

class BasketballWorker(AbstractWorker):
    def __init__(self, manager: ConnectionManager, topic: str, interval: int = 60):
        self.api_key = get_settings().BASKETBALL_API_KEY
        self.url = "https://api.balldontlie.io/v1/games"
        super().__init__(manager, topic, interval)

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
        live_games = [game for game in data if 'Qtr' in game['status'] or 'Half' in game['status']]
        all_events = []
        for game in live_games:
            all_events.append(Event(
                        topic=f"{self.topic}.{game['id']}.{game['home_team']['abbreviation']}",
                        value=float(game['home_team_score']), 
                        unit="points", 
                        metadata={
                            "team": game['home_team']['full_name'], 
                            "opponent": game['visitor_team']['full_name'], 
                            "opponent_score": game['visitor_team_score'], 
                            "status": game['status'],
                            "game_id": game['id']
                        }
                    ))
            all_events.append(Event(
                        topic=f"{self.topic}.{game['id']}.{game['visitor_team']['abbreviation']}",
                        value=float(game['visitor_team_score']), 
                        unit='points', 
                        metadata={
                            "team": game['visitor_team']['full_name'],
                            "opponent": game['home_team']['full_name'],
                            "opponent_score": game['home_team_score'], 
                            "status": game['status'], 
                            'game_id': game['id']
                        }
                    ))
        return all_events