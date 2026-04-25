"""
Scheduled job definitions.

run_weekly_reports() is the single job registered with APScheduler.
It queries every distinct (user_id, owner, repo) row in watched_repos,
skips repos where last_activity_hash hasn't changed, and calls the
report runner from the reports router for each qualifying repo.
"""

import logging
import os
import time

import psycopg

logger = logging.getLogger(__name__)


def run_weekly_reports() -> None:
    """
    Entry point for the weekly scheduled job.

    For each watched repo in the DB:
    - Fetch the current head commit SHA from GitHub
    - Skip if it matches last_activity_hash (no new activity)
    - Otherwise trigger a full report run and persist to DB
    - On failure: log the error and continue to next repo (no silent failures)
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from services import github_api, registry
    from api.routers.reports import _run_report_sync

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("Scheduler: DATABASE_URL not set — skipping weekly run")
        return

    # Fetch all (user_id, owner, repo, last_activity_hash) rows
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, owner, repo, last_activity_hash FROM watched_repos"
                )
                watched = cur.fetchall()
    except Exception as e:
        logger.error(f"Scheduler: failed to read watched_repos: {e}")
        return

    if not watched:
        logger.info("Scheduler: no watched repos found — nothing to do")
        return

    logger.info(f"Scheduler: starting weekly run for {len(watched)} repos")

    for user_id, owner, repo, last_hash in watched:
        try:
            _run_one_repo(
                db_url=db_url,
                user_id=str(user_id) if user_id else None,
                owner=owner,
                repo=repo,
                last_hash=last_hash,
                github_api=github_api,
                run_report_sync=_run_report_sync,
            )
        except Exception as e:
            logger.error(f"Scheduler: unexpected error for {owner}/{repo}: {e}")


def _run_one_repo(*, db_url, user_id, owner, repo, last_hash, github_api, run_report_sync):
    """Process a single repo — check for new activity then run the report."""
    try:
        activity = github_api.fetch_repo_activity(owner, repo)
    except Exception as e:
        logger.error(f"Scheduler: failed to fetch activity for {owner}/{repo}: {e}")
        _retry_once(
            fn=lambda: _do_run(db_url, user_id, owner, repo, run_report_sync),
            owner=owner,
            repo=repo,
        )
        return

    if last_hash and activity.latest_commit_sha == last_hash:
        logger.info(f"Scheduler: {owner}/{repo} — no new activity, skipping")
        return

    logger.info(f"Scheduler: {owner}/{repo} — new activity detected, running report")
    _retry_once(
        fn=lambda: _do_run(db_url, user_id, owner, repo, run_report_sync),
        owner=owner,
        repo=repo,
    )


def _do_run(db_url, user_id, owner, repo, run_report_sync):
    """Insert a pending report row and run the full report sync."""
    import uuid
    report_id = str(uuid.uuid4())

    with psycopg.connect(db_url) as conn:
        conn.execute(
            "INSERT INTO reports (id, user_id, owner, repo, status) VALUES (%s, %s, %s, %s, %s)",
            (report_id, user_id, owner, repo, "Fetching repository activity..."),
        )
        conn.commit()

    run_report_sync(report_id, owner, repo, org_domain=None, user_id=user_id)
    logger.info(f"Scheduler: {owner}/{repo} — report {report_id} complete")


def _retry_once(fn, owner: str, repo: str, delay: int = 1800) -> None:
    """
    Run fn(). If it raises, wait `delay` seconds and try once more.
    Logs the error on both failure and final failure — no silent failures.
    """
    try:
        fn()
    except Exception as e:
        logger.error(f"Scheduler: {owner}/{repo} failed ({e}), retrying in {delay}s")
        time.sleep(delay)
        try:
            fn()
        except Exception as e2:
            logger.error(f"Scheduler: {owner}/{repo} retry also failed: {e2}")
