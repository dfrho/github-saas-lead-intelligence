import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from mcp.server import Server
from mcp.types import TextContent, Tool
import mcp.server.stdio
from dotenv import load_dotenv

load_dotenv()

from services import registry, github_api, claude_api
from services.vendor_map import get_vendors_for_domains
from services.dependency_analyzer import analyze_dependencies


# Initialize MCP server
server = Server("github-lead-intelligence")


@server.call_tool()
async def watch_repo(
    owner: str,
    repo: str,
    label: str = None,
) -> list[TextContent]:
    """
    Add a GitHub repository to the watched-repo registry so it can be monitored
    for engineering activity.
    """
    resolved_label = label or f"{owner}/{repo}"
    created, entry = registry.add_watched_repo(owner, repo, resolved_label)

    if created:
        message = f"Watching {owner}/{repo} (label: \"{resolved_label}\"). Added at {entry.added_at}."
    else:
        message = f"{owner}/{repo} is already in the registry (added {entry.added_at})."

    return [TextContent(type="text", text=message)]


@server.call_tool()
async def list_watched_repos() -> list[TextContent]:
    """List all repositories currently in the watched-repo registry."""
    entries = registry.list_watched_repos()

    if not entries:
        message = "No repositories are currently being watched."
    else:
        rows = []
        for entry in entries:
            checked = f"last checked {entry.last_checked}" if entry.last_checked else "never checked"
            rows.append(f"• {entry.owner}/{entry.repo} — \"{entry.label}\" ({checked})")
        message = "\n".join(rows)

    return [TextContent(type="text", text=message)]


@server.call_tool()
async def fetch_repo_activity(
    owner: str,
    repo: str,
    since: str = None,
    force: bool = False,
) -> list[TextContent]:
    """
    Fetch recent commits, pull requests, and issues for a repository.
    Uses last_activity_hash to skip repos with no new commits. Updates
    last_checked and last_activity_hash in the registry.
    """
    # Check registry for last known state
    entries = registry.list_watched_repos()
    entry = next(
        (
            e
            for e in entries
            if e.owner.lower() == owner.lower() and e.repo.lower() == repo.lower()
        ),
        None,
    )

    activity = github_api.fetch_repo_activity(owner, repo, since)

    # Skip if no new activity (same head commit) unless forced
    if (
        not force
        and entry
        and entry.last_activity_hash
        and activity.latest_commit_sha == entry.last_activity_hash
    ):
        message = (
            f"No new activity for {owner}/{repo} since last check "
            f"(head: {activity.latest_commit_sha})."
        )
        return [TextContent(type="text", text=message)]

    # Persist updated state if this repo is in the registry
    if entry:
        registry.update_registry_entry(
            owner,
            repo,
            last_checked=activity.fetched_at,
            last_activity_hash=activity.latest_commit_sha,
        )

    # Build summary text
    summary_lines = [
        f"Activity for {owner}/{repo} since {activity.since}:",
        f"  Commits:       {len(activity.commits)}",
        f"  Pull requests: {len(activity.pull_requests)}",
        f"  Issues:        {len(activity.issues)}",
        f"  Latest SHA:    {activity.latest_commit_sha or 'none'}",
    ]
    summary = "\n".join(summary_lines)

    # Also include full JSON
    activity_json = json.dumps(
        {
            "owner": activity.owner,
            "repo": activity.repo,
            "fetched_at": activity.fetched_at,
            "since": activity.since,
            "commits": [
                {
                    "sha": c.sha,
                    "author": c.author,
                    "date": c.date,
                    "message": c.message,
                }
                for c in activity.commits
            ],
            "pull_requests": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "merged_at": pr.merged_at,
                }
                for pr in activity.pull_requests
            ],
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "labels": issue.labels,
                    "created_at": issue.created_at,
                    "closed_at": issue.closed_at,
                    "comments": issue.comments,
                }
                for issue in activity.issues
            ],
            "latest_commit_sha": activity.latest_commit_sha,
        },
        indent=2,
    )

    return [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=activity_json),
    ]


