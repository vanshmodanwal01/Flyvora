"""
Automated-collection tracking: CollectionRun (one row per scheduler/manual
trigger) and RoutePriority (the output of the route-discovery/scoring
service - explicitly a "Flyvora Prototype Route Priority", never presented
as an official traffic ranking).
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CollectionRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[CollectionRunStatus] = mapped_column(
        Enum(CollectionRunStatus, name="collection_run_status_enum"), default=CollectionRunStatus.PENDING
    )
    provider: Mapped[str] = mapped_column(String(30))
    trigger: Mapped[str] = mapped_column(String(20), default="scheduled")  # "scheduled" | "manual"

    routes_attempted: Mapped[int] = mapped_column(Integer, default=0)
    routes_successful: Mapped[int] = mapped_column(Integer, default=0)
    routes_failed: Mapped[int] = mapped_column(Integer, default=0)

    observations_found: Mapped[int] = mapped_column(Integer, default=0)
    observations_saved: Mapped[int] = mapped_column(Integer, default=0)
    observations_rejected: Mapped[int] = mapped_column(Integer, default=0)

    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # never contains secrets

    def __repr__(self) -> str:
        return f"<CollectionRun {self.id} {self.status}>"


class RoutePriority(Base):
    """
    One row per (route, scored_at) - kept as history, not overwritten, so
    the scoring methodology's evolution over time is itself inspectable.
    """
    __tablename__ = "route_priorities"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_code: Mapped[str] = mapped_column(String(10), index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rank: Mapped[int] = mapped_column(Integer)

    historical_frequency_score: Mapped[float] = mapped_column(Numeric(6, 4))
    live_availability_score: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    airline_count_score: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    total_score: Mapped[float] = mapped_column(Numeric(6, 4))

    is_demo_priority: Mapped[bool] = mapped_column(default=False)  # manually pinned for demo (e.g. LKO routes), never hides the real score

    def __repr__(self) -> str:
        return f"<RoutePriority {self.route_code} rank={self.rank}>"
