"""
APScheduler setup.

The scheduler is started and stopped via the FastAPI lifespan in src/api/main.py.
Call start_scheduler() on startup and stop_scheduler() on shutdown.

Default schedule: weekly, Sunday 02:00 UTC.
Override via REPORT_CRON env var (standard cron syntax, e.g. "0 2 * * 0").
"""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .jobs import run_weekly_reports

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

# Default: Sunday 02:00 UTC — "0 2 * * 0"
_DEFAULT_CRON = "0 2 * * 0"


def start_scheduler() -> None:
    """Start the background scheduler. Called from FastAPI lifespan on startup."""
    global _scheduler

    cron_expr = os.environ.get("REPORT_CRON", _DEFAULT_CRON).strip()

    # Parse "min hour dom month dow" into CronTrigger kwargs
    parts = cron_expr.split()
    if len(parts) != 5:
        logger.error(
            f"Scheduler: invalid REPORT_CRON '{cron_expr}' — expected 5 fields. "
            f"Falling back to default: {_DEFAULT_CRON}"
        )
        parts = _DEFAULT_CRON.split()

    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        timezone="UTC",
    )

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_weekly_reports,
        trigger=trigger,
        id="weekly_reports",
        name="Weekly lead report generation",
        max_instances=1,          # never overlap runs
        misfire_grace_time=3600,  # allow up to 1h late if server was down
    )
    _scheduler.start()
    logger.info(f"Scheduler: started — cron '{cron_expr}' (UTC)")


def stop_scheduler() -> None:
    """Stop the background scheduler. Called from FastAPI lifespan on shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler: stopped")
    _scheduler = None
