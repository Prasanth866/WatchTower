import asyncio
import os

import httpx


async def check_health() -> None:
    base_url = os.getenv("WATCHTOWER_BASE_URL", "http://localhost:8000")
    url = f"{base_url.rstrip('/')}/api/v1/health"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(check_health())