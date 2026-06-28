from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # Database (async — used by FastAPI)
    DATABASE_URL: str

    # Database (sync — used by Celery tasks and Alembic)
    DATABASE_URL_SYNC: str

    # Redis / Celery
    REDIS_URL: str

    # SearXNG
    SEARXNG_URL: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()