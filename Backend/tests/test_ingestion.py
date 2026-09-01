import csv

from app.services.ingestion import run_ingestion


def _write_csv(path, rows, header=None):
    header = header or ["date", "origin", "destination", "airline", "travel_class", "days_to_departure", "price", "currency"]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def test_ingestion_accepts_valid_rows(db_session, tmp_path):
    csv_path = tmp_path / "valid.csv"
    _write_csv(csv_path, [
        ["2026-08-01", "DEL", "BOM", "6E", "Economy", "10", "4500", "INR"],
        ["2026-08-01", "DEL", "BOM", "AI", "Economy", "10", "4800", "INR"],
    ])

    result = run_ingestion(db_session, str(csv_path))

    assert result["status"] == "Success"
    assert result["counts"]["total"] == 2
    assert result["counts"]["valid"] == 2
    assert result["counts"]["rejected"] == 0


def test_ingestion_rejects_missing_required_field(db_session, tmp_path):
    csv_path = tmp_path / "missing.csv"
    _write_csv(csv_path, [
        ["2026-08-01", "DEL", "", "6E", "Economy", "10", "4500", "INR"],  # missing destination
    ])

    result = run_ingestion(db_session, str(csv_path))

    assert result["counts"]["missing"] == 1
    assert result["counts"]["rejected"] == 1
    assert result["counts"]["valid"] == 0
    assert "missing:destination" in result["rejected_reasons"]


def test_ingestion_rejects_invalid_price(db_session, tmp_path):
    csv_path = tmp_path / "bad_price.csv"
    _write_csv(csv_path, [
        ["2026-08-01", "DEL", "BOM", "6E", "Economy", "10", "-100", "INR"],
    ])

    result = run_ingestion(db_session, str(csv_path))

    assert result["counts"]["invalid"] == 1
    assert "invalid_price" in result["rejected_reasons"]


def test_ingestion_deduplicates_identical_rows(db_session, tmp_path):
    csv_path = tmp_path / "dupes.csv"
    row = ["2026-08-01", "DEL", "BOM", "6E", "Economy", "10", "4500", "INR"]
    _write_csv(csv_path, [row, row])  # exact duplicate within the same file

    result = run_ingestion(db_session, str(csv_path))

    assert result["counts"]["valid"] == 1
    assert result["counts"]["duplicate"] == 1


def test_ingestion_across_two_runs_deduplicates_against_existing_data(db_session, tmp_path):
    row = ["2026-08-01", "DEL", "BOM", "6E", "Economy", "10", "4500", "INR"]
    first_csv = tmp_path / "run1.csv"
    second_csv = tmp_path / "run2.csv"
    _write_csv(first_csv, [row])
    _write_csv(second_csv, [row])  # same quote, re-ingested in a second job

    first = run_ingestion(db_session, str(first_csv))
    second = run_ingestion(db_session, str(second_csv))

    assert first["counts"]["valid"] == 1
    assert second["counts"]["valid"] == 0
    assert second["counts"]["duplicate"] == 1


def test_ingestion_fails_cleanly_on_missing_columns(db_session, tmp_path):
    csv_path = tmp_path / "malformed.csv"
    with open(csv_path, "w", newline="") as f:
        f.write("origin,destination\nDEL,BOM\n")

    try:
        run_ingestion(db_session, str(csv_path))
        assert False, "expected ValueError for missing required columns"
    except ValueError as exc:
        assert "missing required columns" in str(exc)
