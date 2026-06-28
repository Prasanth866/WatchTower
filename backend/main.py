""" 
    Main application entry point for WatchTower backend service.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from core.logger import setup_logging, get_logger
from core.exception import register_exception_handlers
from core.rate_limiter import limiter
from core.worker_status import WorkerStatusRegistry
from api import api_router
from core.config import get_settings
from core.database import engine
from workers.runner import start_all_workers
from services.broadcaster import ConnectionManager

setup_logging()
log = get_logger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Lifespan context manager to handle startup and shutdown events."""
    aredis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app_.state.manager = ConnectionManager(
        aredis,
        event_log_writer=None,
        process_side_effects=settings.ENABLE_WORKERS
    )
    app_.state.worker_status = WorkerStatusRegistry()
    app_.state.worker_status.set_enabled(settings.ENABLE_WORKERS)

    async def start_background_tasks():
        try:
            await app_.state.manager.startup()

            async def heartbeat_loop():
                while True:
                    await asyncio.sleep(60)
                    await app_.state.manager.cleanup_dead_connections()

            background_jobs = [heartbeat_loop()]
            if settings.ENABLE_WORKERS:
                background_jobs.append(
                    start_all_workers(app_.state.manager, app_.state.worker_status)
                )
            else:
                log.info("Worker loops disabled by configuration")

            await asyncio.gather(*background_jobs)
        except asyncio.CancelledError:
            log.info("Background tasks cancelled gracefully")
        except aioredis.RedisError as re:
            log.error("Redis error in background tasks", error=str(re))

    worker_task = asyncio.create_task(start_background_tasks())
    yield

    # ----------------------------------------------------------------
    # Shutdown sequence — order matters:
    # 1. Cancel worker_task and wait for it to finish completely so no
    #    new side-effect tasks are spawned after we start draining.
    # 2. Shutdown ConnectionManager (drains remaining background tasks).
    # 3. Close Redis only after all tasks that may use it are done.
    # 4. Dispose the DB engine last.
    # ----------------------------------------------------------------
    worker_task.cancel()
    await asyncio.gather(worker_task, return_exceptions=True)
    log.info("Worker task stopped")

    if hasattr(app_.state, "manager"):
        await app_.state.manager.shutdown()
        log.info("ConnectionManager shutdown complete")

    if hasattr(app_.state, "manager"):
        await app_.state.manager.redis.aclose()
        log.info("Redis connection closed")

    await engine.dispose()
    log.info("DB engine disposed")

app = FastAPI(
    title="WatchTower",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")