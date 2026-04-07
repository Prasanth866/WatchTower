from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from api import auth ,websocket ,health ,subscription
import asyncpg
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from core.config import get_settings
from workers.runner import start_all_workers
from core.database import engine, Base, CLEAN_DSN
from services.broadcaster import ConnectionManager
import asyncio
log = structlog.get_logger()
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.db_pool = await asyncpg.create_pool(
        dsn=CLEAN_DSN,
        min_size=1,
        max_size=10,
        command_timeout=60
    )
    setting = get_settings()
    aredis=aioredis.from_url(setting.REDIS_URL,decode_responses=True)  
    app.state.manager = ConnectionManager(aredis)  
    async def start_background_tasks():
        try:
            await app.state.manager.startup()
            async def heartbeat_loop():
                while True:
                    await asyncio.sleep(60)
                    await app.state.manager.cleanup_dead_connections()
            await asyncio.gather(start_all_workers(app.state.manager), heartbeat_loop())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("Error in background tasks",error=str(e))

    worker_task =asyncio.create_task(start_background_tasks())
    yield
    worker_task.cancel()
    if hasattr(app.state, 'db_pool'):
        await app.state.db_pool.close()
    await engine.dispose()
    
    
app = FastAPI(
    title="WatchTower",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,prefix='/health', tags=["health"])
app.include_router(auth.router, prefix="/auth",tags=["credentials"])
app.include_router(websocket.router,prefix="/ws",tags=["websocket"])
app.include_router(subscription.router,prefix="/subscriptions",tags=["subscriptions"])