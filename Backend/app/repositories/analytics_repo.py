from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fare_observation import FareObservation
from app.models.reference import Airport
from app.models.route import Route


def get_index_trend(db: Session, weeks: int = 8) -> dict:
    """
    Weekly national average price, indexed to the first week = 100, plus the
    same for routes touching a "South" region airport. Mirrors the Overview
    page's DEMO_INDEX_TREND shape.
    """
    today = date.today()
    start = today - timedelta(weeks=weeks)

    def weekly_series(south_only: bool):
        # floor() is essential here: without it, GROUP BY operates on a
        # continuous float (a fraction of a week) and almost every distinct
        # date lands in its own "bucket" instead of 7 consecutive days
        # collapsing into one week.
        week_bucket = func.floor(func.extract("epoch", FareObservation.observation_date) / (7 * 86400))
        stmt = (
            select(week_bucket.label("week_bucket"), func.avg(FareObservation.price))
            .where(FareObservation.observation_date >= start)
        )
        if south_only:
            stmt = (
                stmt.join(Route, FareObservation.route_id == Route.id)
                .join(Airport, Route.origin_airport_id == Airport.id)
                .where(Airport.region == "South")
            )
        stmt = stmt.group_by("week_bucket").order_by("week_bucket")
        rows = db.execute(stmt).all()
        values = [float(v) for _, v in rows]
        if not values:
            return []
        base = values[0]
        return [round(v / base * 100, 1) for v in values]

    national = weekly_series(south_only=False)
    south = weekly_series(south_only=True)
    n = max(len(national), len(south))
    labels = [f"Wk {i + 1}" for i in range(n)]
    return {"labels": labels, "national": national, "south": south}


def get_lead_time_curve(db: Session, route_id: int | None = None, travel_class: str | None = None) -> dict:
    stmt = select(FareObservation.days_to_departure, func.avg(FareObservation.price))
    if route_id is not None:
        stmt = stmt.where(FareObservation.route_id == route_id)
    if travel_class is not None:
        stmt = stmt.where(FareObservation.travel_class == travel_class)
    stmt = stmt.group_by(FareObservation.days_to_departure).order_by(FareObservation.days_to_departure.desc())

    rows = db.execute(stmt).all()
    labels = [f"T-{days}" for days, _ in rows]
    prices = [round(float(avg), 2) for _, avg in rows]
    return {"labels": labels, "prices": prices}


def get_lead_time_compare(db: Session, route_ids: dict[str, int]) -> dict:
    series = {}
    labels: list[str] = []
    for code, route_id in route_ids.items():
        curve = get_lead_time_curve(db, route_id=route_id)
        if len(curve["labels"]) > len(labels):
            labels = curve["labels"]
        series[code] = curve["prices"]
    return {"labels": labels, "series": series}


def get_checkpoint_breakdown(db: Session, route_id: int | None, checkpoints: list[int]) -> list[dict]:
    curve = get_lead_time_curve(db, route_id=route_id)
    price_by_label = dict(zip(curve["labels"], curve["prices"]))
    base_label = f"T-{max(checkpoints)}" if checkpoints else None
    base_price = price_by_label.get(base_label) if base_label else None

    rows = []
    for d in checkpoints:
        label = f"T-{d}"
        price = price_by_label.get(label)
        if price is None:
            continue
        pct_change = ((price - base_price) / base_price * 100) if base_price else 0.0
        rows.append({"checkpoint": label, "price": price, "pctChange": round(pct_change, 1)})
    return rows


def detect_anomalies(db: Session, z_threshold: float = 2.0) -> list[dict]:
    """
    Phase 1 anomaly detection: rule-based, not ML. For each route, flag the
    most recent observation if it deviates from that route's trailing
    30-day mean by more than `z_threshold` standard deviations. This is
    intentionally simple — Phase 4 is where a real anomaly-detection model
    replaces this function's internals without changing its signature.
    """
    routes = db.execute(select(Route)).scalars().all()
    alerts: list[dict] = []
    cutoff = date.today() - timedelta(days=30)

    for route in routes:
        prices = [
            float(p) for (p,) in db.execute(
                select(FareObservation.price).where(
                    FareObservation.route_id == route.id, FareObservation.observation_date >= cutoff
                )
            ).all()
        ]
        if len(prices) < 5:
            continue
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        stddev = variance ** 0.5
        if stddev == 0:
            continue
        latest = prices[-1]
        z = (latest - mean) / stddev
        if abs(z) >= z_threshold:
            severity = "High" if abs(z) >= 3 else "Medium"
            multiple = round(latest / mean, 1) if mean else 0
            alerts.append({
                "route": route.display_code,
                "detail": f"Fare at ₹{latest:,.0f} ({multiple}× 30-day mean)",
                "severity": severity,
            })
    return alerts
