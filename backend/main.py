from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth 
import asyncpg
import os
import redis.asyncio as redis
from contextlib import asynccontextmanager
from services.database import engine, Base, CLEAN_DSN
from sqlalchemy import text

db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn=CLEAN_DSN
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
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except:
        status["postgres"] = "error"

    return status

app.include_router(auth.router, prefix="/auth",tags=["credentials"])
