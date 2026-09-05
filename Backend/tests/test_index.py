import csv
from datetime import date, timedelta

from app.services.index_service import compute_and_store_index, get_index_history
from app.services.ingestion import run_ingestion


def test_index_reports_insufficient_data_when_empty(db_session):
    result = compute_and_store_index(db_session)
    assert result["status"] == "insufficient_data" or result["status"] == "no_data"


def test_index_computes_with_sufficient_synthetic_data(db_session, tmp_path):
    rows = []
    base = date.today() - timedelta(days=21)
    routes = [("DEL", "BOM"), ("DEL", "BLR"), ("BOM", "BLR")]
    for week_offset in range(3):
        week_date = base + timedelta(weeks=week_offset)
        for origin, dest in routes:
            for i in range(6):  # >= MIN_SAMPLE_SIZE
                rows.append([
                    (week_date + timedelta(days=i % 7)).isoformat(), origin, dest, "6E", "Economy", "10",
                    str(4500 + week_offset * 100), "INR",
                ])
    csv_path = tmp_path / "index_test.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"])
        writer.writerows(rows)
    run_ingestion(db_session, str(csv_path))
    db_session.commit()

    result = compute_and_store_index(db_session)
    assert result["status"] == "ok"
    assert result["periods_computed"] >= 1
    assert result["series"][0]["index_value"] == 100.0  # base period always indexes to 100

    history = get_index_history(db_session)
    assert history["status"] == "ok"
    assert "NOT an official CPI series" in history["label"]
    # Prices rose each week in the synthetic data, so the index should rise too
    assert history["current_index"] >= history["series"][0]["index_value"]
