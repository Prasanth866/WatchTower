from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth ,websocket
import asyncpg
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from services.database import engine, Base, CLEAN_DSN
from sqlalchemy import text
from services.broadcaster import ConnectionManager, REDIS_URL

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
    yield
    if 'db_pool' in app.state:
        await app.state.db_pool.close()
    
    
app = FastAPI(
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "FastAPI running"}


@app.get("/health")
async def health_check():
    status = {"api": "ok"}
    
    try:
        r = aioredis.from_url(REDIS_URL,decode_responses=True)  
        await r.ping()                              # type: ignore
        status["redis"] = "ok"
    except:
        status["redis"] = "error"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except:
        status["postgres"] = "error"

    return status

app.include_router(auth.router, prefix="/auth",tags=["credentials"])
app.include_router(websocket.router,prefix="/ws",tags=["websocket"])