@server.call_tool()
async def analyze_repo(
    owner: str,
    repo: str,
    since: str = None,
) -> list[TextContent]:
    """
    Summarize recent GitHub activity for a repository and classify it into
    SaaS domain categories in a single call. Chains summarize_activity →
    classify_signal and returns both the synopsis and the ranked domain list.
    """
    activity = github_api.fetch_repo_activity(owner, repo, since)

    activity_data = {
        "owner": activity.owner,
        "repo": activity.repo,
        "commits": [{"message": c.message} for c in activity.commits],
        "pull_requests": [{"title": pr.title} for pr in activity.pull_requests],
        "issues": [{"title": i.title} for i in activity.issues],
    }

    synopsis = claude_api.summarize_activity(activity_data)
    classifications = claude_api.classify_signal(synopsis)

    output = {
        "owner": owner,
        "repo": repo,
        "synopsis": synopsis,
        "signals": classifications,
    }

    summary_lines = [
        f"Analysis for {owner}/{repo}",
        f"\nSynopsis:\n{synopsis}",
        f"\nSignals ({len(classifications)} domains matched):",
    ]
    for c in classifications:
        summary_lines.append(f"  [{c.get('confidence', '?').upper()}] {c.get('domain')} — {c.get('reasoning')}")

    return [
        TextContent(type="text", text="\n".join(summary_lines)),
        TextContent(type="text", text=json.dumps(output, indent=2)),
    ]


@server.call_tool()
async def fetch_contributor_profiles(
    owner: str,
    repo: str,
    max_contributors: int = 10,
) -> list[TextContent]:
    """
    Fetch GitHub profile data for the top contributors of a repository:
    name, company, location, bio, follower count, and public org memberships.
    """
    profiles = github_api.fetch_contributor_profiles(owner, repo, max_contributors)

    rows = []
    for p in profiles:
        orgs_str = ", ".join(p.orgs) if p.orgs else "none"
        rows.append(
            f"• {p.login} ({p.contributions} commits)\n"
            f"  Name:     {p.name or '—'}\n"
            f"  Company:  {p.company or '—'}\n"
            f"  Location: {p.location or '—'}\n"
            f"  Orgs:     {orgs_str}\n"
            f"  Bio:      {p.bio or '—'}"
        )
    summary = f"Top {len(profiles)} contributors for {owner}/{repo}:\n\n" + "\n\n".join(rows)

    profiles_json = json.dumps(
        [
            {
                "login": p.login,
                "name": p.name,
                "company": p.company,
                "location": p.location,
                "bio": p.bio,
                "public_repos": p.public_repos,
                "followers": p.followers,
                "contributions": p.contributions,
                "orgs": p.orgs,
            }
            for p in profiles
        ],
        indent=2,
    )

    return [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=profiles_json),
    ]


@server.call_tool()
async def summarize_activity(
    owner: str,
    repo: str,
    since: str = None,
    force: bool = False,
) -> list[TextContent]:
    """
    Fetch recent GitHub activity for a repository and use Claude to produce a
    2-3 sentence technical synopsis of what the team is actively building.
    """
    activity = github_api.fetch_repo_activity(owner, repo, since)

    activity_data = {
        "owner": activity.owner,
        "repo": activity.repo,
        "commits": [{"message": c.message} for c in activity.commits],
        "pull_requests": [{"title": pr.title} for pr in activity.pull_requests],
        "issues": [{"title": i.title} for i in activity.issues],
    }

    synopsis = claude_api.summarize_activity(activity_data)
    return [TextContent(type="text", text=synopsis)]


@server.call_tool()
async def classify_signal(
    summary: str,
) -> list[TextContent]:
    """
    Map an activity synopsis to SaaS domain categories with confidence levels.
    Returns a ranked list of {domain, confidence, reasoning} objects.
    """
    classifications = claude_api.classify_signal(summary)
    return [TextContent(type="text", text=json.dumps(classifications, indent=2))]


@server.call_tool()
async def fetch_company_news(
    owner: str,
    org_domain: str = None,
) -> list[TextContent]:
    """
    Search for recent news about the company behind a GitHub org: funding,
    product launches, technical blog posts, hiring surges, and partnerships.
    Optionally provide org_domain (e.g. "stripe.com") to improve search targeting.
    """
    news = claude_api.fetch_company_news(owner, org_domain)

    if not news:
        return [TextContent(type="text", text=f"No recent news found for {owner}.")]

    rows = []
    for item in news:
        rows.append(
            f"[{item.get('type', 'other').upper()}] {item.get('title', '')}\n"
            f"  Date:    {item.get('date', '—')}\n"
            f"  URL:     {item.get('url', '—')}\n"
            f"  Summary: {item.get('snippet', '')}"
        )
    summary_text = f"News for {owner} ({len(news)} results):\n\n" + "\n\n".join(rows)

    return [
        TextContent(type="text", text=summary_text),
        TextContent(type="text", text=json.dumps(news, indent=2)),
    ]


