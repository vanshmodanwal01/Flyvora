"""
Collection orchestrator: Scheduler/manual-trigger -> route selection ->
provider -> validate -> store -> log. This is the "live" counterpart to
app/services/ingestion.py (the CSV path) - they share validation/hashing
philosophy but are separate because a live observation's identity
includes a real collection timestamp, while a CSV row's identity is
date-granular (see historical-observation rule in the module below).

A single route failing (provider error, malformed result, one bad
observation) never aborts the run - it's counted and the run continues.
"""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.collection import CollectionRun, CollectionRunStatus
from app.models.fare_observation import FareObservation, TravelClass
from app.providers.base import FlightDataProvider, NormalizedFlightObservation
from app.repositories import route_repo
from app.repositories.airline_repo import get_or_create_airline
from app.services.route_priority_service import get_latest_route_priority
from app.utils.hashing import compute_dedup_hash

logger = logging.getLogger("flyvora.collection")

# A live observation's default search horizon: search N days out so a
# recently-inserted route immediately has *some* upcoming-departure data,
# without hammering the provider with a wide date sweep on every run.
DEFAULT_SEARCH_DAYS_AHEAD = 14


def _validate_observation(obs: NormalizedFlightObservation) -> str | None:
    """Returns a rejection reason, or None if valid. Mirrors ingestion.py's
    validation philosophy but operates on the already-typed dataclass
    instead of raw CSV strings."""
    if not obs.origin or len(obs.origin) != 3 or not obs.origin.isalpha():
        return "invalid_origin"
    if not obs.destination or len(obs.destination) != 3 or not obs.destination.isalpha():
        return "invalid_destination"
    if obs.origin == obs.destination:
        return "origin_equals_destination"
    if obs.price is None or obs.price <= 0:
        return "invalid_price"
    if obs.outbound_date < date.today():
        return "outbound_date_in_past"
    return None


def _travel_class_from_string(raw: str | None) -> TravelClass:
    mapping = {"economy": TravelClass.ECONOMY, "business": TravelClass.BUSINESS, "first": TravelClass.FIRST}
    if not raw:
        return TravelClass.ECONOMY
    return mapping.get(raw.strip().lower(), TravelClass.ECONOMY)


def run_collection(
    db: Session,
    provider: FlightDataProvider,
    route_codes: list[str] | None = None,
    max_routes: int = 5,
    currency: str = "INR",
    travel_class: int = 1,
    trigger: str = "manual",
) -> CollectionRun:
    run = CollectionRun(
        started_at=datetime.now(timezone.utc),
        status=CollectionRunStatus.RUNNING,
        provider=provider.name,
        trigger=trigger,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if route_codes is None:
        priority = get_latest_route_priority(db)
        route_codes = [r["route_code"] for r in priority[:max_routes]]
    else:
        route_codes = route_codes[:max_routes]

    if not route_codes:
        run.status = CollectionRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.error_summary = "No routes available to collect (route priority table is empty - run ingestion or scoring first)"
        db.commit()
        return run

    if not provider.is_configured():
        run.status = CollectionRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.error_summary = "Provider not configured (SERPAPI_API_KEY empty) - provider-disabled mode, no live call attempted"
        run.routes_attempted = len(route_codes)
        run.routes_failed = len(route_codes)
        db.commit()
        logger.info("Collection run %s skipped: provider disabled", run.id)
        return run

    search_date = date.today() + timedelta(days=DEFAULT_SEARCH_DAYS_AHEAD)
    routes_successful = 0
    routes_failed = 0
    observations_found = 0
    observations_saved = 0
    observations_rejected = 0
    failure_notes: list[str] = []

    for route_code in route_codes:
        try:
            origin, destination = route_code.split("-")
        except ValueError:
            routes_failed += 1
            failure_notes.append(f"{route_code}: malformed route code")
            continue

        logger.info("Collecting %s", route_code)
        try:
            result = provider.search_flights(
                origin=origin, destination=destination, outbound_date=search_date,
                travel_class=travel_class, currency=currency,
            )
        except Exception as exc:  # noqa: BLE001 - one route's crash must never kill the run
            routes_failed += 1
            failure_notes.append(f"{route_code}: unexpected error ({type(exc).__name__})")
            logger.exception("Unhandled error collecting %s", route_code)
            continue

        if not result.success:
            routes_failed += 1
            failure_notes.append(f"{route_code}: {result.error}")
            logger.warning("%s failed: %s", route_code, result.error)
            continue

        routes_successful += 1
        observations_found += len(result.observations)
        logger.info("%s returned %d flight options", route_code, result.raw_result_count)

        for obs in result.observations:
            reason = _validate_observation(obs)
            if reason:
                observations_rejected += 1
                continue

            airport_o = route_repo.get_or_create_airport(db, obs.origin, city=obs.origin, name=obs.origin)
            airport_d = route_repo.get_or_create_airport(db, obs.destination, city=obs.destination, name=obs.destination)
            route = route_repo.get_or_create_route(db, airport_o, airport_d)
            airline_code = obs.airline_code or (obs.airline_name or "XX")[:3].upper()
            airline = get_or_create_airline(db, airline_code, obs.airline_name or airline_code)

            days_to_departure = (obs.outbound_date - obs.collected_at.date()).days

            # Historical-observation rule: dedup identity includes the real
            # collected_at TIMESTAMP (via isoformat in the hash), not just
            # the day - so two collections of the same flight at different
            # times of day are two rows, not one, exactly as required.
            dedup_hash = compute_dedup_hash(
                route_code=route.display_code,
                airline_code=airline_code,
                travel_class=(obs.travel_class or "Economy"),
                observation_date=obs.collected_at.isoformat(),
                days_to_departure=days_to_departure,
                price=obs.price,
                source=provider.name,
            )

            existing = db.query(FareObservation).filter_by(dedup_hash=dedup_hash).first()
            if existing:
                observations_rejected += 1
                continue

            db.add(FareObservation(
                route_id=route.id,
                airline_id=airline.id,
                travel_class=_travel_class_from_string(obs.travel_class),
                observation_date=obs.collected_at.date(),
                travel_date=obs.outbound_date,
                days_to_departure=max(days_to_departure, 0),
                price=obs.price,
                currency=obs.currency,
                source=provider.name,
                ingestion_job_id=None,
                collection_run_id=run.id,
                dedup_hash=dedup_hash,
                collected_at=obs.collected_at,
            ))
            observations_saved += 1

    db.commit()

    run.finished_at = datetime.now(timezone.utc)
    run.routes_attempted = len(route_codes)
    run.routes_successful = routes_successful
    run.routes_failed = routes_failed
    run.observations_found = observations_found
    run.observations_saved = observations_saved
    run.observations_rejected = observations_rejected
    run.error_summary = "; ".join(failure_notes)[:2000] if failure_notes else None

    if routes_successful == 0:
        run.status = CollectionRunStatus.FAILED
    elif routes_failed > 0:
        run.status = CollectionRunStatus.PARTIAL
    else:
        run.status = CollectionRunStatus.SUCCESS

    db.commit()
    logger.info("Collection run %s completed: %s", run.id, run.status)
    return run
