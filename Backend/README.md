# Flyvora Backend — SIH26056

FastAPI + PostgreSQL backend for Flyvora, an airfare price monitoring prototype for **SIH26056** (MoSPI/DIID — "Development of a Real-time Airfare Price Index for India through Automated Web Scraping of Airline and Online Travel Aggregator Portals for Augmentation of the Consumer Price Index (CPI)").

This is a **prototype**, not a production/national-scale system. It intentionally covers a small, real, evidence-based set of high-priority routes rather than claiming full national coverage.

## What's real vs. what's a labeled prototype convention

- **Real**: the ~300K-row historical fare dataset (`data/raw/easemytrip_2022_real.csv`, genuine EaseMyTrip fares), the SerpApi provider integration (built against SerpApi's current documented API), all analytics, the Airfare Price Index computation, anomaly detection, and forecasting — all computed from actual stored data.
- **Disclosed convention, not fabrication**: the historical dataset's search dates are replayed forward to end "today" (see `scripts/prepare_real_dataset.py` docstring) so trailing-30-day queries have something to show — the real prices/routes/lead-times are untouched.
- **Route priority ("Flyvora Prototype Route Priority")**: a data-driven score from Flyvora's own observation frequency — explicitly **not** an official passenger-traffic ranking.
- **Price Index ("Flyvora Airfare Price Index — Prototype")**: an explainable route-weighted basket methodology — explicitly **not** an official CPI series.
- **Live SerpApi collection**: fully implemented and tested (with fixture-based unit tests matching SerpApi's real documented schema), but **not live-verified** — as shipped, `.env` has no `SERPAPI_API_KEY`, so the provider runs in disabled mode. See "Live data" below.

## Quick start (Docker)

```bash
cd Backend
cp .env.example .env   # fill in SERPAPI_API_KEY if you have one - optional, everything works without it
docker compose up --build
```

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/ingest.py data/raw/easemytrip_2022_prepared.csv --source-label csv-historical-real
```

**Docker status: config reviewed and statically validated (YAML parses, env vars wired correctly) but NOT executed in the environment this was built in — no Docker daemon was available there. Verify `docker compose up --build` yourself before relying on it.**

API docs: http://localhost:8000/docs

## Quick start (without Docker)

```bash
cd Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit DATABASE_URL to your local Postgres
alembic upgrade head
python scripts/prepare_real_dataset.py
python scripts/ingest.py data/raw/easemytrip_2022_prepared.csv --source-label csv-historical-real
uvicorn app.main:app --reload
```

## Live data (SerpApi)

Set `SERPAPI_API_KEY` in `.env` to enable live collection. Without it, every collection attempt returns a clear `"provider-disabled mode"` status — the rest of the system (historical analytics, index, anomalies) works fully either way.

```bash
curl -X POST http://localhost:8000/api/collection/run
curl http://localhost:8000/api/collection/status
curl http://localhost:8000/api/collection/provider-health   # never returns the key itself
```

The scheduler (APScheduler, in-process — see `app/core/scheduler.py` for why not Celery/Redis) runs automatically every `COLLECTION_INTERVAL_MINUTES` (default 60) once the app starts, collecting up to `MAX_ROUTES_PER_RUN` (default 5) routes selected by `/api/collection/route-priority`.

## Key environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SERPAPI_API_KEY` | *(empty)* | SerpApi key. Empty = provider-disabled mode. |
| `COLLECTION_INTERVAL_MINUTES` | 60 | Scheduler interval |
| `MAX_ROUTES_PER_RUN` | 5 | Routes collected per run (credit-conscious) |
| `TOP_N_ROUTES` | 5 | Routes kept in the priority list |
| `DEFAULT_CURRENCY` | INR | |
| `DEFAULT_TRAVEL_CLASS` | 1 (Economy) | SerpApi's own 1-4 encoding |
| `SCHEDULER_ENABLED` | true | Set false to disable automated collection entirely |

## New API groups (this phase)

- `POST /api/collection/run`, `GET /api/collection/status`, `GET /api/collection/provider-health`, `GET /api/collection/route-priority` — all unauthenticated by design for this prototype/demo; never expose the API key.
- `GET /api/index`, `POST /api/index/recompute` — Flyvora Airfare Price Index (Prototype)
- `GET /api/forecast/{route_code}` — returns `"insufficient_data"` explicitly when a route has under 14 days of history; otherwise a validated (train/holdout MAE+MAPE reported) simple-exponential-smoothing forecast.
- `GET /api/analytics/anomalies/detail` — structured per-route anomaly output (entity, current/expected price, z-score, method, severity, `insufficient_historical_data` status for thin routes).

## Testing

```bash
createdb flyvora_test   # once
pytest tests/ -v
```

48 tests as of this phase, covering CSV ingestion, the SerpApi provider (fixture-based, no live call), the collection orchestrator (including a direct test of the historical-observation rule — same route collected at two different timestamps produces two rows, not a dedup collision), route priority scoring, the price index, anomaly detection, and forecasting.

## Known limitations (stated plainly)

- No live SerpApi call has actually been verified end-to-end — the `.env` shipped with this build has no key, and this environment's sandbox couldn't reach `serpapi.com` even with one. Verify on your own machine.
- Lucknow does not appear in the real historical dataset (it only covers 6 metros) — the route-priority mechanism will not surface it until real data exists for it.
- The price index and route priority are prototype methodologies, disclosed as such — not official statistical products.
- Forecasting uses single exponential smoothing (flat forecast, no trend/seasonality) — appropriate for the short history currently available, not a long-term forecasting solution.
- Docker Compose has not been executed in this environment (no daemon available) — config is reviewed and should work but wasn't run.
