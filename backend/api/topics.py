from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class TopicInfo(BaseModel):
    name: str
    description: str | None = None
    unit: str
    interval_seconds : int

AVAILABLE_TOPICS:list[TopicInfo] = [
    TopicInfo(name="crypto",description="Live BTC/ETH prices",unit="USD",interval_seconds=10),
    TopicInfo(name="f1",description="F1 lap telemetry",unit="ms",interval_seconds=5)
]

@router.get("/", response_model=list[TopicInfo])
async def list_topics():
    return AVAILABLE_TOPICS