@server.call_tool()
async def recommend_saas_vendors(
    domains: list,
) -> list[TextContent]:
    """
    Map classified domain signals to curated SaaS vendor recommendations.
    Only returns vendors for high and medium confidence signals.
    Accepts the signals list output from classify_signal or analyze_repo.
    """
    results = get_vendors_for_domains(domains)

    if not results:
        return [TextContent(type="text", text="No vendor recommendations for the provided signals (low confidence or unrecognized domains).")]

    rows = []
    for r in results:
        vendor_lines = "\n".join(
            f"    • {v['name']} ({v['url']}) — {v['pitch']}"
            for v in r["vendors"]
        )
        rows.append(
            f"[{r['confidence'].upper()}] {r['domain']}\n"
            f"  Signal: {r['reasoning']}\n"
            f"  Vendors:\n{vendor_lines}"
        )

    return [
        TextContent(type="text", text="\n\n".join(rows)),
        TextContent(type="text", text=json.dumps(results, indent=2)),
    ]


def _score_lead(
    commits: list,
    pull_requests: list,
    issues: list,
    contributors: list,
    news: list,
    signals: list,
    dependency_score: int = 0,
    dependency_flags: list = None,
) -> tuple[int, dict]:
    """
    Score a lead 0–100 based on activity, pain points, dependencies, team size, and growth.
    Returns (total_score, score_breakdown).
    """
    # Activity score (25%): commit + PR volume
    activity_raw = min(len(commits) / 50, 1.0) * 0.7 + min(len(pull_requests) / 20, 1.0) * 0.3
    activity_score = round(activity_raw * 100)

    # Pain points score (25%): open issues + bug/perf/help-wanted labels
    open_issues = [i for i in issues if i.get("state") == "open"]
    pain_labels = {"bug", "performance", "help wanted", "help-wanted", "security", "regression"}
    labeled_issues = sum(
        1 for i in open_issues
        if any(l.lower() in pain_labels for l in i.get("labels", []))
    )
    pain_raw = min(len(open_issues) / 30, 1.0) * 0.5 + min(labeled_issues / 10, 1.0) * 0.5
    pain_score = round(pain_raw * 100)

    # Team size score (15%): sweet spot is 3–20 contributors
    n = len(contributors)
    if 3 <= n <= 20:
        team_raw = 1.0
    elif n < 3:
        team_raw = n / 3
    else:
        team_raw = max(0.0, 1.0 - (n - 20) / 30)
    team_score = round(team_raw * 100)

    # Growth score (15%): news items weighted by type
    type_weights = {"funding": 3, "launch": 2, "hiring": 1.5, "partnership": 1.5, "technical": 1, "other": 0.5}
    news_weight_sum = sum(type_weights.get(n.get("type", "other"), 0.5) for n in news)
    growth_raw = min(news_weight_sum / 10, 1.0)
    growth_score = round(growth_raw * 100)

    dep_flag_messages = [f.message for f in (dependency_flags or [])]

    total = round(
        activity_score * 0.25
        + pain_score * 0.25
        + dependency_score * 0.20
        + team_score * 0.15
        + growth_score * 0.15
    )

    breakdown = {
        "activity":     {"score": activity_score,    "weight": 0.25, "signals": [f"{len(commits)} commits, {len(pull_requests)} PRs"]},
        "pain_points":  {"score": pain_score,         "weight": 0.25, "signals": [f"{len(open_issues)} open issues, {labeled_issues} with pain labels"]},
        "dependencies": {"score": dependency_score,   "weight": 0.20, "signals": dep_flag_messages or ["no dependency files found"]},
        "team_size":    {"score": team_score,          "weight": 0.15, "signals": [f"{n} contributors"]},
        "growth":       {"score": growth_score,        "weight": 0.15, "signals": [f"{len(news)} news items"]},
    }

    return total, breakdown


def _score_label(score: int) -> str:
    if score >= 80:
        return "Hot lead"
    if score >= 60:
        return "Warm lead"
    if score >= 40:
        return "Lukewarm"
    return "Low priority"


