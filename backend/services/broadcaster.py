import asyncio
import re
from contextlib import suppress
from fastapi.websockets import WebSocketState
from fastapi import WebSocket, status
from redis.asyncio import Redis
from schemas.event import Event
from core.topics import AVAILABLE_TOPICS
from core.config import get_settings
from core.logger import get_logger
from services.event_processing_service import process_event_side_effects

setting = get_settings()

log = get_logger(__name__)

class ConnectionManager:
    def __init__(self,redis:Redis):
        self._redis = redis
        self._connection:dict[str,dict[WebSocket,str]] = {}
        self._listen_task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()
        self._side_effect_limit = max(1, int(getattr(setting, "SIDE_EFFECT_CONCURRENCY", 16)))
        self._side_effect_semaphore = asyncio.Semaphore(self._side_effect_limit)
        self._send_timeout_seconds = float(getattr(setting, "WEBSOCKET_SEND_TIMEOUT_SECONDS", 2.0))

    @property
    def redis(self) -> Redis:
        return self._redis

    async def startup(self):
        self._listen_task = asyncio.create_task(self._listen())
        log.info("ConnectionManager started")

    async def shutdown(self):
        if self._listen_task:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        if self._background_tasks:
            for task in list(self._background_tasks):
                task.cancel()
            await asyncio.gather(*list(self._background_tasks), return_exceptions=True)
            self._background_tasks.clear()

    def _track_background_task(self, task: asyncio.Task) -> None:
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _process_side_effects_async(self, event: Event) -> None:
        try:
            await process_event_side_effects(self, event)
        except Exception as e:
            log.error("Error in event side-effects", topic=event.topic, error=str(e))
        finally:
            self._side_effect_semaphore.release()

    async def _send_with_timeout(self, ws: WebSocket, payload: dict) -> None:
        await asyncio.wait_for(ws.send_json(payload), timeout=self._send_timeout_seconds)

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

    def is_user_connected(self, user_id: str, topic: str) -> bool:
        """Return True when the user has at least one live socket on topic or its parent keys."""
        for key in self._topic_keys(topic):
            topic_connections = self._connection.get(key, {})
            if any(str(uid) == str(user_id) for uid in topic_connections.values()):
                return True
        return False

    def get_connection_counts(self) -> dict[str, int]:
        """Return current websocket connection counts grouped by topic."""
        return {topic: len(connections) for topic, connections in self._connection.items()}

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
        try:
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
                    await self._side_effect_semaphore.acquire()
                    task = asyncio.create_task(self._process_side_effects_async(event))
                    self._track_background_task(task)
                except Exception as e:
                    log.error("Error processing message",error=str(e))
                    continue
        finally:
            await pubsub.close()

    async def _broadcast(self,topic:str,event:Event):
        target_connections: dict[WebSocket, str] = {}
        keys = self._topic_keys(topic)
        for key in keys:
            target_connections.update(self._connection.get(key, {}))

        if not target_connections:
            log.debug("No active connections for topic",topic=topic)
            return
        payload = event.model_dump(mode="json")

        websockets= list(target_connections.keys())
        tasks=[self._send_with_timeout(ws, payload) for ws in websockets]
        
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
                except Exception:
                    dead.append(ws)
            for ws in dead:
                await self.disconnect_socket(ws, topic)
