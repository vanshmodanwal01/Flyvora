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

## Real dataset included

`data/raw/easemytrip_2022_real.csv` is a **genuine** ~300K-row fare dataset (airline, route, class, days-to-departure, price) scraped from EaseMyTrip, covering India's 6 busiest metro-pair routes (Delhi, Mumbai, Bangalore, Kolkata, Hyderabad, Chennai — per DGCA traffic data, these six handle ~71% of India's domestic passengers). Every airline, route, class, lead-time, and price value in it is real.

**One disclosed caveat:** the source doesn't publish a per-row calendar date, only a documented 48-day collection window (11 Feb – 31 Mar 2022). `scripts/prepare_real_dataset.py` deterministically distributes rows across that real window, then **replays** the whole window forward so it ends on "today" — purely so the app's trailing-30/90-day queries have something to show live. This is a disclosed placement convention, not fabricated pricing; every row is tagged `source="csv-historical-real"` and the resulting `data_sources` record says so. Run it again any time to refresh the replay window:

```bash
python scripts/prepare_real_dataset.py
python scripts/ingest.py data/raw/easemytrip_2022_prepared.csv --source-label csv-historical-real
```

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
