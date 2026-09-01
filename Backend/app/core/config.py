"""
Centralized application configuration.

Every setting is read from environment variables (or a local .env file in
development). Nothing here should be hardcoded per-environment — Docker
Compose, a bare-metal dev run, and a future cloud deployment all just set
different env vars against this same class.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://flyvora:flyvora_dev_password@localhost:5432/flyvora"

    # --- CORS ---
    # Comma-separated in the env var, parsed into a list here.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Misc ---
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Flyvora API"
    API_PREFIX: str = "/api"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so we don't re-parse the environment on every request."""
    return Settings()


settings = get_settings()
