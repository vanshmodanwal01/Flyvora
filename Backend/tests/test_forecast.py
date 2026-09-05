import csv
from datetime import date, timedelta

from app.services.forecast_service import get_forecast
from app.services.ingestion import run_ingestion


def test_forecast_reports_insufficient_data_for_short_history(db_session, tmp_path):
    rows = [[
        (date.today() - timedelta(days=i)).isoformat(), "DEL", "BOM", "6E", "Economy", "10", "4500", "INR",
    ] for i in range(5)]  # well under MINIMUM_DAYS_REQUIRED
    csv_path = tmp_path / "short.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerows(rows)
    run_ingestion(db_session, str(csv_path))
    db_session.commit()

    result = get_forecast(db_session, "DEL-BOM")
    assert result["status"] == "insufficient_data"
    assert "insufficient historical observations" in result["message"]


def test_forecast_produces_validated_output_for_sufficient_history(db_session, tmp_path):
    rows = [[
        (date.today() - timedelta(days=i)).isoformat(), "DEL", "BOM", "6E", "Economy", "10",
        str(4500 + i * 10), "INR",
    ] for i in range(25)]
    csv_path = tmp_path / "long.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerows(rows)
    run_ingestion(db_session, str(csv_path))
    db_session.commit()

    result = get_forecast(db_session, "DEL-BOM")
    assert result["status"] == "ok"
    assert "validation" in result
    assert result["validation"]["mae"] >= 0
    assert len(result["forecast"]) == 5


def test_forecast_reports_route_not_found(db_session):
    result = get_forecast(db_session, "ZZZ-ZZZ")
    assert result["status"] == "route_not_found"
