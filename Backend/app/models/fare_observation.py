"""
FareObservation: one row per observed fare quote. Event-level and
append-only — we never update or aggregate in place here, so the same raw
data can answer any slicing the dashboards need (by route, by airline, by
lead-time bucket, by date range) via GROUP BY at query time.
"""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TravelClass(str, enum.Enum):
    ECONOMY = "Economy"
    BUSINESS = "Business"
    FIRST = "First Class"


class FareObservation(Base):
    __tablename__ = "fare_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), index=True)
    airline_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"), index=True)

    travel_class: Mapped[TravelClass] = mapped_column(Enum(TravelClass, name="travel_class_enum"))
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    days_to_departure: Mapped[int] = mapped_column(SmallInteger, index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # "csv" today; "api" once Phase 2 lands a live source. Keeps the schema
    # source-agnostic without needing a migration when that happens.
    source: Mapped[str] = mapped_column(String(20), default="csv")

    ingestion_job_id: Mapped[int] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)

    # sha256 of the natural key (route, airline, class, date, lead time,
    # price, source). Unique constraint on this is what makes duplicate
    # detection an O(1) insert-conflict instead of a pre-check query.
    dedup_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    route = relationship("Route", back_populates="fare_observations")
    airline = relationship("Airline", back_populates="fare_observations")
    ingestion_job = relationship("IngestionJob", back_populates="fare_observations")

    def __repr__(self) -> str:
        return f"<FareObservation route={self.route_id} price={self.price}>"
