# backend/app/core/config.py

from functools import lru_cache
from pydantic_settings import BaseSettings  # ⬅️ changed import


class Settings(BaseSettings):
    app_name: str = "Stock Sentiment Service"
    api_v1_prefix: str = "/api/v1"

    newsapi_key: str
    twitter_bearer_token: str | None = None

    # default training window (you can tweak)
    default_start_date: str = "2023-01-01"
    default_end_date: str = "2024-01-01"

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignore unknown env vars if any


@lru_cache()
def get_settings() -> Settings:
    return Settings()