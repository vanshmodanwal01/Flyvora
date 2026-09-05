"""
Flyvora Airfare Price Index - Prototype.

EXPLICITLY NOT an official CPI series. This is a documented, explainable
analytical prototype inspired by the SIH26056 objective, not a
government statistical product.

METHODOLOGY (v1-route-weighted):
1. Base period = the earliest week that has at least MIN_SAMPLE_SIZE
   observations for at least MIN_ROUTES_IN_BASKET routes.
2. The basket = every route that has >= MIN_SAMPLE_SIZE observations in
   BOTH the base period and the period being indexed. A route with too few
   observations in either period is excluded from that period's index and
   the exclusion is visible via the returned sample_size/basket_routes -
   this is what "route composition changes" and "sample-size thresholds"
   mean in practice here.
3. For each included route, compute period_avg_price / base_period_avg_price
   (a per-route relative). The index for the period is the EQUAL-WEIGHTED
   mean of those relatives, scaled to 100 at the base period.

This is a Laspeyres-style fixed-relative-comparison, but with EQUAL
weights across included routes, not expenditure-share weights (Flyvora has
no real passenger-volume/spend data per route to weight by - using one
would be fabricating a weighting scheme this data doesn't support).
Equal-weighting is the honest, simplest defensible choice given what's
actually measurable here, and is disclosed as such rather than presented
as CPI-equivalent.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fare_observation import FareObservation
from app.models.index_value import IndexValue
from app.models.route import Route

MIN_SAMPLE_SIZE = 5          # per route, per period
MIN_ROUTES_IN_BASKET = 3     # minimum routes for a period's index to be considered reliable
METHODOLOGY_VERSION = "v1-route-weighted"


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weekly_route_averages(db: Session) -> dict[date, dict[str, tuple[float, int]]]:
    """Returns {week_start: {route_code: (avg_price, sample_size)}}."""
    rows = db.execute(
        select(FareObservation.observation_date, Route.display_code, FareObservation.price)
        .join(Route, FareObservation.route_id == Route.id)
    ).all()

    buckets: dict[date, dict[str, list[float]]] = {}
    for obs_date, route_code, price in rows:
        week = _week_start(obs_date)
        buckets.setdefault(week, {}).setdefault(route_code, []).append(float(price))

    return {
        week: {code: (sum(prices) / len(prices), len(prices)) for code, prices in routes.items()}
        for week, routes in buckets.items()
    }


def compute_and_store_index(db: Session) -> dict:
    """
    Recomputes the full weekly index history from scratch and stores it.
    Cheap enough at this data scale (weekly buckets, not per-observation)
    to just replace the "national" scope's stored history each time it's
    called rather than doing incremental updates.
    """
    weekly = _weekly_route_averages(db)
    if not weekly:
        return {"status": "no_data", "methodology_version": METHODOLOGY_VERSION}

    weeks = sorted(weekly.keys())

    base_week = None
    for week in weeks:
        eligible = {code: v for code, v in weekly[week].items() if v[1] >= MIN_SAMPLE_SIZE}
        if len(eligible) >= MIN_ROUTES_IN_BASKET:
            base_week = week
            break

    if base_week is None:
        return {
            "status": "insufficient_data",
            "reason": f"No week has >= {MIN_ROUTES_IN_BASKET} routes with >= {MIN_SAMPLE_SIZE} observations",
            "methodology_version": METHODOLOGY_VERSION,
        }

    base_prices = {code: v[0] for code, v in weekly[base_week].items() if v[1] >= MIN_SAMPLE_SIZE}

    db.query(IndexValue).filter(IndexValue.scope == "national").delete()

    computed = []
    for week in weeks:
        if week < base_week:
            continue
        included = {
            code: v for code, v in weekly[week].items()
            if v[1] >= MIN_SAMPLE_SIZE and code in base_prices
        }
        if len(included) < MIN_ROUTES_IN_BASKET:
            continue  # this period genuinely can't support a reliable index - skipped, not faked

        relatives = [avg / base_prices[code] for code, (avg, _) in included.items()]
        index_value = round((sum(relatives) / len(relatives)) * 100, 2)
        total_sample = sum(count for _, count in included.values())

        db.add(IndexValue(
            scope="national", period=week, base_period=base_week,
            index_value=index_value, sample_size=total_sample,
            methodology_version=METHODOLOGY_VERSION,
        ))
        computed.append({"period": week.isoformat(), "index_value": index_value, "routes_in_basket": len(included), "sample_size": total_sample})

    db.commit()
    return {
        "status": "ok",
        "base_period": base_week.isoformat(),
        "methodology_version": METHODOLOGY_VERSION,
        "min_sample_size": MIN_SAMPLE_SIZE,
        "min_routes_in_basket": MIN_ROUTES_IN_BASKET,
        "periods_computed": len(computed),
        "series": computed,
    }


def get_index_history(db: Session, scope: str = "national") -> dict:
    rows = db.execute(
        select(IndexValue).where(IndexValue.scope == scope).order_by(IndexValue.period)
    ).scalars().all()
    if not rows:
        return {"status": "not_computed", "series": []}
    latest = rows[-1]
    first = rows[0]
    change_pct = round((float(latest.index_value) - float(first.index_value)) / float(first.index_value) * 100, 2) if first.index_value else 0.0
    return {
        "status": "ok",
        "label": "Flyvora Airfare Price Index — Prototype (NOT an official CPI series)",
        "methodology_version": latest.methodology_version,
        "base_period": latest.base_period.isoformat(),
        "current_index": float(latest.index_value),
        "change_percent_since_base": change_pct,
        "series": [
            {"period": r.period.isoformat(), "index_value": float(r.index_value), "sample_size": r.sample_size}
            for r in rows
        ],
    }
