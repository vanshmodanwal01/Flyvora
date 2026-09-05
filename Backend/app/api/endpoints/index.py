from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.index_service import compute_and_store_index, get_index_history

router = APIRouter(prefix="/index", tags=["index"])


@router.get("")
def index_history(db: Session = Depends(get_db)):
    """Flyvora Airfare Price Index - Prototype. NOT an official CPI series - see label/methodology_version in the response."""
    return get_index_history(db)


@router.post("/recompute")
def recompute_index(db: Session = Depends(get_db)):
    """Recomputes the full weekly index history from current data. Prototype/demo endpoint, no auth layer."""
    return compute_and_store_index(db)
