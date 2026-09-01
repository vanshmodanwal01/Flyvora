"""
Route: one row per origin-destination airport pair.

`display_code` is denormalized (e.g. "DEL-BOM") purely so read queries for
the heatmap/ranking table don't need a join every time — it's derived and
kept in sync at write time, never edited directly.
"""
from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (UniqueConstraint("origin_airport_id", "destination_airport_id", name="uq_route_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), index=True)
    destination_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), index=True)
    display_code: Mapped[str] = mapped_column(String(10), index=True)

    # Nullable: a route's share of the overall index basket. Can be seeded
    # manually or computed later by the Phase 3 index engine — Phase 1 just
    # needs somewhere to store it since the frontend already displays it.
    index_weight: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    origin = relationship("Airport", foreign_keys=[origin_airport_id])
    destination = relationship("Airport", foreign_keys=[destination_airport_id])
    fare_observations: Mapped[list["FareObservation"]] = relationship(back_populates="route")

    def __repr__(self) -> str:
        return f"<Route {self.display_code}>"
