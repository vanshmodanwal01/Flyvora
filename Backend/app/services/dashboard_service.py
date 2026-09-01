from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.route import Route
from app.repositories import analytics_repo
from app.schemas.dashboard import OverviewSummary


def get_overview_summary(db: Session) -> OverviewSummary:
    trend = analytics_repo.get_index_trend(db, weeks=8)
    national_series = trend["national"]
    current_index = national_series[-1] if national_series else 100.0

    anomalies = analytics_repo.detect_anomalies(db)

    tracked_routes = db.execute(select(Route)).scalars().all()

    # 30-day "inflation rate" here is just the index's own change over the
    # trailing window it already computed — simple and explainable, which
    # matters more for a hackathon demo than a fancier formula.
    inflation_rate = (current_index - national_series[0]) if len(national_series) > 1 else 0.0

    return OverviewSummary(
        airfareIndex=current_index,
        inflationRate=round(inflation_rate, 1),
        anomaliesDetected=len(anomalies),
        trackedRoutes=len(tracked_routes),
    )
