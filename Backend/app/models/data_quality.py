"""
IngestionJob and DataSource: these two tables are what turn the Data Quality
dashboard from a mockup into something real. IngestionJob rows == the
"Pipeline Run Log" table; DataSource rows == the "Data Source Status" list.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(str, enum.Enum):
    RUNNING = "Running"
    SUCCESS = "Success"
    WARNING = "Warning"
    FAILED = "Failed"


class SourceStatus(str, enum.Enum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    IDLE = "Idle"
    FAILED = "Failed"


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), default="csv")
    file_name: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus, name="job_status_enum"), default=JobStatus.RUNNING)

    total_records: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)
    missing_value_records: Mapped[int] = mapped_column(Integer, default=0)
    rejected_records: Mapped[int] = mapped_column(Integer, default=0)

    fare_observations: Mapped[list["FareObservation"]] = relationship(back_populates="ingestion_job")

    def __repr__(self) -> str:
        return f"<IngestionJob {self.file_name} {self.status}>"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(50))
    status: Mapped[SourceStatus] = mapped_column(Enum(SourceStatus, name="source_status_enum"), default=SourceStatus.IDLE)
    detail: Mapped[str] = mapped_column(String(255), default="")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DataSource {self.name} {self.status}>"
