from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.data_quality import DataSource, IngestionJob, JobStatus
from app.models.fare_observation import FareObservation


def create_job(db: Session, file_name: str, source_type: str = "csv") -> IngestionJob:
    job = IngestionJob(file_name=file_name, source_type=source_type, status=JobStatus.RUNNING)
    db.add(job)
    db.flush()
    return job


def finalize_job(db: Session, job: IngestionJob, counts: dict, status: JobStatus) -> IngestionJob:
    job.completed_at = datetime.now(timezone.utc)
    job.status = status
    job.total_records = counts.get("total", 0)
    job.valid_records = counts.get("valid", 0)
    job.invalid_records = counts.get("invalid", 0)
    job.duplicate_records = counts.get("duplicate", 0)
    job.missing_value_records = counts.get("missing", 0)
    job.rejected_records = counts.get("rejected", 0)
    db.flush()
    return job


def list_recent_runs(db: Session, limit: int = 10) -> list[IngestionJob]:
    return list(
        db.execute(select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(limit)).scalars().all()
    )


def list_data_sources(db: Session) -> list[DataSource]:
    return list(db.execute(select(DataSource)).scalars().all())


def upsert_data_source(db: Session, name: str, type_: str, status, detail: str) -> DataSource:
    source = db.execute(select(DataSource).where(DataSource.name == name)).scalar_one_or_none()
    if source is None:
        source = DataSource(name=name, type=type_, status=status, detail=detail)
        db.add(source)
    else:
        source.status = status
        source.detail = detail
        source.last_synced_at = datetime.now(timezone.utc)
    db.flush()
    return source


def get_summary(db: Session) -> dict:
    latest_job = db.execute(select(IngestionJob).order_by(IngestionJob.started_at.desc()).limit(1)).scalar_one_or_none()
    total_records = db.execute(select(func.count(FareObservation.id))).scalar_one()

    last_30_jobs = list(
        db.execute(
            select(IngestionJob).where(IngestionJob.started_at >= datetime.now(timezone.utc) - timedelta(days=30))
        ).scalars().all()
    )
    # "Uptime" here means the pipeline itself completed, not that every row
    # was clean — a run that finishes with some rejected rows is a Warning,
    # not downtime. Only FAILED runs (the CSV couldn't even be read, or
    # produced zero usable rows) count against uptime.
    not_failed = sum(1 for j in last_30_jobs if j.status != JobStatus.FAILED)
    uptime = (not_failed / len(last_30_jobs) * 100) if last_30_jobs else 100.0

    total_invalid = sum(j.invalid_records for j in last_30_jobs)

    return {
        "recordsIngested": total_records,
        "pipelineUptime": f"{uptime:.1f}%",
        "validationFailures": total_invalid,
        "lastRun": latest_job.completed_at if latest_job else None,
    }


def get_validation_rate(db: Session) -> dict:
    jobs = list(
        db.execute(
            select(IngestionJob).where(IngestionJob.started_at >= datetime.now(timezone.utc) - timedelta(days=30))
        ).scalars().all()
    )
    total = sum(j.total_records for j in jobs)
    if total == 0:
        return {"passed": 0.0, "warned": 0.0, "failed": 0.0}
    valid = sum(j.valid_records for j in jobs)
    duplicate = sum(j.duplicate_records for j in jobs)
    rejected = sum(j.rejected_records for j in jobs)
    return {
        "passed": round(valid / total * 100, 1),
        "warned": round(duplicate / total * 100, 1),
        "failed": round(rejected / total * 100, 1),
    }


def get_ingestion_volume(db: Session, days: int = 30) -> list[dict]:
    jobs = list(
        db.execute(
            select(IngestionJob)
            .where(IngestionJob.started_at >= datetime.now(timezone.utc) - timedelta(days=days))
            .order_by(IngestionJob.started_at)
        ).scalars().all()
    )
    return [
        {"label": job.started_at.strftime("%d %b"), "records": job.valid_records}
        for job in jobs
    ]
