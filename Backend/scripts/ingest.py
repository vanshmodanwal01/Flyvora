#!/usr/bin/env python3
"""
CLI entrypoint for CSV ingestion.

Usage:
    python scripts/ingest.py data/raw/flights.csv

Run inside the backend container:
    docker compose exec backend python scripts/ingest.py data/raw/flights.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.services.ingestion import run_ingestion  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Ingest a CSV of historical flight fares into Flyvora.")
    parser.add_argument("csv_path", help="Path to the CSV file to ingest")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        result = run_ingestion(db, str(csv_path))
    except ValueError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    counts = result["counts"]
    print(f"Job #{result['job_id']} — status: {result['status']}")
    print(f"  total:     {counts['total']}")
    print(f"  valid:     {counts['valid']}")
    print(f"  invalid:   {counts['invalid']}")
    print(f"  duplicate: {counts['duplicate']}")
    print(f"  missing:   {counts['missing']}")
    print(f"  rejected:  {counts['rejected']}")
    if result["rejected_reasons"]:
        print("  rejection reasons:")
        for reason, count in sorted(result["rejected_reasons"].items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count}")


if __name__ == "__main__":
    main()
