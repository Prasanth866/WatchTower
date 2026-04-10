"""API endpoints for managing and retrieving information about topics."""
from fastapi import APIRouter
from core.topics import AVAILABLE_TOPICS, TopicInfo

router = APIRouter()

@router.get("/", response_model=list[TopicInfo])
async def list_topics():
    """Endpoint to retrieve a list of all available topics."""
    return AVAILABLE_TOPICS
