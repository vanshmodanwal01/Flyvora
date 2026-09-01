from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.routes import RouteListItem, RouteRankingRow, RouteSummary
from app.services import route_service

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("", response_model=list[RouteListItem])
def list_routes(db: Session = Depends(get_db)):
    """Populates the route-picker dropdown on the Route Explorer page."""
    return route_service.list_routes(db)


@router.get("/ranking", response_model=list[RouteRankingRow])
def route_ranking(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Powers the sector-volatility / route-heatmap table on Overview and Route Explorer."""
    return route_service.get_route_ranking(db, days=days)


@router.get("/{route_code}/summary", response_model=RouteSummary)
def route_summary(route_code: str, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Powers the KPI tiles, price-trend chart, and airline breakdown for one route."""
    summary = route_service.get_route_summary(db, route_code, days=days)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No data for route '{route_code}'")
    return summary
