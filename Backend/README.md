# Flyvora Backend — Phase 1

FastAPI + PostgreSQL backend for the Flyvora (APIx) airfare price index dashboards. This is **Phase 1**: CSV ingestion, a normalized relational schema, and read APIs that mirror the existing frontend's mock data shapes. No external flight APIs, ML, or forecasting yet — see the main repo README for the full phase roadmap.

## Quick start (Docker — recommended)

```bash
cd Backend
cp .env.example .env
docker compose up --build
```

Then, in another terminal, run migrations and load some data:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/ingest.py data/raw/sample_fares.csv
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

## Quick start (without Docker)

Requires Python 3.12+ and a running PostgreSQL 16 instance.

```bash
cd Backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL to point at your local Postgres
alembic upgrade head
python scripts/ingest.py data/raw/sample_fares.csv
uvicorn app.main:app --reload
```

## CSV data contract

`scripts/ingest.py <path-to-csv>` expects these columns (case-insensitive; extra columns are ignored):

| Column | Required | Notes |
|---|---|---|
| `date` | yes | Observation date, e.g. `2026-08-27` |
| `origin` | yes | 3-letter IATA airport code |
| `destination` | yes | 3-letter IATA airport code |
| `airline` | yes | IATA code (`6E`) or name (`IndiGo`) — unrecognized carriers are still accepted and created automatically |
| `days_to_departure` | yes | Integer ≥ 0 |
| `price` | yes | Numeric > 0 |
| `travel_class` | no | `Economy` / `Business` / `First Class` — defaults to `Economy` |
| `currency` | no | Defaults to `INR` |

`data/raw/sample_fares.csv` is a **synthetic** dataset (1,780 rows, 6 routes, 5 airlines, ~45 days) generated for development and demo purposes only, with a handful of intentionally invalid rows so the Data Quality dashboard has something real to report. Replace it with actual historical fare data before relying on any numbers for the SIH submission.

## Running tests

Tests run against a real Postgres database (Postgres-specific SQL like `ON CONFLICT` doesn't work against SQLite). Create a `flyvora_test` database once:

```bash
createdb flyvora_test   # or: psql -c "CREATE DATABASE flyvora_test OWNER flyvora;"
pytest tests/ -v
```

## Regenerating a migration after changing a model

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Project structure

See the main repo README / Phase 1 architecture notes for the full folder-by-folder breakdown (`app/api`, `app/models`, `app/services`, `app/repositories`, etc.).
