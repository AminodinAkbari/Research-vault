from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # AI roadmap generation — any OpenAI-compatible chat-completions API
    # (defaults target OpenRouter, but any compatible base URL/model works).
    # Left blank by default so the app still starts without it configured;
    # the roadmap service raises a clear error at call time if it's unset.
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api-inference.huggingface.co/v1"
    AI_MODEL: str = "deepseek-ai/DeepSeek-V3-0324"

    # Roadmap response caching (Redis)
    ROADMAP_CACHE_TTL_SECONDS: int = 3600

    # AI endpoints rate limiting (Redis, fixed window) — shared budget across
    # roadmap, summarise, explain, suggest-tags and search-semantic.
    AI_RATE_LIMIT_MAX_REQUESTS: int = 10
    AI_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Auth endpoints rate limiting (Redis, fixed window, IP-based) —
    # brute-force protection for register/login.
    AUTH_RATE_LIMIT_MAX_REQUESTS: int = 20
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 300

    OPENROUTER_API_KEY: str | None = None
    HF_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()