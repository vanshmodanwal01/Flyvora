from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.data_quality import (
    DataQualitySummary,
    DataSourceStatusItem,
    IngestionVolumePoint,
    PipelineRunLogRow,
    ValidationRate,
)
from app.services import data_quality_service

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/summary", response_model=DataQualitySummary)
def summary(db: Session = Depends(get_db)):
    """KPI cards at the top of the Data Quality page."""
    return data_quality_service.get_summary(db)


@router.get("/validation-rate", response_model=ValidationRate)
def validation_rate(db: Session = Depends(get_db)):
    """Passed/warned/failed doughnut chart."""
    return data_quality_service.get_validation_rate(db)


@router.get("/ingestion-volume", response_model=list[IngestionVolumePoint])
def ingestion_volume(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Daily ingestion volume bar chart."""
    return data_quality_service.get_ingestion_volume(db, days=days)


@router.get("/sources", response_model=list[DataSourceStatusItem])
def sources(db: Session = Depends(get_db)):
    """Data source status list."""
    return data_quality_service.get_sources(db)


@router.get("/runs", response_model=list[PipelineRunLogRow])
def runs(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    """Pipeline run log table."""
    return data_quality_service.get_run_log(db, limit=limit)
