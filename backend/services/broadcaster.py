import asyncio
import re
from fastapi.websockets import WebSocketState
from fastapi import WebSocket, status
from redis.asyncio import Redis
from schemas.event import Event
from core.topics import AVAILABLE_TOPICS
from core.config import get_settings
from core.logger import get_logger

setting = get_settings()

log = get_logger(__name__)

class ConnectionManager:
    def __init__(self,redis:Redis):
        self._redis = redis
        self._connection:dict[str,dict[WebSocket,str]] = {}

    @property
    def redis(self) -> Redis:
        return self._redis

    async def startup(self):
        asyncio.create_task(self._listen())
        log.info("ConnectionManager started")

    async def subscribe(self,websocket:WebSocket,topic:str,user_id:str):
        self._connection.setdefault(topic,{})[websocket] = user_id
        log.info("User subscribed",user_id=user_id,topic=topic)

    async def disconnect_socket(self,websocket:WebSocket,topic:str):
        topic_connections = self._connection.get(topic,{})
        user_id = topic_connections.pop(websocket,None)
        if user_id:
            log.info("User unsubscribed",user_id=user_id,topic=topic)
        if not topic_connections:
            self._connection.pop(topic,None)

    async def disconnect_user_from_topic(self,user_id:str,topic:str):
        topic_connections = self._connection.get(topic,{})
        ws_to_remove = [ws for ws,uid in topic_connections.items() if str(uid) == str(user_id)]
        for ws in ws_to_remove:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.close(code=status.WS_1000_NORMAL_CLOSURE)
                    log.info("Closed websocket connection",user_id=user_id,topic=topic)
            except Exception as e:
                log.error("Error closing websocket",error=str(e))
            finally:
                await self.disconnect_socket(ws, topic)

    async def publish(self,topic:str,event:Event):
        await self._redis.publish(topic,event.model_dump_json())

    @staticmethod
    def _topic_keys(topic: str) -> list[str]:
        keys = [topic]
        parts = topic.split(".")
        if len(parts) > 1:
            for i in range(len(parts) - 1, 0, -1):
                keys.append(".".join(parts[:i]))
        root = re.split(r"[:.]", topic, maxsplit=1)[0]
        if root not in keys:
            keys.append(root)
        return keys

    async def _listen(self):
        pubsub = self._redis.pubsub()
        channels = [topic.name for topic in AVAILABLE_TOPICS]
        patterns = [f"{topic.name}.*" for topic in AVAILABLE_TOPICS]
        await pubsub.subscribe(*channels)
        await pubsub.psubscribe(*patterns)
        log.info("Subscribed to Redis channels and patterns", channels=channels, patterns=patterns)
        async for message in pubsub.listen():
            if message["type"] not in ["message", "pmessage"]:
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
        target_connections: dict[WebSocket, str] = {}
        keys = self._topic_keys(topic)
        for key in keys:
            target_connections.update(self._connection.get(key, {}))

        if not target_connections:
            log.info("No active connections for topic",topic=topic)
            return
        payload = event.model_dump(mode="json")

        websockets= list(target_connections.keys())
        tasks=[ws.send_json(payload) for ws in websockets]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i ,res in enumerate(results):
            if isinstance(res, Exception):
                ws=websockets[i]
                log.error("Broadcast failed for socket",error=str(ws),topic=event.topic)
                for key in keys:
                    await self.disconnect_socket(ws, key)

    async def cleanup_dead_connections(self):
        for topic in list(self._connection.keys()):
            topic_connections = self._connection.get(topic,{})
            dead = []
            for ws in list(topic_connections.keys()):
                if ws.client_state != WebSocketState.CONNECTED:
                    dead.append(ws)
                    continue

                try:
                    await ws.send_json({"type":"ping"})
                except Exception as e:
                    dead.append(ws)
            for ws in dead:
                await self.disconnect_socket(ws, topic)
