import json
from mcp.server import Server
from mcp.types import TextContent, Tool
import mcp.server.stdio
from dotenv import load_dotenv

load_dotenv()

from services import registry, github_api, claude_api


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
    import asyncio

    asyncio.run(main())
