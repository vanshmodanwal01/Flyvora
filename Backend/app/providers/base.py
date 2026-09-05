"""
Provider abstraction: the rest of Flyvora depends on this interface, never
on a specific vendor's response shape.

    FlightDataProvider (ABC)
            |
            +---- SerpApiProvider   (real, implemented)
            |
            +---- FutureProvider    (not yet written - the point of this
                                      abstraction is that adding one never
                                      touches the collection service, the
                                      DB layer, or the API layer)

search_flights() returns a list of NormalizedFlightObservation - a
provider-neutral shape. If a provider can't supply a field, it's None.
Nothing here ever invents a value a provider didn't actually return.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class NormalizedFlightObservation:
    """Provider-neutral shape every FlightDataProvider must produce."""
    source: str                      # e.g. "serpapi"
    origin: str                      # 3-letter IATA
    destination: str                 # 3-letter IATA
    airline_name: str | None
    airline_code: str | None         # 2-char IATA if the provider gives one; SerpApi's `airline` is a name, not a code
    flight_number: str | None
    departure_time: datetime | None  # local time as given by the provider, naive if provider gives no tz
    arrival_time: datetime | None
    duration_minutes: int | None
    stops: int | None
    price: float | None
    currency: str
    travel_class: str | None
    outbound_date: date              # the date the search was FOR (i.e. travel date)
    collected_at: datetime           # when Flyvora made this observation - always set by the provider, always tz-aware
    raw_ref: str | None = None       # optional: a provider-specific id/token, never the raw payload itself


@dataclass
class ProviderSearchResult:
    """Wraps the observations plus whatever went wrong, per route, so the
    collection orchestrator can log a partial failure instead of crashing."""
    observations: list[NormalizedFlightObservation]
    provider: str
    success: bool
    error: str | None = None
    raw_result_count: int = 0        # how many itineraries the provider returned, before any of our filtering


class ProviderError(Exception):
    """Raised by a provider on auth failure, timeout, rate limit, or malformed response.
    Never carries the API key in its message."""
    pass


class FlightDataProvider(ABC):
    name: str = "unnamed_provider"

    @abstractmethod
    def is_configured(self) -> bool:
        """True if this provider has what it needs (e.g. an API key) to attempt a real call."""
        raise NotImplementedError

    @abstractmethod
    def search_flights(
        self,
        origin: str,
        destination: str,
        outbound_date: date,
        travel_class: int = 1,
        currency: str = "INR",
    ) -> ProviderSearchResult:
        """
        Search one route for one date. Must never raise for an ordinary
        "no flights found" or provider error - those go in
        ProviderSearchResult.success/error so one bad route never crashes
        a multi-route collection run. Only raises ProviderError for
        something the caller genuinely cannot proceed from (e.g. missing
        configuration entirely).
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict:
        """Returns a small, secret-free dict describing provider health -
        see app/providers/serpapi_provider.py for the exact shape."""
        raise NotImplementedError
