from fastapi import APIRouter
from core.topics import AVAILABLE_TOPICS, TopicInfo

router = APIRouter()

@router.get("/", response_model=list[TopicInfo])
async def list_topics():
    return AVAILABLE_TOPICS