"""
Reference/lookup tables: Airline and Airport.

These exist so ingestion can normalize messy source strings ("Air India",
"AIR INDIA", "AI") down to one canonical row, rather than storing free-text
airline/airport names directly on every fare observation.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Airline(Base):
    __tablename__ = "airlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    iata_code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    fare_observations: Mapped[list["FareObservation"]] = relationship(back_populates="airline")

    def __repr__(self) -> str:
        return f"<Airline {self.iata_code} {self.name}>"


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    iata_code: Mapped[str] = mapped_column(String(3), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    # Coarse region tag (e.g. "South", "North", "East", "West") so the
    # Overview page's national-vs-regional index split has something to
    # group on without a separate regions table. Nullable: unmapped
    # airports still ingest fine, they just won't count toward any
    # regional sub-index until tagged.
    region: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Airport {self.iata_code} {self.city}>"
