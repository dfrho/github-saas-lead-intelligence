"""
/reports endpoints — trigger, list, fetch, and export lead reports.
"""

import asyncio
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services import registry, github_api, claude_api
from services.vendor_map import get_vendors_for_domains
from services.dependency_analyzer import analyze_dependencies
from ..auth import get_current_user, get_optional_user
from ..deps import get_db

router = APIRouter(prefix="/reports", tags=["reports"])

# Progress status messages shown to the client while a report generates
PROGRESS_STEPS = [
    "Fetching repository activity...",
    "Analyzing commits...",
    "Classifying signals...",
    "Researching company news...",
    "Profiling contributors...",
    "Scoring the lead...",
    "Almost done...",
]


# ── Pydantic models ───────────────────────────────────────────────────────────

class RunReportRequest(BaseModel):
    owner: str
    repo: str
    org_domain: str | None = None


class ScoreBreakdown(BaseModel):
    activity: int
    pain_points: int
    dependencies: int
    team_size: int
    growth: int


class ReportSummary(BaseModel):
    id: str
    owner: str
    repo: str
    run_at: str
    status: str
    score_composite: int | None
    confidence_label: str | None


class ReportDetail(ReportSummary):
    score_activity: int | None
    score_pain_points: int | None
    score_dependencies: int | None
    score_team_size: int | None
    score_growth: int | None
    markdown_body: str | None
    json_body: dict | None


# ── Scoring helpers (duplicated from main.py to keep services/ untouched) ─────

def _score_lead(commits, pull_requests, issues, contributors, news, signals, dependency_score=0, dependency_flags=None):
    activity_raw = min(len(commits) / 50, 1.0) * 0.7 + min(len(pull_requests) / 20, 1.0) * 0.3
    activity_score = round(activity_raw * 100)

    open_issues = [i for i in issues if i.get("state") == "open"]
    pain_labels = {"bug", "performance", "help wanted", "help-wanted", "security", "regression"}
    labeled_issues = sum(1 for i in open_issues if any(l.lower() in pain_labels for l in i.get("labels", [])))
    pain_raw = min(len(open_issues) / 30, 1.0) * 0.5 + min(labeled_issues / 10, 1.0) * 0.5
    pain_score = round(pain_raw * 100)

    n = len(contributors)
    if 3 <= n <= 20:
        team_raw = 1.0
    elif n < 3:
        team_raw = n / 3
    else:
        team_raw = max(0.0, 1.0 - (n - 20) / 30)
    team_score = round(team_raw * 100)

    type_weights = {"funding": 3, "launch": 2, "hiring": 1.5, "partnership": 1.5, "technical": 1, "other": 0.5}
    news_weight_sum = sum(type_weights.get(item.get("type", "other"), 0.5) for item in news)
    growth_score = round(min(news_weight_sum / 10, 1.0) * 100)

    total = round(activity_score * 0.25 + pain_score * 0.25 + dependency_score * 0.20 + team_score * 0.15 + growth_score * 0.15)

    return total, activity_score, pain_score, team_score, growth_score


def _confidence_label(score: int) -> str:
    if score >= 80:
        return "Hot lead"
    if score >= 60:
        return "Warm lead"
    if score >= 40:
        return "Lukewarm"
    return "Low priority"


# ── Background report runner ──────────────────────────────────────────────────

