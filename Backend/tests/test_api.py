import csv
import random
from datetime import date, timedelta

import pytest

from app.services.ingestion import run_ingestion


@pytest.fixture
def seeded_db(db_session, tmp_path):
    """Ingest a small but real dataset so every endpoint has something to return."""
    random.seed(7)
    rows = []
    today = date(2026, 8, 27)
    routes = [("DEL", "BOM"), ("BLR", "HYD")]
    airlines = ["6E", "AI", "SG"]
    for day_offset in range(20):
        obs_date = today - timedelta(days=day_offset)
        for origin, destination in routes:
            for airline in airlines:
                rows.append([
                    obs_date.isoformat(), origin, destination, airline, "Economy",
                    random.choice([1, 5, 10, 20, 30]), round(random.uniform(3500, 6000), 2), "INR",
                ])

    csv_path = tmp_path / "seed.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerows(rows)

    run_ingestion(db_session, str(csv_path))
    db_session.commit()
    return db_session


@pytest.mark.parametrize("path", [
    "/api/dashboard/overview/summary",
    "/api/routes",
    "/api/routes/ranking",
    "/api/airlines/comparison",
    "/api/airlines/route-matrix",
    "/api/airlines/index-trend",
    "/api/analytics/index-trend",
    "/api/analytics/lead-time",
    "/api/analytics/lead-time/checkpoints",
    "/api/analytics/anomalies",
    "/api/data-quality/summary",
    "/api/data-quality/validation-rate",
    "/api/data-quality/ingestion-volume",
    "/api/data-quality/sources",
    "/api/data-quality/runs",
])
def test_endpoint_returns_200(client, seeded_db, path):
    response = client.get(path)
    assert response.status_code == 200, response.text


def test_route_summary_matches_frontend_shape(client, seeded_db):
    response = client.get("/api/routes/DEL-BOM/summary")
    assert response.status_code == 200
    body = response.json()
    for key in ("name", "avgFare", "change30D", "changeTrend", "weight", "observations", "airlines", "labels", "routePrices", "nationalAvgPrices"):
        assert key in body


def test_route_summary_404_for_unknown_route(client, seeded_db):
    response = client.get("/api/routes/ZZZ-ZZZ/summary")
    assert response.status_code == 404


def test_lead_time_compare_requires_routes_param(client, seeded_db):
    response = client.get("/api/analytics/lead-time/compare")
    assert response.status_code == 422  # required query param missing
