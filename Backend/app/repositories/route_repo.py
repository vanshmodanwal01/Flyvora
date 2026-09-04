"""
All raw route/fare queries live here. Services call these and apply
business logic (formatting, trend direction) on top — repositories never
know about the frontend's response shape.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fare_observation import FareObservation
from app.models.reference import Airline, Airport
from app.models.route import Route


def list_routes(db: Session) -> list[Route]:
    return list(db.execute(select(Route).order_by(Route.display_code)).scalars().all())


def get_route_by_code(db: Session, code: str) -> Route | None:
    return db.execute(select(Route).where(Route.display_code == code.upper())).scalar_one_or_none()


def get_or_create_airport(db: Session, iata_code: str, city: str, name: str, region: str | None = None) -> Airport:
    airport = db.execute(select(Airport).where(Airport.iata_code == iata_code.upper())).scalar_one_or_none()
    if airport:
        return airport
    airport = Airport(iata_code=iata_code.upper(), city=city, name=name, region=region)
    db.add(airport)
    db.flush()
    return airport


def get_or_create_route(db: Session, origin: Airport, destination: Airport) -> Route:
    route = db.execute(
        select(Route).where(
            Route.origin_airport_id == origin.id,
            Route.destination_airport_id == destination.id,
        )
    ).scalar_one_or_none()
    if route:
        return route
    route = Route(
        origin_airport_id=origin.id,
        destination_airport_id=destination.id,
        display_code=f"{origin.iata_code}-{destination.iata_code}",
    )
    db.add(route)
    db.flush()
    return route


def _avg_price_in_window(db: Session, route_id: int, start: date, end: date) -> float | None:
    result = db.execute(
        select(func.avg(FareObservation.price)).where(
            FareObservation.route_id == route_id,
            FareObservation.observation_date >= start,
            FareObservation.observation_date <= end,
        )
    ).scalar_one()
    return float(result) if result is not None else None


def get_route_ranking(db: Session, days: int = 30) -> list[dict]:
    """
    For every route with observations, compare the average price in the
    most recent `days` window against the prior window of equal length,
    and return the percent change plus its configured index weight.
    """
    today = date.today()
    recent_start = today - timedelta(days=days)
    prior_start = recent_start - timedelta(days=days)

    routes = list_routes(db)
    rows: list[dict] = []
    for route in routes:
        recent_avg = _avg_price_in_window(db, route.id, recent_start, today)
        prior_avg = _avg_price_in_window(db, route.id, prior_start, recent_start)
        if recent_avg is None or prior_avg in (None, 0):
            continue
        pct_change = ((recent_avg - prior_avg) / prior_avg) * 100
        weight = float(route.index_weight) if route.index_weight is not None else 0.0
        rows.append({"route": route.display_code, "weight": weight, "change": round(pct_change, 1)})
    return sorted(rows, key=lambda r: r["change"], reverse=True)


def get_route_summary(db: Session, route: Route, days: int = 30) -> dict | None:
    today = date.today()
    start = today - timedelta(days=days)
    prior_start = start - timedelta(days=days)

    observations = db.execute(
        select(FareObservation)
        .where(FareObservation.route_id == route.id, FareObservation.observation_date >= start)
        .order_by(FareObservation.observation_date)
    ).scalars().all()

    if not observations:
        return None

    daily_avg: dict[date, list[float]] = {}
    for obs in observations:
        daily_avg.setdefault(obs.observation_date, []).append(float(obs.price))

    labels = [f"{d.day} {d.strftime('%b')}" for d in sorted(daily_avg.keys())]
    route_prices = [round(sum(v) / len(v), 2) for _, v in sorted(daily_avg.items())]

    # National average across the same dates, for the comparison line.
    national_rows = db.execute(
        select(FareObservation.observation_date, func.avg(FareObservation.price))
        .where(FareObservation.observation_date >= start)
        .group_by(FareObservation.observation_date)
        .order_by(FareObservation.observation_date)
    ).all()
    national_by_date = {d: float(avg) for d, avg in national_rows}
    national_avg_prices = [round(national_by_date.get(d, route_prices[i]), 2) for i, d in enumerate(sorted(daily_avg.keys()))]

    recent_avg = sum(route_prices) / len(route_prices)
    prior_avg = _avg_price_in_window(db, route.id, prior_start, start)
    pct_change = ((recent_avg - prior_avg) / prior_avg * 100) if prior_avg else 0.0

    airline_breakdown = {}
    airline_rows = db.execute(
        select(Airline.iata_code, func.avg(FareObservation.price))
        .join(FareObservation, FareObservation.airline_id == Airline.id)
        .where(FareObservation.route_id == route.id, FareObservation.observation_date >= start)
        .group_by(Airline.iata_code)
    ).all()
    for code, avg in airline_rows:
        airline_breakdown[code] = float(avg)

    return {
        "route": route,
        "avg_fare": recent_avg,
        "pct_change": pct_change,
        "observations": len(observations),
        "labels": labels,
        "route_prices": route_prices,
        "national_avg_prices": national_avg_prices,
        "airline_breakdown": airline_breakdown,
    }
