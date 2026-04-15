"""Database setup and configuration using SQLAlchemy."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in the environment variables. "
        "Check your .env file or Docker Compose settings."
    )

CLEAN_DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=_env_bool("SQLALCHEMY_ECHO", default=False),
    future=True,
    max_overflow=0,
    pool_size=5,
)

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
