from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth ,websocket ,health
import asyncpg
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from workers.runner import start_all_workers
from services.database import engine, Base, CLEAN_DSN
from services.broadcaster import ConnectionManager, REDIS_URL
import asyncio
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.db_pool = await asyncpg.create_pool(
        dsn=CLEAN_DSN
    )
    aredis=aioredis.from_url(REDIS_URL,decode_responses=True)  
    app.state.manager = ConnectionManager(aredis)  
    await app.state.manager.startup()  
    worker_task =asyncio.create_task(start_all_workers(app.state.manager))
    yield
    worker_task.cancel()
    if 'db_pool' in app.state:
        await app.state.db_pool.close()
    
    
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