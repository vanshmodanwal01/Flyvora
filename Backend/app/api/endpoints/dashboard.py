from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import OverviewSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview/summary", response_model=OverviewSummary)
def overview_summary(db: Session = Depends(get_db)):
    """The 4 KPI cards at the top of the Overview page."""
    return dashboard_service.get_overview_summary(db)
