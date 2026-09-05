"""
Collection orchestrator tests.

Uses a StubProvider (test-only, clearly named and never used outside
tests/) to exercise validation/normalization/storage/dedup without a real
network call. This is explicitly a stub for testing the orchestration
logic, not a claim that live collection has been verified end-to-end -
see the final report for what live verification actually requires.
"""
from datetime import date, datetime, timedelta, timezone

from app.models.collection import CollectionRunStatus
from app.models.fare_observation import FareObservation
from app.providers.base import FlightDataProvider, NormalizedFlightObservation, ProviderSearchResult
from app.services.collection_service import run_collection
from app.services.route_priority_service import compute_route_priority


class StubProvider(FlightDataProvider):
    """Test-only double. Never talks to the network. Not used in production code."""
    name = "stub_test_provider"

    def __init__(self, observations_by_route: dict[str, list[NormalizedFlightObservation]], configured: bool = True):
        self._observations_by_route = observations_by_route
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    def search_flights(self, origin, destination, outbound_date, travel_class=1, currency="INR", **kwargs):
        route = f"{origin}-{destination}"
        if route == "FAIL-ROUTE":
            return ProviderSearchResult(observations=[], provider=self.name, success=False, error="simulated_failure")
        obs = self._observations_by_route.get(route, [])
        return ProviderSearchResult(observations=obs, provider=self.name, success=True, raw_result_count=len(obs))

    def health_check(self) -> dict:
        return {"provider": self.name, "configured": self._configured}


def _make_obs(origin="DEL", destination="BOM", price=4500.0, outbound_date=None) -> NormalizedFlightObservation:
    return NormalizedFlightObservation(
        source="stub_test_provider", origin=origin, destination=destination,
        airline_name="IndiGo", airline_code="6E", flight_number="6E 123",
        departure_time=None, arrival_time=None, duration_minutes=130, stops=0,
        price=price, currency="INR", travel_class="Economy",
        outbound_date=outbound_date or (date.today() + timedelta(days=14)),
        collected_at=datetime.now(timezone.utc),
    )


def test_collection_run_with_no_configured_routes_fails_cleanly(db_session):
    provider = StubProvider(observations_by_route={})
    run = run_collection(db_session, provider, route_codes=[], max_routes=5)
    assert run.status == CollectionRunStatus.FAILED


def test_collection_run_saves_valid_observations(db_session):
    provider = StubProvider(observations_by_route={"DEL-BOM": [_make_obs()]})
    run = run_collection(db_session, provider, route_codes=["DEL-BOM"], max_routes=5)
    assert run.status == CollectionRunStatus.SUCCESS
    assert run.observations_saved == 1
    saved = db_session.query(FareObservation).filter_by(collection_run_id=run.id).all()
    assert len(saved) == 1
    assert saved[0].source == "stub_test_provider"
    assert saved[0].collection_run_id == run.id


def test_collection_run_rejects_invalid_price(db_session):
    provider = StubProvider(observations_by_route={"DEL-BOM": [_make_obs(price=-100)]})
    run = run_collection(db_session, provider, route_codes=["DEL-BOM"], max_routes=5)
    assert run.observations_rejected == 1
    assert run.observations_saved == 0


def test_collection_run_handles_partial_route_failure_without_crashing(db_session):
    provider = StubProvider(observations_by_route={"DEL-BOM": [_make_obs()]})
    run = run_collection(db_session, provider, route_codes=["DEL-BOM", "FAIL-ROUTE"], max_routes=5)
    assert run.status == CollectionRunStatus.PARTIAL
    assert run.routes_successful == 1
    assert run.routes_failed == 1
    assert run.observations_saved == 1  # the good route's data is still saved


def test_collection_run_preserves_repeated_observations_at_different_collection_times(db_session):
    """The historical-observation rule: two collections of the same route at
    different real timestamps are two rows, not a deduped one."""
    provider_morning = StubProvider(observations_by_route={
        "DEL-BOM": [NormalizedFlightObservation(
            source="stub_test_provider", origin="DEL", destination="BOM",
            airline_name="IndiGo", airline_code="6E", flight_number="6E 123",
            departure_time=None, arrival_time=None, duration_minutes=130, stops=0,
            price=4850.0, currency="INR", travel_class="Economy",
            outbound_date=date.today() + timedelta(days=14),
            collected_at=datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc),
        )]
    })
    provider_afternoon = StubProvider(observations_by_route={
        "DEL-BOM": [NormalizedFlightObservation(
            source="stub_test_provider", origin="DEL", destination="BOM",
            airline_name="IndiGo", airline_code="6E", flight_number="6E 123",
            departure_time=None, arrival_time=None, duration_minutes=130, stops=0,
            price=5120.0, currency="INR", travel_class="Economy",  # price genuinely changed
            outbound_date=date.today() + timedelta(days=14),
            collected_at=datetime(2026, 9, 4, 16, 0, tzinfo=timezone.utc),
        )]
    })

    run1 = run_collection(db_session, provider_morning, route_codes=["DEL-BOM"], max_routes=5)
    run2 = run_collection(db_session, provider_afternoon, route_codes=["DEL-BOM"], max_routes=5)

    assert run1.observations_saved == 1
    assert run2.observations_saved == 1  # NOT deduped against run1 - different collected_at, different price

    all_obs = db_session.query(FareObservation).filter(
        FareObservation.collection_run_id.in_([run1.id, run2.id])
    ).all()
    assert len(all_obs) == 2
    prices = sorted(float(o.price) for o in all_obs)
    assert prices == [4850.0, 5120.0]


def test_route_priority_scoring_is_data_driven_not_hardcoded(db_session):
    """Empty DB -> empty priority list; never fabricates a route that has no data."""
    result = compute_route_priority(db_session, top_n=5)
    assert result == []
