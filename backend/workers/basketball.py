from datetime import datetime,timezone
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

    async def fetch(self) -> Event:
        today = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
        headers = {"Authorization": self.api_key}
        params = {"dates[]":today}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.url,headers=headers, params=params,timeout= 10)
                if response.status_code == 429:
                    raise Exception("API rate limit exceeded")
                response.raise_for_status()
                data = response.json().get("data", [])
            except httpx.HTTPError as e:
                raise Exception(f"Error fetching basketball data: {e}")
        live_games = [game for game in data if 'Qtr' in game['status'] or 'Half' in game['status']]
        return  Event(
                    topic=self.topic,
                    value=float(len(live_games)),
                    unit="live_games_count",
                    metadata={
                        "total_games_today": len(data),
                        "games":[
                            {
                                "matchup":f"{game['visitor_team']['abbreviation']} @ {game['home_team']['abbreviation']}",
                                "score":f"{game['visitor_team_score']} - {game['home_team_score']}",
                                "status":game['status'],
                                "id":game['id'],
                            } for game in live_games
                        ],
                        "provider":"balldontlie",
                        "last_updated":datetime.now(timezone.utc).isoformat()
                    }
                )