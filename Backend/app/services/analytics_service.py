from sqlalchemy.orm import Session

from app.repositories import analytics_repo, route_repo
from app.schemas.analytics import (
    AnomalyAlert,
    CheckpointRow,
    IndexTrendResponse,
    LeadTimeCompareResponse,
    LeadTimeCurve,
)

DEFAULT_CHECKPOINTS = [45, 30, 21, 14, 7, 3, 1]


def get_index_trend(db: Session, weeks: int = 8) -> IndexTrendResponse:
    data = analytics_repo.get_index_trend(db, weeks=weeks)
    return IndexTrendResponse(**data)


def get_lead_time_curve(db: Session, route_code: str | None, travel_class: str | None) -> LeadTimeCurve:
    route_id = None
    if route_code:
        route = route_repo.get_route_by_code(db, route_code)
        route_id = route.id if route else None
    data = analytics_repo.get_lead_time_curve(db, route_id=route_id, travel_class=travel_class)
    return LeadTimeCurve(**data)


def get_lead_time_compare(db: Session, route_codes: list[str]) -> LeadTimeCompareResponse:
    route_ids = {}
    for code in route_codes:
        route = route_repo.get_route_by_code(db, code)
        if route:
            route_ids[code] = route.id
    data = analytics_repo.get_lead_time_compare(db, route_ids)
    return LeadTimeCompareResponse(**data)


def get_checkpoint_breakdown(db: Session, route_code: str | None) -> list[CheckpointRow]:
    route_id = None
    if route_code:
        route = route_repo.get_route_by_code(db, route_code)
        route_id = route.id if route else None
    rows = analytics_repo.get_checkpoint_breakdown(db, route_id=route_id, checkpoints=DEFAULT_CHECKPOINTS)
    return [CheckpointRow(**r) for r in rows]


def get_anomalies(db: Session) -> list[AnomalyAlert]:
    alerts = analytics_repo.detect_anomalies(db)
    return [AnomalyAlert(**a) for a in alerts]
