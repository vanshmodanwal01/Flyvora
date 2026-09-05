"""
SerpApiProvider tests.

No live network call is made here (that's impossible to verify in CI or
without a real key) - instead these tests exercise the actual code paths
against fixture responses shaped exactly like SerpApi's documented JSON
(serpapi.com/google-flights-api), verified at implementation time. This
tests the code Flyvora actually runs, not a reimplementation of it.
"""
from datetime import date
from unittest.mock import Mock, patch

from app.providers.serpapi_provider import SerpApiProvider, _extract_airline_code, _parse_provider_datetime

# A trimmed but structurally faithful example of a real google_flights
# response, per SerpApi's own documented JSON example.
REALISTIC_RESPONSE = {
    "search_metadata": {"status": "Success"},
    "best_flights": [
        {
            "flights": [
                {
                    "departure_airport": {"name": "Indira Gandhi International Airport", "id": "DEL", "time": "2026-09-20 06:15"},
                    "arrival_airport": {"name": "Chhatrapati Shivaji Maharaj International Airport", "id": "BOM", "time": "2026-09-20 08:25"},
                    "duration": 130,
                    "airplane": "Airbus A320",
                    "airline": "IndiGo",
                    "travel_class": "Economy",
                    "flight_number": "6E 123",
                }
            ],
            "total_duration": 130,
            "price": 4850,
            "type": "One way",
            "departure_token": "abc123",
        }
    ],
    "other_flights": [],
}


def test_extract_airline_code_from_flight_number():
    assert _extract_airline_code("6E 123") == "6E"
    assert _extract_airline_code("AI 456") == "AI"
    assert _extract_airline_code(None) is None
    assert _extract_airline_code("") is None


def test_parse_provider_datetime():
    dt = _parse_provider_datetime("2026-09-20 06:15")
    assert dt.year == 2026 and dt.hour == 6 and dt.minute == 15
    assert _parse_provider_datetime(None) is None
    assert _parse_provider_datetime("not-a-date") is None


def test_provider_not_configured_returns_clear_failure_without_network_call():
    provider = SerpApiProvider(api_key="")
    with patch("app.providers.serpapi_provider.requests.get") as mock_get:
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    mock_get.assert_not_called()
    assert result.success is False
    assert "not configured" in result.error


def test_provider_normalizes_realistic_response():
    provider = SerpApiProvider(api_key="fake-test-key-not-real")
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = REALISTIC_RESPONSE
    with patch("app.providers.serpapi_provider.requests.get", return_value=mock_response):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))

    assert result.success is True
    assert result.raw_result_count == 1
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.origin == "DEL"
    assert obs.destination == "BOM"
    assert obs.airline_name == "IndiGo"
    assert obs.airline_code == "6E"
    assert obs.price == 4850.0
    assert obs.stops == 0
    assert obs.duration_minutes == 130


def test_provider_handles_malformed_response_gracefully():
    provider = SerpApiProvider(api_key="fake-test-key-not-real")
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"best_flights": [{"flights": []}]}  # no usable segments
    with patch("app.providers.serpapi_provider.requests.get", return_value=mock_response):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    assert result.success is True
    assert len(result.observations) == 0  # empty segments skipped, not crashed on


def test_provider_handles_api_error_field():
    provider = SerpApiProvider(api_key="fake-test-key-not-real")
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"error": "Invalid API key."}
    with patch("app.providers.serpapi_provider.requests.get", return_value=mock_response):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    assert result.success is False
    assert "Invalid API key" in result.error


def test_provider_handles_rate_limit():
    provider = SerpApiProvider(api_key="fake-test-key-not-real")
    mock_response = Mock(status_code=429)
    with patch("app.providers.serpapi_provider.requests.get", return_value=mock_response):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    assert result.success is False
    assert result.error == "rate_limited"


def test_provider_handles_auth_failure_without_exposing_response_body():
    provider = SerpApiProvider(api_key="fake-test-key-not-real")
    mock_response = Mock(status_code=401)
    mock_response.text = "some body that might echo the key back"
    with patch("app.providers.serpapi_provider.requests.get", return_value=mock_response):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    assert result.success is False
    assert result.error == "authentication_failed"


def test_provider_handles_timeout():
    import requests as requests_module
    provider = SerpApiProvider(api_key="fake-test-key-not-real", max_retries=0)
    with patch("app.providers.serpapi_provider.requests.get", side_effect=requests_module.exceptions.Timeout):
        result = provider.search_flights("DEL", "BOM", date(2026, 9, 20))
    assert result.success is False


def test_health_check_never_exposes_key():
    provider = SerpApiProvider(api_key="super-secret-value-should-never-appear")
    health = provider.health_check()
    assert "super-secret-value-should-never-appear" not in str(health)
    assert health["configured"] is True
