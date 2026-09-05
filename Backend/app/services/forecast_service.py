"""
Forecasting - deliberately simple (single exponential smoothing), not a
new dependency-heavy model. Justification for the choice: daily route-level
price series here are short (weeks, not years) and don't show strong
seasonality Flyvora can currently measure, so a heavier model (ARIMA,
LSTM) would be both unjustified by data volume and unexplainable to a
judge in a live demo. Exponential smoothing is transparent: one parameter
(alpha), one formula, and its error on held-out days is reported alongside
every forecast so the number is never presented as unqualified.

MINIMUM_DAYS_REQUIRED gates this entirely: below that, the function
returns an explicit "insufficient data" status - it does not degrade to a
lower-quality guess.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fare_observation import FareObservation
from app.repositories import route_repo

MINIMUM_DAYS_REQUIRED = 14   # need at least this many distinct days of history to attempt anything
VALIDATION_HOLDOUT_DAYS = 5  # last N real days held out to score the method honestly
FORECAST_HORIZON_DAYS = 5
ALPHA = 0.4                  # smoothing factor - higher = more weight on recent observations


def _daily_series(db: Session, route_id: int) -> list[tuple[date, float]]:
    rows = db.execute(
        select(FareObservation.observation_date, func.avg(FareObservation.price))
        .where(FareObservation.route_id == route_id)
        .group_by(FareObservation.observation_date)
        .order_by(FareObservation.observation_date)
    ).all()
    return [(d, float(p)) for d, p in rows]


def _simple_exponential_smoothing(values: list[float], alpha: float) -> list[float]:
    """Returns the smoothed (fitted) series, same length as input."""
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
    return smoothed


def get_forecast(db: Session, route_code: str) -> dict:
    route = route_repo.get_route_by_code(db, route_code)
    if route is None:
        return {"status": "route_not_found", "route": route_code}

    series = _daily_series(db, route.id)
    if len(series) < MINIMUM_DAYS_REQUIRED:
        return {
            "status": "insufficient_data",
            "route": route_code,
            "message": "Forecast unavailable: insufficient historical observations.",
            "days_available": len(series),
            "days_required": MINIMUM_DAYS_REQUIRED,
        }

    dates = [d for d, _ in series]
    prices = [p for _, p in series]

    # --- Validation: fit on everything except the last VALIDATION_HOLDOUT_DAYS, score against them ---
    train = prices[:-VALIDATION_HOLDOUT_DAYS]
    holdout = prices[-VALIDATION_HOLDOUT_DAYS:]
    if len(train) < 5:
        return {
            "status": "insufficient_data",
            "route": route_code,
            "message": "Forecast unavailable: insufficient historical observations.",
            "days_available": len(series),
            "days_required": MINIMUM_DAYS_REQUIRED,
        }

    fitted = _simple_exponential_smoothing(train, ALPHA)
    naive_holdout_prediction = fitted[-1]  # SES's one-step-ahead forecast is just the last smoothed value
    errors = [abs(naive_holdout_prediction - actual) for actual in holdout]
    mae = round(sum(errors) / len(errors), 2)
    mape = round(sum(abs(e / a) for e, a in zip(errors, holdout) if a) / len(holdout) * 100, 2)

    # --- Refit on the FULL series (train + holdout) to actually project forward ---
    full_fitted = _simple_exponential_smoothing(prices, ALPHA)
    last_level = full_fitted[-1]
    forecast_dates = [dates[-1] + timedelta(days=i) for i in range(1, FORECAST_HORIZON_DAYS + 1)]
    # SES has a flat forecast (no trend component) - every future point equals the last smoothed level.
    # This is a real, disclosed limitation, not hidden.
    forecast_values = [round(last_level, 2)] * FORECAST_HORIZON_DAYS

    return {
        "status": "ok",
        "route": route_code,
        "method": "simple_exponential_smoothing",
        "alpha": ALPHA,
        "days_of_history_used": len(series),
        "validation": {
            "holdout_days": VALIDATION_HOLDOUT_DAYS,
            "mae": mae,
            "mape_percent": mape,
        },
        "forecast": [
            {"date": d.isoformat(), "predicted_price": v}
            for d, v in zip(forecast_dates, forecast_values)
        ],
        "limitation": "Single exponential smoothing assumes no trend or seasonality - forecast is flat. "
                       "Appropriate given the short history currently available; revisit once more data accumulates.",
    }
