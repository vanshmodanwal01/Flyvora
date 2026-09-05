"""
SerpApiProvider: talks to SerpApi's Google Flights engine and normalizes
its response into NormalizedFlightObservation objects.

Verified against SerpApi's current documentation (serpapi.com/google-flights-api)
at implementation time - not assumed from memory. Key facts this code relies on:

- Endpoint: GET https://serpapi.com/search
- engine=google_flights, departure_id/arrival_id are 3-letter IATA codes,
  type=2 means one-way (so return_date must NOT be sent), outbound_date is
  YYYY-MM-DD, travel_class is an int 1-4, currency/gl/hl are the
  localization params.
- Results come back under "best_flights" and/or "other_flights", NOT a
  single flat list - a route can have results in either, both, or neither.
- Each itinerary has its own top-level "price" (an integer in the request
  currency) and a "flights" array of one or more *segments* (multi-segment
  = a connection). There is no single documented "airline_code" field -
  SerpApi gives an airline *name* string; the 2-letter carrier code is only
  recoverable from the documented flight_number format (IATA convention:
  2-char code + digits), which is a real parsing rule, not a guess.
- price_insights (when present) carries a lowest_price/typical_price_range/
  price_history - not stored per-observation here, but available for future use.

Every field this code cannot get from the actual response is left as None -
never invented.
"""
import logging
import time
from datetime import date, datetime, timezone

import requests

from app.providers.base import (
    FlightDataProvider,
    NormalizedFlightObservation,
    ProviderSearchResult,
)

logger = logging.getLogger("flyvora.providers.serpapi")

SERPAPI_ENDPOINT = "https://serpapi.com/search"


def _extract_airline_code(flight_number: str | None) -> str | None:
    """IATA flight numbers are documented as '2-character airline code + 1-4 digits'
    (e.g. 'NH 962' -> 'NH'). This is a real, documented parsing rule, not inference."""
    if not flight_number:
        return None
    code = flight_number.strip().split(" ")[0].strip()
    return code if 2 <= len(code) <= 3 else None


def _parse_provider_datetime(raw: str | None) -> datetime | None:
    """SerpApi gives departure/arrival times as 'YYYY-MM-DD HH:MM' local strings, no tz."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


class SerpApiProvider(FlightDataProvider):
    name = "serpapi"

    def __init__(self, api_key: str, timeout_seconds: int = 20, max_retries: int = 2):
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None
        self._last_error: str | None = None

    def is_configured(self) -> bool:
        return bool(self._api_key.strip())

    def health_check(self) -> dict:
        # Never include the key itself - not even a masked fragment, per the
        # security rules this project is being built under.
        return {
            "provider": self.name,
            "configured": self.is_configured(),
            "last_success_at": self._last_success_at.isoformat() if self._last_success_at else None,
            "last_failure_at": self._last_failure_at.isoformat() if self._last_failure_at else None,
            "last_error": self._last_error,
        }

    def search_flights(
        self,
        origin: str,
        destination: str,
        outbound_date: date,
        travel_class: int = 1,
        currency: str = "INR",
        country: str = "IN",
        language: str = "en",
    ) -> ProviderSearchResult:
        if not self.is_configured():
            return ProviderSearchResult(
                observations=[], provider=self.name, success=False,
                error="SerpApi is not configured (SERPAPI_API_KEY is empty) - provider-disabled mode",
            )

        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date.isoformat(),
            "type": "2",  # one-way - return_date must be omitted for this type
            "travel_class": str(travel_class),
            "currency": currency,
            "gl": country,
            "hl": language,
            "adults": "1",
            "api_key": self._api_key,
        }

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=self._timeout)
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning("SerpApi timeout on %s-%s (attempt %d)", origin, destination, attempt + 1)
                time.sleep(2 ** attempt)
                continue
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logger.warning("SerpApi request error on %s-%s: %s", origin, destination, type(exc).__name__)
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 429:
                self._last_failure_at = datetime.now(timezone.utc)
                self._last_error = "rate_limited"
                return ProviderSearchResult(observations=[], provider=self.name, success=False, error="rate_limited")
            if response.status_code in (401, 403):
                self._last_failure_at = datetime.now(timezone.utc)
                self._last_error = "authentication_failed"
                # Never include response body here - it may echo the key back in query-string form.
                return ProviderSearchResult(observations=[], provider=self.name, success=False, error="authentication_failed")
            if response.status_code != 200:
                last_exc = RuntimeError(f"HTTP {response.status_code}")
                time.sleep(2 ** attempt)
                continue

            try:
                data = response.json()
            except ValueError as exc:
                last_exc = exc
                continue

            if data.get("error"):
                self._last_failure_at = datetime.now(timezone.utc)
                self._last_error = str(data["error"])[:200]
                return ProviderSearchResult(observations=[], provider=self.name, success=False, error=self._last_error)

            observations, raw_count = self._normalize(data, origin, destination, outbound_date, currency)
            self._last_success_at = datetime.now(timezone.utc)
            self._last_error = None
            return ProviderSearchResult(
                observations=observations, provider=self.name, success=True, raw_result_count=raw_count,
            )

        self._last_failure_at = datetime.now(timezone.utc)
        self._last_error = str(last_exc)[:200] if last_exc else "unknown_error"
        return ProviderSearchResult(observations=[], provider=self.name, success=False, error=self._last_error)

    def _normalize(
        self, data: dict, origin: str, destination: str, outbound_date: date, currency: str,
    ) -> tuple[list[NormalizedFlightObservation], int]:
        itineraries = (data.get("best_flights") or []) + (data.get("other_flights") or [])
        observations: list[NormalizedFlightObservation] = []
        collected_at = datetime.now(timezone.utc)

        for itinerary in itineraries:
            segments = itinerary.get("flights") or []
            if not segments:
                continue
            first_leg, last_leg = segments[0], segments[-1]
            flight_number = first_leg.get("flight_number")

            observations.append(NormalizedFlightObservation(
                source=self.name,
                origin=first_leg.get("departure_airport", {}).get("id", origin),
                destination=last_leg.get("arrival_airport", {}).get("id", destination),
                airline_name=first_leg.get("airline"),
                airline_code=_extract_airline_code(flight_number),
                flight_number=flight_number,
                departure_time=_parse_provider_datetime(first_leg.get("departure_airport", {}).get("time")),
                arrival_time=_parse_provider_datetime(last_leg.get("arrival_airport", {}).get("time")),
                duration_minutes=itinerary.get("total_duration"),
                stops=max(len(segments) - 1, 0),
                price=float(itinerary["price"]) if itinerary.get("price") is not None else None,
                currency=currency,
                travel_class=first_leg.get("travel_class"),
                outbound_date=outbound_date,
                collected_at=collected_at,
                raw_ref=itinerary.get("departure_token") or itinerary.get("booking_token"),
            ))
        return observations, len(itineraries)
