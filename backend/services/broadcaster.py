import asyncio
import re
import inspect
from typing import Any
from contextlib import suppress
from fastapi.websockets import WebSocketState
from fastapi import WebSocket, status
from redis.asyncio import Redis
from schemas.event import Event
from core.coins import AVAILABLE_COINS
from core.config import get_settings
from core.logger import get_logger
from services.event_processing_service import process_event_side_effects

setting = get_settings()

log = get_logger(__name__)

class ConnectionManager:
    def __init__(self, redis: Redis, event_log_writer: Any | None = None, process_side_effects: bool = True):
        self._redis = redis
        self._event_log_writer = event_log_writer
        self._process_side_effects = process_side_effects
        self._connection: dict[str, dict[WebSocket, str]] = {}
        self._conn_lock = asyncio.Lock()  # Guards _connection dict for all mutations/iterations
        self._listen_task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()
        self._bg_tasks_lock = asyncio.Lock()  # Guards _background_tasks set
        self._side_effect_limit = max(1, int(getattr(setting, "SIDE_EFFECT_CONCURRENCY", 16)))
        self._side_effect_semaphore = asyncio.Semaphore(self._side_effect_limit)
        self._send_timeout_seconds = float(getattr(setting, "WEBSOCKET_SEND_TIMEOUT_SECONDS", 2.0))
        self._shutdown_drain_seconds = float(getattr(setting, "SIDE_EFFECT_SHUTDOWN_DRAIN_SECONDS", 10.0))

    @property
    def redis(self) -> Redis:
        return self._redis

    @property
    def event_log_writer(self) -> Any | None:
        return self._event_log_writer

    @staticmethod
    async def _safe_await(value):
        if inspect.isawaitable(value):
            return await value
        return value

    async def startup(self):
        self._listen_task = asyncio.create_task(self._listen())
        log.info("ConnectionManager started")

    async def shutdown(self):
        if self._listen_task:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        # Drain background side-effect tasks before closing resources
        async with self._bg_tasks_lock:
            pending_tasks = list(self._background_tasks)

        if pending_tasks:
            done, pending = await asyncio.wait(
                pending_tasks,
                timeout=self._shutdown_drain_seconds,
            )
            if pending:
                for task in list(pending):
                    task.cancel()
                await asyncio.gather(*list(pending), return_exceptions=True)
            if done:
                await asyncio.gather(*list(done), return_exceptions=True)

            async with self._bg_tasks_lock:
                self._background_tasks.clear()

        # Clean up Redis connection tracking for all remaining sockets
        if hasattr(self._redis, "hincrby"):
            async with self._conn_lock:
                snapshot = {
                    topic: dict(conns)
                    for topic, conns in self._connection.items()
                }
            for topic, connections in snapshot.items():
                for ws, user_id in connections.items():
                    try:
                        val = await self._safe_await(
                            self._redis.hincrby(f"watchtower:user:{user_id}:topics", topic, -1)
                        )
                        if val <= 0:
                            await self._safe_await(
                                self._redis.hdel(f"watchtower:user:{user_id}:topics", topic)
                            )
                    except Exception:
                        pass

    def side_effect_runtime(self) -> dict[str, int]:
        queue_size = 0
        dropped_events = 0
        if self._event_log_writer:
            queue_size = int(getattr(self._event_log_writer, "queue_size", 0))
            dropped_events = int(getattr(self._event_log_writer, "dropped_events", 0))

        return {
            "active_tasks": len(self._background_tasks),
            "queue_size": queue_size,
            "dropped_events": dropped_events,
        }

    def _track_background_task(self, task: asyncio.Task) -> None:
        # Callback runs from the event loop thread — safe to access the set directly,
        # but we schedule a coroutine to add under lock to keep things consistent.
        async def _add():
            async with self._bg_tasks_lock:
                self._background_tasks.add(task)

        async def _discard(t: asyncio.Task):
            async with self._bg_tasks_lock:
                self._background_tasks.discard(t)

        # Schedule the add immediately; the discard is added as a done_callback.
        asyncio.ensure_future(_add())
        task.add_done_callback(lambda t: asyncio.ensure_future(_discard(t)))

    async def _process_side_effects_async(self, event: Event) -> None:
        try:
            await process_event_side_effects(self, event)
        except Exception as e:
            log.error("Error in event side-effects", topic=event.topic, error=str(e))
        finally:
            self._side_effect_semaphore.release()

    async def _send_with_timeout(self, ws: WebSocket, payload: dict) -> None:
        await asyncio.wait_for(ws.send_json(payload), timeout=self._send_timeout_seconds)

    async def subscribe(self, websocket: WebSocket, topic: str, user_id: str):
        async with self._conn_lock:
            self._connection.setdefault(topic, {})[websocket] = user_id
        log.info("User subscribed", user_id=user_id, topic=topic)
        if hasattr(self._redis, "hincrby"):
            try:
                await self._safe_await(self._redis.hincrby(f"watchtower:user:{user_id}:topics", topic, 1))
                await self._safe_await(self._redis.expire(f"watchtower:user:{user_id}:topics", 86400))
            except Exception as e:
                log.error("Failed to track connection in Redis", error=str(e))

    async def disconnect_socket(self, websocket: WebSocket, topic: str):
        async with self._conn_lock:
            topic_connections = self._connection.get(topic, {})
            user_id = topic_connections.pop(websocket, None)
            if not topic_connections:
                self._connection.pop(topic, None)

        if user_id:
            log.info("User unsubscribed", user_id=user_id, topic=topic)
            if hasattr(self._redis, "hincrby"):
                try:
                    val = await self._safe_await(
                        self._redis.hincrby(f"watchtower:user:{user_id}:topics", topic, -1)
                    )
                    if val <= 0:
                        await self._safe_await(
                            self._redis.hdel(f"watchtower:user:{user_id}:topics", topic)
                        )
                except Exception as e:
                    log.error("Failed to untrack connection in Redis", error=str(e))

    async def disconnect_user_from_topic(self, user_id: str, topic: str):
        async with self._conn_lock:
            topic_connections = self._connection.get(topic, {})
            ws_to_remove = [ws for ws, uid in topic_connections.items() if str(uid) == str(user_id)]

        for ws in ws_to_remove:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.close(code=status.WS_1000_NORMAL_CLOSURE)
                    log.info("Closed websocket connection", user_id=user_id, topic=topic)
            except Exception as e:
                log.error("Error closing websocket", error=str(e))
            finally:
                await self.disconnect_socket(ws, topic)

    async def is_user_connected(self, user_id: str, topic: str) -> bool:
        """Return True when the user has at least one live socket on topic or its parent keys."""
        keys = self._topic_keys(topic)
        async with self._conn_lock:
            for key in keys:
                topic_connections = self._connection.get(key, {})
                if any(str(uid) == str(user_id) for uid in topic_connections.values()):
                    return True
        if hasattr(self._redis, "hgetall"):
            try:
                user_topics = await self._safe_await(
                    self._redis.hgetall(f"watchtower:user:{user_id}:topics")
                )
                for k in keys:
                    if user_topics.get(k):
                        try:
                            if int(user_topics[k]) > 0:
                                return True
                        except ValueError:
                            pass
            except Exception as e:
                log.error("Redis error in is_user_connected", error=str(e))
        return False

    async def send_user_alert(self, user_id: str, topic: str, alert_payload: dict) -> bool:
        """Send an alert payload to a specific user subscribed to a topic (or its patterns)."""
        keys = self._topic_keys(topic)
        sent = False
        for key in keys:
            async with self._conn_lock:
                topic_connections = dict(self._connection.get(key, {}))
            for ws, uid in topic_connections.items():
                if str(uid) == str(user_id):
                    try:
                        await self._send_with_timeout(ws, alert_payload)
                        sent = True
                    except Exception as e:
                        log.error("Failed to send alert to websocket", error=str(e), user_id=user_id)
                        await self.disconnect_socket(ws, key)
        return sent

    def get_connection_counts(self) -> dict[str, int]:
        """Return current websocket connection counts grouped by topic."""
        # Snapshot without lock — acceptable for metrics (eventual consistency)
        return {topic: len(connections) for topic, connections in self._connection.items()}

    async def publish(self, topic: str, event: Event):
        await self._safe_await(self._redis.publish(topic, event.model_dump_json()))
        await self._safe_await(self._redis.set(f"price:{topic}", str(event.value)))
        await self._safe_await(self._redis.set(f"price_event:{topic}", event.model_dump_json()))

    @staticmethod
    def _topic_keys(topic: str) -> list[str]:
        keys = [topic]
        parts = topic.split(".")
        if len(parts) > 1:
            for i in range(len(parts) - 1, 0, -1):
                keys.append(".".join(parts[:i]))
        root = re.split(r"[:.>]", topic, maxsplit=1)[0]
        if root not in keys:
            keys.append(root)
        return keys

    async def _listen(self):
        channels = [coin.symbol for coin in AVAILABLE_COINS]
        patterns = [f"{coin.symbol}.*" for coin in AVAILABLE_COINS]
        backoff = 1.0
        max_backoff = 60.0

        while True:
            pubsub = None
            try:
                pubsub = self._redis.pubsub()
                await self._safe_await(pubsub.subscribe(*channels))
                await self._safe_await(pubsub.psubscribe(*patterns))
                log.info("Subscribed to Redis channels and patterns", channels=channels, patterns=patterns)
                backoff = 1.0
                async for message in pubsub.listen():
                    if message["type"] not in ["message", "pmessage"]:
                        continue
                    try:
                        topic = message["channel"]
                        if isinstance(topic, bytes):
                            topic = topic.decode()
                        event = Event.model_validate_json(message["data"])
                        await self._broadcast(topic, event)
                        if self._process_side_effects:
                            await self._side_effect_semaphore.acquire()
                            task = asyncio.create_task(self._process_side_effects_async(event))
                            self._track_background_task(task)
                    except Exception as e:
                        log.error("Error processing message", error=str(e))
                        continue
            except asyncio.CancelledError:
                log.info("Redis listener task cancelled gracefully")
                break
            except Exception as e:
                log.error("Redis connection lost in listener, retrying", error=str(e), backoff_seconds=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, max_backoff)
            finally:
                if pubsub:
                    try:
                        await self._safe_await(pubsub.aclose())
                    except Exception:
                        pass

    async def _broadcast(self, topic: str, event: Event):
        keys = self._topic_keys(topic)

        # Snapshot connections under lock to avoid dict mutation during send
        async with self._conn_lock:
            target_connections: dict[WebSocket, str] = {}
            for key in keys:
                target_connections.update(self._connection.get(key, {}))

        if not target_connections:
            log.debug("No active connections for topic", topic=topic)
            return

        payload = event.model_dump(mode="json")
        websockets = list(target_connections.keys())
        tasks = [self._send_with_timeout(ws, payload) for ws in websockets]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                ws = websockets[i]
                log.error("Broadcast failed for socket", error=str(res), topic=event.topic)
                for key in keys:
                    await self.disconnect_socket(ws, key)

    async def cleanup_dead_connections(self):
        # Snapshot topics under lock; then check/clean each ws without holding the lock
        async with self._conn_lock:
            topics_snapshot = list(self._connection.keys())

        for topic in topics_snapshot:
            async with self._conn_lock:
                ws_snapshot = list(self._connection.get(topic, {}).keys())

            dead = []
            for ws in ws_snapshot:
                if ws.client_state != WebSocketState.CONNECTED:
                    dead.append(ws)
                    continue
                try:
                    await ws.send_json({"type": "ping"})
                except Exception:
                    dead.append(ws)

            for ws in dead:
                await self.disconnect_socket(ws, topic)
