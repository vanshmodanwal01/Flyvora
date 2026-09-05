from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import (
    AnomalyAlert,
    CheckpointRow,
    IndexTrendResponse,
    LeadTimeCompareResponse,
    LeadTimeCurve,
    StructuredAnomaly,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/index-trend", response_model=IndexTrendResponse)
def index_trend(weeks: int = Query(8, ge=1, le=52), db: Session = Depends(get_db)):
    """National + South-regional airfare index trend line, Overview page."""
    return analytics_service.get_index_trend(db, weeks=weeks)


@router.get("/lead-time", response_model=LeadTimeCurve)
def lead_time_curve(
    route: str | None = Query(None, description="Route code, e.g. DEL-BOM. Omit for the all-routes aggregate."),
    travel_class: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Elasticity curve (price vs. days to departure), Lead-Time page hero chart."""
    return analytics_service.get_lead_time_curve(db, route_code=route, travel_class=travel_class)


@router.get("/lead-time/checkpoints", response_model=list[CheckpointRow])
def lead_time_checkpoints(
    route: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Checkpoint breakdown table (T-45..T-1), Lead-Time page."""
    return analytics_service.get_checkpoint_breakdown(db, route_code=route)


@router.get("/lead-time/compare", response_model=LeadTimeCompareResponse)
def lead_time_compare(
    routes: str = Query(..., description="Comma-separated route codes, e.g. DEL-BOM,BLR-DEL,BOM-BLR"),
    db: Session = Depends(get_db),
):
    """Multi-route elasticity comparison chart, Lead-Time page."""
    route_codes = [r.strip() for r in routes.split(",") if r.strip()]
    return analytics_service.get_lead_time_compare(db, route_codes)


@router.get("/anomalies", response_model=list[AnomalyAlert])
def anomalies(db: Session = Depends(get_db)):
    """Rule-based anomaly alerts list, Overview page."""
    return analytics_service.get_anomalies(db)


@router.get("/anomalies/detail", response_model=list[StructuredAnomaly])
def anomalies_detail(db: Session = Depends(get_db)):
    """Structured per-route anomaly detail: current/expected price, z-score,
    method, and an explicit insufficient_historical_data status rather than
    a fabricated anomaly for thinly-observed routes."""
    return analytics_service.get_anomalies_structured(db)
