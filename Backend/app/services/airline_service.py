from sqlalchemy.orm import Session

from app.repositories import airline_repo
from app.schemas.airlines import AirlineComparisonRow, AirlineIndexTrend, AirlineRouteMatrix


def get_airline_comparison(db: Session, days: int = 30) -> list[AirlineComparisonRow]:
    rows = airline_repo.get_airline_comparison(db, days=days)
    return [AirlineComparisonRow(**r) for r in rows]


def get_airline_route_matrix(db: Session, days: int = 30) -> AirlineRouteMatrix:
    data = airline_repo.get_airline_route_matrix(db, days=days)
    return AirlineRouteMatrix(routes=data["routes"], matrix=data["matrix"])


def get_airline_index_trend(db: Session, days: int = 30) -> AirlineIndexTrend:
    data = airline_repo.get_airline_index_trend(db, days=days)
    return AirlineIndexTrend(labels=data["labels"], series=data["series"])