def _write_report(owner: str, repo: str, report: dict) -> Path:
    """Write the report JSON and Markdown to reports/ and return the file path."""
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = reports_dir / f"{owner}__{repo}__{date_str}"

    # Write JSON
    with open(f"{base}.json", "w") as f:
        json.dump(report, f, indent=2)

    # Write Markdown
    score = report["lead_score"]
    bd = report["score_breakdown"]
    signals = report.get("signals", [])
    vendors = report.get("vendors", [])
    contributors = report.get("enrichment", {}).get("top_contributors", [])
    news = report.get("enrichment", {}).get("company_news", [])
    dep_analysis = report.get("enrichment", {}).get("dependency_analysis", {})
    dep_flags = dep_analysis.get("flags", [])
    dep_ecosystem = dep_analysis.get("ecosystem", "unknown")

    signal_lines = "\n".join(
        f"- [{s.get('confidence','?').upper()}] **{s.get('domain')}** — {s.get('reasoning','')}"
        for s in signals
    ) or "- No signals detected"

    vendor_lines = ""
    for v_entry in vendors:
        vendor_lines += f"\n### {v_entry['domain']} ({v_entry['confidence']})\n"
        for v in v_entry["vendors"]:
            vendor_lines += f"- **[{v['name']}]({v['url']})** — {v['pitch']}\n"

    contributor_lines = "\n".join(
        f"- **{c.get('login')}** ({c.get('contributions')} commits)"
        + (f" — {c.get('company')}" if c.get('company') else "")
        for c in contributors[:5]
    ) or "- No contributor data"

    news_lines = "\n".join(
        f"- [{n.get('type','other').upper()}] **{n.get('title','')}** ({n.get('date','')}) — {n.get('snippet','')}"
        for n in news
    ) or "- No recent news found"

    dep_lines = "\n".join(
        f"- [{f.get('severity','?').upper()}] {f.get('message','')}"
        for f in dep_flags
    ) or "- No dependency flags detected"

    md = f"""# Lead Report: {owner}/{repo}

**Lead Score:** {score}/100 — {_score_label(score)}
**Generated:** {report['generated_at']}

## Score Breakdown

| Component    | Score | Weight |
|--------------|-------|--------|
| Activity     | {bd['activity']['score']}    | 25%    |
| Pain Points  | {bd['pain_points']['score']}    | 25%    |
| Dependencies | {bd['dependencies']['score']}     | 20%    |
| Team Size    | {bd['team_size']['score']}    | 15%    |
| Growth       | {bd['growth']['score']}    | 15%    |

## Synopsis

{report.get('synopsis', '')}

## Domain Signals

{signal_lines}

## Vendor Recommendations
{vendor_lines}
## Top Contributors

{contributor_lines}

## Company News

{news_lines}

## Dependency Signals (Ecosystem: {dep_ecosystem})

{dep_lines}

## Recommended Outreach Angle

{report.get('recommended_angle', '')}
"""

    with open(f"{base}.md", "w") as f:
        f.write(md)

    return Path(f"{base}.md")


