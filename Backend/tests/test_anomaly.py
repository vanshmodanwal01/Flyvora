import csv
from datetime import date, timedelta

from app.services.ingestion import run_ingestion


def test_structured_anomaly_reports_insufficient_data_for_thin_route(client, db_session, tmp_path):
    csv_path = tmp_path / "thin.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerow([date.today().isoformat(), "DEL", "BOM", "6E", "Economy", "10", "4500", "INR"])
    run_ingestion(db_session, str(csv_path))
    db_session.commit()

    response = client.get("/api/analytics/anomalies/detail")
    assert response.status_code == 200
    body = response.json()
    thin_route = next(r for r in body if r["route"] == "DEL-BOM")
    assert thin_route["status"] == "insufficient_historical_data"
    assert thin_route["is_anomaly"] is False
    assert thin_route["severity"] is None


def test_structured_anomaly_flags_real_spike(client, db_session, tmp_path):
    rows = [[
        (date.today() - timedelta(days=i)).isoformat(), "DEL", "BOM", "6E", "Economy", "10", "4500", "INR",
    ] for i in range(1, 11)]  # strictly BEFORE today, so today's spike is unambiguously the latest date
    rows.append([date.today().isoformat(), "DEL", "BOM", "6E", "Economy", "10", "50000", "INR"])  # genuine spike, today

    csv_path = tmp_path / "spike.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerows(rows)
    run_ingestion(db_session, str(csv_path))
    db_session.commit()

    response = client.get("/api/analytics/anomalies/detail")
    body = response.json()
    route = next(r for r in body if r["route"] == "DEL-BOM")
    assert route["status"] == "evaluated"
    assert route["is_anomaly"] is True
    assert route["severity"] in ("HIGH", "MEDIUM")
    assert route["z_score"] > 2
