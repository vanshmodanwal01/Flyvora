"""
APScheduler wiring for automated collection.

Why APScheduler and not Celery+Redis: the collection workload here is
"call an HTTP API for a handful of routes once an hour" - a single
in-process BackgroundScheduler job. Celery would need a broker (Redis) and
a separate worker process for no real benefit at this scale; cron would
work but gives no in-app visibility (no /api/collection/status without a
separate results store) and no shared code path with the manual-trigger
endpoint. APScheduler's BackgroundScheduler runs inside the same FastAPI
process, is trivial to start/stop from a startup/shutdown hook, and calls
the exact same run_collection() the manual endpoint calls.

Overlap prevention: APScheduler's default `max_instances=1` on the job
means a still-running collection blocks a new one from starting rather
than running concurrently - important since collection does DB writes.

Multi-worker warning: if this app is ever run with multiple Uvicorn/Gunicorn
worker processes, EACH process would start its own scheduler and you'd get
duplicate collection runs. For this prototype (single worker, `uvicorn
app.main:app`), that's not a concern - documented here so it doesn't get
missed if deployment changes.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.providers import get_provider
from app.services.collection_service import run_collection
from app.services.route_priority_service import compute_route_priority

logger = logging.getLogger("flyvora.scheduler")

_scheduler: BackgroundScheduler | None = None


def _scheduled_collection_job():
    db = SessionLocal()
    try:
        compute_route_priority(db, top_n=settings.TOP_N_ROUTES)
        provider = get_provider()
        run = run_collection(
            db, provider,
            max_routes=settings.MAX_ROUTES_PER_RUN,
            currency=settings.DEFAULT_CURRENCY,
            travel_class=settings.DEFAULT_TRAVEL_CLASS,
            trigger="scheduled",
        )
        logger.info("Scheduled collection run %s finished with status %s", run.id, run.status)
    except Exception:  # noqa: BLE001 - a scheduler job must never take the process down
        logger.exception("Scheduled collection job raised an unhandled exception")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
        return None
    if _scheduler is not None:
        return _scheduler  # already running - never start a second instance

    _scheduler = BackgroundScheduler(timezone=settings.APP_TIMEZONE)
    _scheduler.add_job(
        _scheduled_collection_job,
        "interval",
        minutes=settings.COLLECTION_INTERVAL_MINUTES,
        id="flyvora_collection_job",
        max_instances=1,          # overlap prevention
        coalesce=True,            # if a run was missed, run once, not N times back-to-back
        # No explicit next_run_time: letting APScheduler default it means
        # the first run fires one full interval from now, which is what we
        # want. Passing next_run_time=None here (an earlier version of this
        # code did) actually PAUSES the job indefinitely - verified by
        # testing, not assumed - so it's deliberately omitted.
    )
    _scheduler.start()
    logger.info("Scheduler started: collection every %d minutes", settings.COLLECTION_INTERVAL_MINUTES)
    return _scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_scheduler_status() -> dict:
    if _scheduler is None:
        return {"running": False, "next_run_time": None, "interval_minutes": settings.COLLECTION_INTERVAL_MINUTES}
    job = _scheduler.get_job("flyvora_collection_job")
    return {
        "running": _scheduler.running,
        "next_run_time": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "interval_minutes": settings.COLLECTION_INTERVAL_MINUTES,
    }
