import json
from mcp.server import Server
from mcp.types import TextContent, Tool
import mcp.server.stdio
from dotenv import load_dotenv

load_dotenv()

from services import registry, github_api


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
