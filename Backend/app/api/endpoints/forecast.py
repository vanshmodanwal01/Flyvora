from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.forecast_service import get_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/{route_code}")
def forecast(route_code: str, db: Session = Depends(get_db)):
    """Simple exponential smoothing with an explicit insufficient-data status - never a fabricated prediction."""
    return get_forecast(db, route_code)
