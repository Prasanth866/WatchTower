import os
import asyncio
import structlog
from fastapi import WebSocket
from redis.asyncio import Redis
from schemas.event import Event
from api.topics import AVAILABLE_TOPICS

log = structlog.get_logger()

REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379")

class ConnectionManager:
    def __init__(self,redis:Redis):
        self._redis = redis
        self._connection:dict[str,dict[WebSocket,str]] = {}

    async def startup(self):
        asyncio.create_task(self._listen())
        log.info("ConnectionManager started")

    async def subscribe(self,websocket:WebSocket,topic:str,user_id:str):
        self._connection.setdefault(topic,{})[websocket] = user_id
        log.info("User subscribed",user_id=user_id,topic=topic)

    async def disconnect_user(self,websocket:WebSocket,topic:str):
        topic_connections = self._connection.get(topic,{})
        user_id = topic_connections.pop(websocket,None)
        if user_id:
            log.info("User disconnected",user_id=user_id,topic=topic)
        if not topic_connections:
            self._connection.pop(topic,None)

    async def publish(self,topic:str,event:Event):
        await self._redis.publish(topic,event.model_dump_json())

    async def _listen(self):
        pubsub = self._redis.pubsub()
        channels = [topic.name for topic in AVAILABLE_TOPICS]
        await pubsub.subscribe(*channels)
        log.info("Subscribed to Redis channels",channels=channels)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                topic = message["channel"]
                if isinstance(topic, bytes):
                    topic = topic.decode()
                event= Event.model_validate_json(message["data"])
                await self._broadcast(topic,event)
            except Exception as e:
                log.error("Error processing message",error=str(e))
                continue
    async def _broadcast(self,topic:str,event:Event):
        connections=self._connection.get(topic,{})
        log.info("Broadcasting event",topic=topic,connection_count=len(connections))
        dead=set()
        for ws in list(connections):
            try:
                await ws.send_json(event.model_dump(mode="json"))
                log.info('send to websocket',topic=topic)
            except Exception as e:
                log.error("Error sending message to websocket",error=str(e))
                dead.add(ws)

        for ws in dead:
            self._connection.get(topic,{}).pop(ws,None)
        if not self._connection.get(topic):
            self._connection.pop(topic,None)