from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    github_webhook_secret: str = ""
    github_app_id: str = ""
    github_installation_id: str = ""
    github_private_key_path: str = ""
    redis_url: str = "redis://localhost:6379/0"
    postgres_url: str = "postgresql://postgres:postgres@localhost:5432/pr_reviewer"


@lru_cache
def get_settings() -> Settings:
    return Settings()
