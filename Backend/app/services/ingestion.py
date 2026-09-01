"""
CSV ingestion pipeline: validation -> cleaning -> normalization ->
duplicate detection -> load.

This module is deliberately the only place that knows about CSV specifics.
`run_ingestion()` returns a normalized list of row-dicts ready for the
database; if Phase 2 adds a live flight API, that source only needs to
produce the same normalized row shape and can reuse `_load_valid_rows()`
and everything downstream unchanged.

Expected CSV columns (case-insensitive, extra columns are ignored):
    date               observation date, YYYY-MM-DD
    origin             3-letter IATA airport code
    destination        3-letter IATA airport code
    airline            IATA code (e.g. "6E") or airline name (e.g. "IndiGo")
    days_to_departure  integer >= 0
    price              numeric > 0
    travel_class       optional; one of Economy/Business/First Class (default Economy)
    currency           optional; default INR
"""
import os
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.data_quality import JobStatus, SourceStatus
from app.models.fare_observation import FareObservation, TravelClass
from app.repositories import data_quality_repo, route_repo
from app.repositories.airline_repo import get_or_create_airline
from app.utils.hashing import compute_dedup_hash

REQUIRED_COLUMNS = {"date", "origin", "destination", "airline", "days_to_departure", "price"}

# Known airline aliases -> (iata_code, canonical_name). Anything not found
# here still ingests fine — it's created as a new airline on the fly using
# whatever code/name the row supplies, since real-world CSVs will contain
# more carriers than we can hardcode.
AIRLINE_ALIASES: dict[str, tuple[str, str]] = {
    "6E": ("6E", "IndiGo"), "INDIGO": ("6E", "IndiGo"),
    "AI": ("AI", "Air India"), "AIR INDIA": ("AI", "Air India"),
    "SG": ("SG", "SpiceJet"), "SPICEJET": ("SG", "SpiceJet"),
    "QP": ("QP", "Akasa Air"), "AKASA": ("QP", "Akasa Air"), "AKASA AIR": ("QP", "Akasa Air"),
    "UK": ("UK", "Vistara"), "VISTARA": ("UK", "Vistara"),
}

VALID_TRAVEL_CLASSES = {c.value.upper(): c for c in TravelClass}

# Coarse region tags for common Indian domestic airports, so the Overview
# page's "South Regional" index has something to group on out of the box.
# Unrecognized codes simply ingest with region=None — they still work,
# they just won't count toward any regional sub-index until added here or
# updated directly in the `airports` table.
IATA_REGIONS: dict[str, str] = {
    "BLR": "South", "HYD": "South", "MAA": "South", "COK": "South", "TRV": "South",
    "DEL": "North", "JAI": "North", "LKO": "North", "CHD": "North",
    "BOM": "West", "PNQ": "West", "AMD": "West", "GOI": "West",
    "CCU": "East", "PAT": "East", "GAU": "East", "BBI": "East",
}


class RowResult:
    __slots__ = ("valid", "reason", "data")

    def __init__(self, valid: bool, reason: str | None = None, data: dict | None = None):
        self.valid = valid
        self.reason = reason
        self.data = data


def _validate_and_clean_row(row: dict) -> RowResult:
    # --- Missing-value check ---
    missing = [col for col in REQUIRED_COLUMNS if not str(row.get(col, "")).strip()]
    if missing:
        return RowResult(False, reason=f"missing:{','.join(missing)}")

    # --- Date ---
    try:
        obs_date = pd.to_datetime(row["date"]).date()
    except (ValueError, TypeError):
        return RowResult(False, reason="invalid_date")

    # --- Airport codes ---
    origin = str(row["origin"]).strip().upper()
    destination = str(row["destination"]).strip().upper()
    if len(origin) != 3 or len(destination) != 3 or not origin.isalpha() or not destination.isalpha():
        return RowResult(False, reason="invalid_airport_code")
    if origin == destination:
        return RowResult(False, reason="origin_equals_destination")

    # --- Days to departure ---
    try:
        days_to_departure = int(float(row["days_to_departure"]))
        if days_to_departure < 0:
            raise ValueError
    except (ValueError, TypeError):
        return RowResult(False, reason="invalid_days_to_departure")

    # --- Price ---
    try:
        price = float(str(row["price"]).replace(",", "").replace("₹", "").strip())
        if price <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return RowResult(False, reason="invalid_price")

    # --- Airline normalization ---
    raw_airline = str(row["airline"]).strip().upper()
    if raw_airline in AIRLINE_ALIASES:
        airline_code, airline_name = AIRLINE_ALIASES[raw_airline]
    else:
        airline_code = raw_airline[:3] if len(raw_airline) <= 3 else raw_airline[:2]
        airline_name = str(row["airline"]).strip()

    # --- Travel class (optional, default Economy) ---
    raw_class = str(row.get("travel_class", "")).strip().upper()
    travel_class = VALID_TRAVEL_CLASSES.get(raw_class, TravelClass.ECONOMY)

    currency = str(row.get("currency", "INR")).strip().upper() or "INR"

    return RowResult(True, data={
        "observation_date": obs_date,
        "origin": origin,
        "destination": destination,
        "airline_code": airline_code,
        "airline_name": airline_name,
        "days_to_departure": days_to_departure,
        "price": price,
        "travel_class": travel_class,
        "currency": currency,
    })


