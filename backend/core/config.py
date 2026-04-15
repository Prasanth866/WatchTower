"""Core configuration settings for the application."""
import json
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration settings."""
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SQLALCHEMY_ECHO: bool = False
    BASKETBALL_API_KEY: str
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    ENABLE_WORKERS: bool = True
    SIDE_EFFECT_CONCURRENCY: int = 16
    WEBSOCKET_SEND_TIMEOUT_SECONDS: float = 2.0
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    @field_validator("SECRET_KEY")
    @classmethod
    def check_secret_strength(cls, v: str) -> str:
        """Ensure the SECRET_KEY is sufficiently strong."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for HS256 safety.")
        return v

    def cors_allowed_origins_list(self) -> list[str]:
        """Parse CORS origins from either JSON array string or comma-separated string."""
        raw = self.CORS_ALLOWED_ORIGINS.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

@lru_cache()

def get_settings()->Settings:
    """Get the application settings, cached for performance."""
    return Settings() # type: ignore
