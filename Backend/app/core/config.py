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
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,http://127.0.0.1:5500"

    # --- Misc ---
    ENVIRONMENT: str = "development"
    APP_NAME: str = "Flyvora API"
    API_PREFIX: str = "/api"

    # --- Live provider (SerpApi Google Flights) ---
    # Never logged, never returned by any endpoint, never has a default value.
    SERPAPI_API_KEY: str = ""
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_TRAVEL_CLASS: int = 1  # 1=Economy, 2=Premium economy, 3=Business, 4=First (SerpApi's own encoding)
    DEFAULT_COUNTRY: str = "IN"    # SerpApi `gl` param
    DEFAULT_LANGUAGE: str = "en"   # SerpApi `hl` param
    PROVIDER_TIMEOUT_SECONDS: int = 20
    PROVIDER_MAX_RETRIES: int = 2

    # --- Automated collection ---
    COLLECTION_INTERVAL_MINUTES: int = 60
    MAX_ROUTES_PER_RUN: int = 5
    TOP_N_ROUTES: int = 5
    SCHEDULER_ENABLED: bool = True
    DEMO_MODE: bool = False

    # --- Timezone ---
    APP_TIMEZONE: str = "Asia/Kolkata"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def serpapi_configured(self) -> bool:
        return bool(self.SERPAPI_API_KEY.strip())


@lru_cache
def get_settings() -> Settings:
    """Cached so we don't re-parse the environment on every request."""
    return Settings()


settings = get_settings()
