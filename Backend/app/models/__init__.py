"""
Importing every model module here guarantees they're all registered against
Base's mapper registry before SQLAlchemy tries to resolve the string-based
relationship() references between them (e.g. Route -> "FareObservation").

Alembic's env.py also imports this module so autogenerate can see every table.
"""
from app.models.reference import Airline, Airport  # noqa: F401
from app.models.route import Route  # noqa: F401
from app.models.fare_observation import FareObservation, TravelClass  # noqa: F401
from app.models.data_quality import DataSource, IngestionJob, JobStatus, SourceStatus  # noqa: F401

__all__ = [
    "Airline",
    "Airport",
    "Route",
    "FareObservation",
    "TravelClass",
    "IngestionJob",
    "JobStatus",
    "DataSource",
    "SourceStatus",
]
