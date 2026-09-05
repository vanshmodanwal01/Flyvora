from datetime import datetime

from pydantic import BaseModel


class CollectionRunResponse(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    provider: str
    trigger: str
    routes_attempted: int
    routes_successful: int
    routes_failed: int
    observations_found: int
    observations_saved: int
    observations_rejected: int
    error_summary: str | None


class CollectionStatusResponse(BaseModel):
    scheduler_running: bool
    next_scheduled_run: str | None
    collection_interval_minutes: int
    max_routes_per_run: int
    last_run: CollectionRunResponse | None
    routes_monitored: int


class ProviderHealthResponse(BaseModel):
    provider: str
    configured: bool
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error: str | None = None


class RoutePriorityItem(BaseModel):
    route_code: str
    rank: int
    historical_frequency_score: float
    live_availability_score: float
    airline_count_score: float
    total_score: float
    is_demo_priority: bool