def run_ingestion(db: Session, file_path: str) -> dict:
    file_name = os.path.basename(file_path)
    job = data_quality_repo.create_job(db, file_name=file_name)
    db.commit()

    counts = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0, "missing": 0, "rejected": 0}
    rejected_reasons: dict[str, int] = {}
    normalized_rows: list[dict] = []

    try:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False, na_values=[])
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as exc:  # noqa: BLE001 - surface any read failure as a failed job
        data_quality_repo.finalize_job(db, job, counts, JobStatus.FAILED)
        db.commit()
        raise ValueError(f"Could not read CSV: {exc}") from exc

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        data_quality_repo.finalize_job(db, job, counts, JobStatus.FAILED)
        db.commit()
        raise ValueError(f"CSV is missing required columns: {sorted(missing_cols)}")

    for row in df.to_dict(orient="records"):
        counts["total"] += 1
        result = _validate_and_clean_row(row)
        if not result.valid:
            counts["invalid"] += 1
            counts["rejected"] += 1
            if result.reason and result.reason.startswith("missing"):
                counts["missing"] += 1
            rejected_reasons[result.reason] = rejected_reasons.get(result.reason, 0) + 1
            continue
        normalized_rows.append(result.data)

    # Resolve/create reference rows (airports, airlines, routes) up front so
    # the bulk insert below only needs foreign keys, not lookups per row.
    airport_cache: dict[str, int] = {}
    airline_cache: dict[str, int] = {}
    route_cache: dict[tuple[str, str], int] = {}

    insertable: list[dict] = []
    seen_hashes_this_run: set[str] = set()

    for r in normalized_rows:
        if r["origin"] not in airport_cache:
            airport = route_repo.get_or_create_airport(
                db, r["origin"], city=r["origin"], name=r["origin"], region=IATA_REGIONS.get(r["origin"])
            )
            airport_cache[r["origin"]] = airport.id
        if r["destination"] not in airport_cache:
            airport = route_repo.get_or_create_airport(
                db, r["destination"], city=r["destination"], name=r["destination"], region=IATA_REGIONS.get(r["destination"])
            )
            airport_cache[r["destination"]] = airport.id

        if r["airline_code"] not in airline_cache:
            airline = get_or_create_airline(db, r["airline_code"], r["airline_name"])
            airline_cache[r["airline_code"]] = airline.id

        route_key = (r["origin"], r["destination"])
        if route_key not in route_cache:
            from app.models.reference import Airport as AirportModel
            origin_obj = db.get(AirportModel, airport_cache[r["origin"]])
            dest_obj = db.get(AirportModel, airport_cache[r["destination"]])
            route = route_repo.get_or_create_route(db, origin_obj, dest_obj)
            route_cache[route_key] = route.id

        dedup_hash = compute_dedup_hash(
            route_code=f"{r['origin']}-{r['destination']}",
            airline_code=r["airline_code"],
            travel_class=r["travel_class"].value,
            observation_date=r["observation_date"].isoformat(),
            days_to_departure=r["days_to_departure"],
            price=r["price"],
            source="csv",
        )
        if dedup_hash in seen_hashes_this_run:
            counts["duplicate"] += 1
            continue
        seen_hashes_this_run.add(dedup_hash)

        insertable.append({
            "route_id": route_cache[route_key],
            "airline_id": airline_cache[r["airline_code"]],
            "travel_class": r["travel_class"],
            "observation_date": r["observation_date"],
            "days_to_departure": r["days_to_departure"],
            "price": r["price"],
            "currency": r["currency"],
            "source": "csv",
            "ingestion_job_id": job.id,
            "dedup_hash": dedup_hash,
            "created_at": datetime.now(timezone.utc),
        })

    db.flush()

    inserted_count = 0
    if insertable:
        stmt = pg_insert(FareObservation).values(insertable).on_conflict_do_nothing(index_elements=["dedup_hash"])
        result = db.execute(stmt)
        inserted_count = result.rowcount if result.rowcount is not None else 0
        counts["duplicate"] += len(insertable) - inserted_count

    counts["valid"] = inserted_count

    status = JobStatus.SUCCESS
    if counts["total"] == 0:
        status = JobStatus.FAILED
    elif counts["rejected"] > 0 or counts["duplicate"] > 0:
        status = JobStatus.WARNING

    data_quality_repo.finalize_job(db, job, counts, status)

    data_quality_repo.upsert_data_source(
        db,
        name=f"CSV Import — {file_name}",
        type_="csv",
        status=SourceStatus.HEALTHY if status != JobStatus.FAILED else SourceStatus.FAILED,
        detail=f"{inserted_count:,} records loaded, {counts['rejected']:,} rejected",
    )

    db.commit()

    return {
        "job_id": job.id,
        "status": status.value,
        "counts": counts,
        "rejected_reasons": rejected_reasons,
    }