@server.call_tool()
async def generate_lead_report(
    owner: str,
    repo: str,
    since: str = None,
    org_domain: str = None,
    exclude_domains: list = None,
) -> list[TextContent]:
    """
    Full orchestration: fetches activity, summarizes, classifies, fetches contributor
    profiles and company news in parallel, recommends vendors and outreach angle,
    scores the lead, and writes a Markdown + JSON report to reports/.
    """
    # Step 1: fetch raw activity (must be first — everything depends on it)
    activity = github_api.fetch_repo_activity(owner, repo, since)

    activity_data = {
        "owner": activity.owner,
        "repo": activity.repo,
        "commits": [{"message": c.message} for c in activity.commits],
        "pull_requests": [{"title": pr.title} for pr in activity.pull_requests],
        "issues": [
            {"title": i.title, "state": i.state, "labels": i.labels}
            for i in activity.issues
        ],
    }

    # Step 2: summarize then classify (sequential — classify depends on synopsis)
    synopsis = await asyncio.get_event_loop().run_in_executor(
        None, claude_api.summarize_activity, activity_data
    )
    signals = await asyncio.get_event_loop().run_in_executor(
        None, claude_api.classify_signal, synopsis
    )

    # Step 3: parallel — contributors, news, own-domain detection, and deps are all independent
    contributors_future = asyncio.get_event_loop().run_in_executor(
        None, github_api.fetch_contributor_profiles, owner, repo, 10
    )
    news_future = asyncio.get_event_loop().run_in_executor(
        None, claude_api.fetch_company_news, owner, org_domain
    )
    own_domains_future = asyncio.get_event_loop().run_in_executor(
        None, claude_api.detect_company_own_domains, owner, org_domain
    )
    deps_future = asyncio.get_event_loop().run_in_executor(
        None, lambda: analyze_dependencies(github_api.fetch_dependency_files(owner, repo))
    )

    contributors, news, detected_own_domains, dep_analysis = await asyncio.gather(
        contributors_future, news_future, own_domains_future, deps_future
    )

    # Merge auto-detected own domains with any manually passed exclusions
    all_exclude_domains = list(set(detected_own_domains) | set(exclude_domains or []))

    vendors_future = asyncio.get_event_loop().run_in_executor(
        None, get_vendors_for_domains, signals, owner, all_exclude_domains
    )
    vendors = await vendors_future

    # Step 4: outreach angle (depends on signals + news)
    outreach_angle = await asyncio.get_event_loop().run_in_executor(
        None, claude_api.recommend_outreach_angle, synopsis, signals, news
    )

    # Step 5: score
    issues_raw = [
        {"state": i.state, "labels": i.labels}
        for i in activity.issues
    ]
    contributors_raw = [{"contributions": c.contributions} for c in contributors]
    lead_score, score_breakdown = _score_lead(
        activity.commits, activity.pull_requests, issues_raw, contributors_raw, news, signals,
        dependency_score=dep_analysis.score,
        dependency_flags=dep_analysis.flags,
    )

    # Step 6: assemble report
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report = {
        "repo": f"{owner}/{repo}",
        "generated_at": generated_at,
        "lead_score": lead_score,
        "lead_label": _score_label(lead_score),
        "score_breakdown": score_breakdown,
        "synopsis": synopsis,
        "signals": signals,
        "vendors": vendors,
        "recommended_angle": outreach_angle,
        "enrichment": {
            "top_contributors": [
                {
                    "login": c.login,
                    "name": c.name,
                    "company": c.company,
                    "contributions": c.contributions,
                    "orgs": c.orgs,
                }
                for c in contributors
            ],
            "company_news": news,
            "dependency_analysis": {
                "ecosystem": dep_analysis.ecosystem,
                "detected_packages": dep_analysis.detected_packages,
                "flags": [
                    {"type": f.type, "severity": f.severity, "message": f.message}
                    for f in dep_analysis.flags
                ],
            },
        },
    }

    # Step 7: write files
    report_path = _write_report(owner, repo, report)

    return [
        TextContent(type="text", text=f"Report written to {report_path}"),
        TextContent(type="text", text=json.dumps(report, indent=2)),
    ]


@server.call_tool()
async def run_full_analysis(
    owner: str,
    repo: str,
    since: str = None,
    org_domain: str = None,
    exclude_domains: list = None,
) -> list[TextContent]:
    """
    Single top-level call to generate a complete lead report for a repository.
    Runs all enrichment, scoring, and report generation in one command.
    Returns a console-friendly summary and the report file path.
    """
    results = await generate_lead_report(owner, repo, since, org_domain, exclude_domains)

    # results[0] is the file path line, results[1] is full JSON
    report = json.loads(results[1].text)

    score = report["lead_score"]
    label = report["lead_label"]
    top_signals = [
        f"  [{s.get('confidence','?').upper()}] {s.get('domain')}"
        for s in report.get("signals", [])[:3]
    ]
    signals_str = "\n".join(top_signals) or "  None detected"

    summary = (
        f"Analysis complete for {owner}/{repo}\n\n"
        f"Lead Score:  {score}/100 — {label}\n"
        f"Top Signals:\n{signals_str}\n\n"
        f"Outreach Angle:\n{report.get('recommended_angle', '')}\n\n"
        f"Report: {results[0].text}"
    )

    return [
        TextContent(type="text", text=summary),
        TextContent(type="text", text=results[1].text),
    ]


async def main():
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            mcp.server.stdio.ServerParams(
                name="github-lead-intelligence",
                version="0.1.0",
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
