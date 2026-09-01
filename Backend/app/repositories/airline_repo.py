from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fare_observation import FareObservation
from app.models.reference import Airline
from app.models.route import Route


def get_or_create_airline(db: Session, iata_code: str, name: str) -> Airline:
    airline = db.execute(select(Airline).where(Airline.iata_code == iata_code.upper())).scalar_one_or_none()
    if airline:
        return airline
    airline = Airline(iata_code=iata_code.upper(), name=name)
    db.add(airline)
    db.flush()
    return airline


def get_airline_comparison(db: Session, days: int = 30) -> list[dict]:
    today = date.today()
    start = today - timedelta(days=days)
    prior_start = start - timedelta(days=days)

    total_obs = db.execute(
        select(func.count(FareObservation.id)).where(FareObservation.observation_date >= start)
    ).scalar_one()

    rows = []
    airlines = db.execute(select(Airline)).scalars().all()
    for airline in airlines:
        recent_avg = db.execute(
            select(func.avg(FareObservation.price)).where(
                FareObservation.airline_id == airline.id, FareObservation.observation_date >= start
            )
        ).scalar_one()
        if recent_avg is None:
            continue
        prior_avg = db.execute(
            select(func.avg(FareObservation.price)).where(
                FareObservation.airline_id == airline.id,
                FareObservation.observation_date >= prior_start,
                FareObservation.observation_date < start,
            )
        ).scalar_one()
        change_30d = ((float(recent_avg) - float(prior_avg)) / float(prior_avg) * 100) if prior_avg else 0.0

        airline_obs_count = db.execute(
            select(func.count(FareObservation.id)).where(
                FareObservation.airline_id == airline.id, FareObservation.observation_date >= start
            )
        ).scalar_one()
        market_share = (airline_obs_count / total_obs * 100) if total_obs else 0.0

        rows.append({
            "name": airline.name,
            "avgFare": round(float(recent_avg), 2),
            "change30d": round(change_30d, 1),
            "marketShare": round(market_share, 1),
        })
    return sorted(rows, key=lambda r: r["avgFare"])


def get_airline_route_matrix(db: Session, days: int = 30) -> dict:
    today = date.today()
    start = today - timedelta(days=days)

    rows = db.execute(
        select(Route.display_code, Airline.name, func.avg(FareObservation.price))
        .join(FareObservation, FareObservation.route_id == Route.id)
        .join(Airline, FareObservation.airline_id == Airline.id)
        .where(FareObservation.observation_date >= start)
        .group_by(Route.display_code, Airline.name)
    ).all()

    routes = sorted({r[0] for r in rows})
    matrix: dict[str, list[float]] = {}
    lookup = {(route_code, airline_name): float(avg) for route_code, airline_name, avg in rows}
    for _, airline_name, _ in rows:
        if airline_name in matrix:
            continue
        matrix[airline_name] = [round(lookup.get((rc, airline_name), 0.0), 2) for rc in routes]

    return {"routes": routes, "matrix": matrix}


def get_airline_index_trend(db: Session, days: int = 30) -> dict:
    """
    Base-100 index per airline over the window: for each day, the ratio of
    that day's average fare to the airline's average fare on the first day
    of the window, scaled to 100.
    """
    today = date.today()
    start = today - timedelta(days=days)

    airlines = db.execute(select(Airline)).scalars().all()
    all_dates = sorted({
        d for (d,) in db.execute(
            select(FareObservation.observation_date).where(FareObservation.observation_date >= start).distinct()
        ).all()
    })
    labels = [f"D{i + 1}" for i in range(len(all_dates))]

    series: dict[str, list[float]] = {}
    for airline in airlines:
        daily = db.execute(
            select(FareObservation.observation_date, func.avg(FareObservation.price))
            .where(FareObservation.airline_id == airline.id, FareObservation.observation_date >= start)
            .group_by(FareObservation.observation_date)
        ).all()
        if not daily:
            continue
        daily_map = {d: float(avg) for d, avg in daily}
        base = next((v for d, v in sorted(daily_map.items())), None)
        if not base:
            continue
        values = []
        last = 100.0
        for d in all_dates:
            if d in daily_map:
                last = round(daily_map[d] / base * 100, 1)
            values.append(last)
        series[airline.name] = values

    return {"labels": labels, "series": series}
