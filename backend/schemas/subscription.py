from pydantic import BaseModel


class TopicSubscriptionRead(BaseModel):
    topic: str


class TopicSubscriptionActionResponse(BaseModel):
    message: str
