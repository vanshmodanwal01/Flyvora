"""
Collection endpoints - explicitly a prototype/demo surface, not a hardened
admin API. POST /run has no auth layer (matches the rest of this
prototype's endpoints and was an explicit scope decision for the demo) -
it never accepts or returns provider credentials.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.scheduler import get_scheduler_status
from app.models.collection import CollectionRun
from app.providers import get_provider
from app.repositories import route_repo
from app.schemas.collection import (
    CollectionRunResponse,
    CollectionStatusResponse,
    ProviderHealthResponse,
    RoutePriorityItem,
)
from app.services.collection_service import run_collection
from app.services.route_priority_service import compute_route_priority, get_latest_route_priority

router = APIRouter(prefix="/collection", tags=["collection"])


def _to_run_response(run: CollectionRun) -> CollectionRunResponse:
    return CollectionRunResponse(
        id=run.id, started_at=run.started_at, finished_at=run.finished_at,
        status=run.status.value, provider=run.provider, trigger=run.trigger,
        routes_attempted=run.routes_attempted, routes_successful=run.routes_successful,
        routes_failed=run.routes_failed, observations_found=run.observations_found,
        observations_saved=run.observations_saved, observations_rejected=run.observations_rejected,
        error_summary=run.error_summary,
    )


@router.post("/run", response_model=CollectionRunResponse)
def trigger_collection(
    max_routes: int = Query(default=None, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Manually trigger a collection run - for demo/dev use. Never exposes the API key."""
    provider = get_provider()
    run = run_collection(
        db, provider,
        max_routes=max_routes or settings.MAX_ROUTES_PER_RUN,
        currency=settings.DEFAULT_CURRENCY,
        travel_class=settings.DEFAULT_TRAVEL_CLASS,
        trigger="manual",
    )
    return _to_run_response(run)


@router.get("/status", response_model=CollectionStatusResponse)
def collection_status(db: Session = Depends(get_db)):
    scheduler_status = get_scheduler_status()
    last_run = db.query(CollectionRun).order_by(CollectionRun.started_at.desc()).first()
    routes_monitored = len(route_repo.list_routes(db))
    return CollectionStatusResponse(
        scheduler_running=scheduler_status["running"],
        next_scheduled_run=scheduler_status["next_run_time"],
        collection_interval_minutes=scheduler_status["interval_minutes"],
        max_routes_per_run=settings.MAX_ROUTES_PER_RUN,
        last_run=_to_run_response(last_run) if last_run else None,
        routes_monitored=routes_monitored,
    )


@router.get("/provider-health", response_model=ProviderHealthResponse)
def provider_health():
    """Never returns the API key - only whether one is configured and recent call outcomes."""
    provider = get_provider()
    return ProviderHealthResponse(**provider.health_check())


@router.get("/route-priority", response_model=list[RoutePriorityItem])
def route_priority(
    recompute: bool = Query(False, description="Recompute from current data instead of returning the last computed set"),
    db: Session = Depends(get_db),
):
    """'Flyvora Prototype Route Priority' - NOT an official traffic ranking. See route_priority_service docstring."""
    if recompute:
        return compute_route_priority(db, top_n=settings.TOP_N_ROUTES)
    existing = get_latest_route_priority(db)
    if existing:
        return existing
    return compute_route_priority(db, top_n=settings.TOP_N_ROUTES)