def _run_report_sync(report_id: str, owner: str, repo: str, org_domain: str | None, user_id: str | None):
    """
    Run a full lead report and persist the result to the reports table.
    Designed to run in a BackgroundTask (sync, not async).
    """
    db_url = os.environ["DATABASE_URL"]

    def _update_status(step: str):
        with psycopg.connect(db_url) as conn:
            conn.execute("UPDATE reports SET status = %s WHERE id = %s", (step, report_id))
            conn.commit()

    try:
        _update_status(PROGRESS_STEPS[0])
        activity = github_api.fetch_repo_activity(owner, repo)

        activity_data = {
            "owner": activity.owner,
            "repo": activity.repo,
            "commits": [{"message": c.message} for c in activity.commits],
            "pull_requests": [{"title": pr.title} for pr in activity.pull_requests],
            "issues": [{"title": i.title, "state": i.state, "labels": i.labels} for i in activity.issues],
        }

        _update_status(PROGRESS_STEPS[1])
        synopsis = claude_api.summarize_activity(activity_data)

        _update_status(PROGRESS_STEPS[2])
        signals = claude_api.classify_signal(synopsis)

        _update_status(PROGRESS_STEPS[3])
        news = claude_api.fetch_company_news(owner, org_domain)

        _update_status(PROGRESS_STEPS[4])
        contributors = github_api.fetch_contributor_profiles(owner, repo, 10)
        dep_analysis = analyze_dependencies(github_api.fetch_dependency_files(owner, repo))
        own_domains = claude_api.detect_company_own_domains(owner, org_domain)
        vendors = get_vendors_for_domains(signals, owner, list(set(own_domains)))

        _update_status(PROGRESS_STEPS[5])
        outreach_angle = claude_api.recommend_outreach_angle(synopsis, signals, news)

        issues_raw = [{"state": i.state, "labels": i.labels} for i in activity.issues]
        contributors_raw = [{"contributions": c.contributions} for c in contributors]
        total, act_score, pain_score, team_score, growth_score = _score_lead(
            activity.commits, activity.pull_requests, issues_raw, contributors_raw,
            news, signals, dep_analysis.score, dep_analysis.flags,
        )

        _update_status(PROGRESS_STEPS[6])

        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        report_json = {
            "repo": f"{owner}/{repo}",
            "generated_at": generated_at,
            "lead_score": total,
            "lead_label": _confidence_label(total),
            "score_breakdown": {
                "activity": act_score,
                "pain_points": pain_score,
                "dependencies": dep_analysis.score,
                "team_size": team_score,
                "growth": growth_score,
            },
            "synopsis": synopsis,
            "signals": signals,
            "vendors": vendors,
            "recommended_angle": outreach_angle,
            "enrichment": {
                "top_contributors": [
                    {"login": c.login, "name": c.name, "company": c.company,
                     "contributions": c.contributions, "orgs": c.orgs}
                    for c in contributors
                ],
                "company_news": news,
                "dependency_analysis": {
                    "ecosystem": dep_analysis.ecosystem,
                    "detected_packages": dep_analysis.detected_packages,
                    "flags": [{"type": f.type, "severity": f.severity, "message": f.message} for f in dep_analysis.flags],
                },
            },
        }

        # Build minimal markdown body for the DB (full rendering is done in the UI)
        md = f"# Lead Report: {owner}/{repo}\n\n**Score:** {total}/100 — {_confidence_label(total)}\n\n## Synopsis\n\n{synopsis}\n\n## Outreach Angle\n\n{outreach_angle}\n"

        with psycopg.connect(db_url) as conn:
            conn.execute(
                """
                UPDATE reports SET
                    status = 'complete',
                    score_composite = %s,
                    score_activity = %s,
                    score_pain_points = %s,
                    score_dependencies = %s,
                    score_team_size = %s,
                    score_growth = %s,
                    confidence_label = %s,
                    markdown_body = %s,
                    json_body = %s
                WHERE id = %s
                """,
                (
                    total, act_score, pain_score, dep_analysis.score, team_score, growth_score,
                    _confidence_label(total), md, json.dumps(report_json), report_id,
                ),
            )
            conn.commit()

        # Also update registry if repo is watched by this user
        if user_id:
            registry.update_registry_entry(
                owner, repo, user_id=user_id,
                last_checked=generated_at,
                last_activity_hash=activity.latest_commit_sha,
            )

    except Exception as e:
        with psycopg.connect(db_url) as conn:
            conn.execute(
                "UPDATE reports SET status = %s WHERE id = %s",
                (f"error: {str(e)[:200]}", report_id),
            )
            conn.commit()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_report(
    body: RunReportRequest,
    background_tasks: BackgroundTasks,
    user_id: str | None = Depends(get_optional_user),
    conn=Depends(get_db),
):
    """
    Trigger a full lead report. Available to unauthenticated users (pre-auth flow).
    Returns a report_id immediately; the report is generated in the background.
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reports (user_id, owner, repo, status) VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, body.owner, body.repo, PROGRESS_STEPS[0]),
        )
        report_id = str(cur.fetchone()[0])
    conn.commit()

    background_tasks.add_task(
        _run_report_sync, report_id, body.owner, body.repo, body.org_domain, user_id
    )

    return {"report_id": report_id, "status": PROGRESS_STEPS[0]}


@router.get("/status/{report_id}")
def get_report_status(report_id: str, conn=Depends(get_db)):
    """
    Poll the status of an in-progress report.
    Returns the current status string (one of PROGRESS_STEPS, 'complete', or 'error: ...').
    Used by the frontend progress indicator.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM reports WHERE id = %s", (report_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return {"report_id": report_id, "status": row[0]}


