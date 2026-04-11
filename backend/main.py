""" 
    Main application entry point for WatchTower backend service.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import redis.asyncio as aioredis
from core.logger import setup_logging, get_logger
from core.exception import register_exception_handlers
from api import api_router
from core.config import get_settings
from core.database import engine,Base,CLEAN_DSN
from workers.runner import start_all_workers
from services.broadcaster import ConnectionManager

setup_logging()
log = get_logger(__name__)

@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Lifespan context manager to handle startup and shutdown events."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app_.state.db_pool = await asyncpg.create_pool(
        dsn=CLEAN_DSN,
        min_size=1,
        max_size=10,
        command_timeout=60
    )
    setting = get_settings()
    aredis=aioredis.from_url(setting.REDIS_URL,decode_responses=True)
    app_.state.manager = ConnectionManager(aredis)
    async def start_background_tasks():
        try:
            await app_.state.manager.startup()
            async def heartbeat_loop():
                while True:
                    await asyncio.sleep(60)
                    await app_.state.manager.cleanup_dead_connections()
            await asyncio.gather(
                start_all_workers(app_.state.manager),
                heartbeat_loop()
                )
        except asyncio.CancelledError:
            log.info("Background tasks cancelled gracefully")
        except aioredis.RedisError as re:
            log.error("Redis error in background tasks",error=str(re))

    worker_task =asyncio.create_task(start_background_tasks())
    yield
    worker_task.cancel()
    if hasattr(app_.state, 'db_pool'):
        await app_.state.db_pool.close()
    await engine.dispose()

app = FastAPI(
    title="WatchTower",
    lifespan=lifespan
)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router,prefix="/api/v1")