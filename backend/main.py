from fastapi import FastAPI
import asyncpg
import os
import redis.asyncio as redis
from contextlib import asynccontextmanager

db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL")
    )
    yield
    await db_pool.close()

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
        r = redis.from_url(os.getenv("REDIS_URL"))  # type: ignore
        await r.ping()                              # type: ignore
        status["redis"] = "ok"
    except:
        status["redis"] = "error"

    try:
        async with db_pool.acquire() as conn:       #type: ignore
            await conn.execute("SELECT 1")
        status["postgres"] = "ok"
    except:
        status["postgres"] = "error"

    return status
