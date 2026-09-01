"""
Deterministic hashing for duplicate detection.

The hash is computed from the *natural key* of a fare observation — the
combination of fields that together should be unique. Two CSV rows (even
from different files, different ingestion runs) that describe the same
quote will hash identically and the second insert will be rejected by the
database's unique constraint rather than by a slower pre-check SELECT.
"""
import hashlib


def compute_dedup_hash(
    route_code: str,
    airline_code: str,
    travel_class: str,
    observation_date: str,
    days_to_departure: int,
    price: float,
    source: str,
) -> str:
    natural_key = "|".join([
        route_code.strip().upper(),
        airline_code.strip().upper(),
        travel_class.strip(),
        observation_date,
        str(days_to_departure),
        f"{price:.2f}",
        source.strip().lower(),
    ])
    return hashlib.sha256(natural_key.encode("utf-8")).hexdigest()
