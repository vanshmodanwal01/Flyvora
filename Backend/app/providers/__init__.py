"""
Provider factory. The rest of the app calls get_provider() and gets back
whatever FlightDataProvider is currently active - it never imports
SerpApiProvider directly. Swapping or adding a provider means changing
this one function, nothing that calls it.
"""
from functools import lru_cache

from app.core.config import settings
from app.providers.base import FlightDataProvider
from app.providers.serpapi_provider import SerpApiProvider

__all__ = ["FlightDataProvider", "get_provider"]


@lru_cache
def get_provider() -> FlightDataProvider:
    return SerpApiProvider(
        api_key=settings.SERPAPI_API_KEY,
        timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        max_retries=settings.PROVIDER_MAX_RETRIES,
    )
