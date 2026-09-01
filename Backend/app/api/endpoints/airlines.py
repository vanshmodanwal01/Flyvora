from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.airlines import AirlineComparisonRow, AirlineIndexTrend, AirlineRouteMatrix
from app.services import airline_service

router = APIRouter(prefix="/airlines", tags=["airlines"])


@router.get("/comparison", response_model=list[AirlineComparisonRow])
def airline_comparison(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Avg-fare bar chart + ranking table, shared by Overview and Airline Comparison pages."""
    return airline_service.get_airline_comparison(db, days=days)


@router.get("/route-matrix", response_model=AirlineRouteMatrix)
def airline_route_matrix(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Grouped bar chart: fare by route, per airline."""
    return airline_service.get_airline_route_matrix(db, days=days)


@router.get("/index-trend", response_model=AirlineIndexTrend)
def airline_index_trend(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """30-day carrier index trend line chart, base = 100."""
    return airline_service.get_airline_index_trend(db, days=days)
