from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class TopicInfo(BaseModel):
    name: str
    description: str | None = None
    unit: str
    interval_seconds : int

AVAILABLE_TOPICS:list[TopicInfo] = [
    TopicInfo(name="crypto",description="Live BTC prices",unit="USD",interval_seconds=15),
    TopicInfo(name="basketball",description="Live NBA scores",unit="No of matches",interval_seconds=60)
]

@router.get("/", response_model=list[TopicInfo])
async def list_topics():
    return AVAILABLE_TOPICS