@router.get("", response_model=list[ReportSummary])
def list_reports(user_id: str = Depends(get_current_user), conn=Depends(get_db)):
    """List all completed reports for the authenticated user, newest first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, owner, repo, run_at, status, score_composite, confidence_label
            FROM reports
            WHERE user_id = %s AND status = 'complete'
            ORDER BY run_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    return [
        ReportSummary(
            id=str(r[0]), owner=r[1], repo=r[2],
            run_at=r[3].isoformat() if r[3] else "",
            status=r[4], score_composite=r[5], confidence_label=r[6],
        )
        for r in rows
    ]


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: str,
    user_id: str = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Fetch a single completed report. Only the owning user can access it.

    If the report was triggered anonymously (user_id IS NULL), it is claimed
    by the first authenticated user who views it — this supports the pre-auth
    flow where a visitor runs a report before signing in.
    """
    with conn.cursor() as cur:
        # Fetch report owned by this user OR unclaimed (pre-auth anonymous run)
        cur.execute(
            """
            SELECT id, owner, repo, run_at, status,
                   score_composite, score_activity, score_pain_points,
                   score_dependencies, score_team_size, score_growth,
                   confidence_label, markdown_body, json_body, user_id
            FROM reports
            WHERE id = %s AND (user_id = %s OR user_id IS NULL)
            """,
            (report_id, user_id),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Claim anonymous report on first authenticated access
    if row[14] is None:
        with conn.cursor() as cur:
            cur.execute("UPDATE reports SET user_id = %s WHERE id = %s", (user_id, report_id))
        conn.commit()

    return ReportDetail(
        id=str(row[0]), owner=row[1], repo=row[2],
        run_at=row[3].isoformat() if row[3] else "",
        status=row[4],
        score_composite=row[5], score_activity=row[6], score_pain_points=row[7],
        score_dependencies=row[8], score_team_size=row[9], score_growth=row[10],
        confidence_label=row[11], markdown_body=row[12],
        json_body=row[13] if isinstance(row[13], dict) else (json.loads(row[13]) if row[13] else None),
    )


@router.get("/{report_id}/export")
def export_report(
    report_id: str,
    format: str = Query(default="csv", pattern="^(csv|txt)$"),
    user_id: str = Depends(get_current_user),
    conn=Depends(get_db),
):
    """Download a report as CSV or TXT."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT owner, repo, json_body, markdown_body FROM reports WHERE id = %s AND user_id = %s",
            (report_id, user_id),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    owner, repo, json_body, markdown_body = row
    data = json_body if isinstance(json_body, dict) else (json.loads(json_body) if json_body else {})

    if format == "txt":
        content = markdown_body or f"# {owner}/{repo}\n\nNo report content available."
        return StreamingResponse(
            io.StringIO(content),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{owner}__{repo}.txt"'},
        )

    # CSV: one row per contributor, plus a summary header block
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Lead Report", f"{owner}/{repo}"])
    writer.writerow(["Score", data.get("lead_score", ""), "Label", data.get("lead_label", "")])
    writer.writerow(["Synopsis", data.get("synopsis", "")])
    writer.writerow(["Outreach Angle", data.get("recommended_angle", "")])
    writer.writerow([])
    writer.writerow(["Contributors"])
    writer.writerow(["Login", "Name", "Company", "Contributions", "Orgs"])
    for c in data.get("enrichment", {}).get("top_contributors", []):
        writer.writerow([
            c.get("login", ""), c.get("name", ""), c.get("company", ""),
            c.get("contributions", ""), ", ".join(c.get("orgs", [])),
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{owner}__{repo}.csv"'},
    )
