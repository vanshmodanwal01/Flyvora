from sqlalchemy.orm import Session

from app.repositories import data_quality_repo
from app.schemas.data_quality import (
    DataQualitySummary,
    DataSourceStatusItem,
    IngestionVolumePoint,
    PipelineRunLogRow,
    ValidationRate,
)


def get_summary(db: Session) -> DataQualitySummary:
    return DataQualitySummary(**data_quality_repo.get_summary(db))


def get_validation_rate(db: Session) -> ValidationRate:
    return ValidationRate(**data_quality_repo.get_validation_rate(db))


def get_ingestion_volume(db: Session, days: int = 30) -> list[IngestionVolumePoint]:
    return [IngestionVolumePoint(**p) for p in data_quality_repo.get_ingestion_volume(db, days=days)]


def get_sources(db: Session) -> list[DataSourceStatusItem]:
    sources = data_quality_repo.list_data_sources(db)
    return [
        DataSourceStatusItem(name=s.name, status=s.status.value, detail=s.detail)
        for s in sources
    ]


def get_run_log(db: Session, limit: int = 10) -> list[PipelineRunLogRow]:
    jobs = data_quality_repo.list_recent_runs(db, limit=limit)
    rows = []
    for job in jobs:
        duration = (job.completed_at - job.started_at).total_seconds() if job.completed_at else 0.0
        rows.append(PipelineRunLogRow(
            time=job.started_at,
            status=job.status.value,
            records=job.valid_records,
            durationSeconds=round(duration, 1),
        ))
    return rows
