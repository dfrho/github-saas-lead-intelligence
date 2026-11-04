"""
Run the report pipeline for one repo against the real GitHub and Claude APIs,
without the database or the web app. Prints each step so a failure shows where.

Usage (from the repo root, with GITHUB_TOKEN and ANTHROPIC_API_KEY in .env):
    python scripts/smoke_report.py stripe stripe-python
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Same import roots as the API: services/ and src.services both resolve
_ROOT = Path(__file__).parent.parent
sys.path[:0] = [str(_ROOT / "src"), str(_ROOT)]
load_dotenv()

from services import claude_api, github_api  # noqa: E402
from services.dependency_analyzer import analyze_dependencies  # noqa: E402
from services.vendor_map import get_vendors_for_domains  # noqa: E402


def step(name):
    print(f"\n── {name}", flush=True)


def main(owner: str, repo: str) -> None:
    step("Checking the repo is public")
    github_api.ensure_public_repo(owner, repo)

    step("Fetching activity from GitHub")
    activity = github_api.fetch_repo_activity(owner, repo)
    print(f"{len(activity.commits)} commits, {len(activity.pull_requests)} PRs, {len(activity.issues)} issues")
    activity_data = {
        "owner": owner,
        "repo": repo,
        "commits": [{"message": c.message} for c in activity.commits],
        "pull_requests": [{"title": pr.title} for pr in activity.pull_requests],
        "issues": [{"title": i.title, "state": i.state, "labels": i.labels} for i in activity.issues],
    }

    step("Claude: summarize activity")
    synopsis = claude_api.summarize_activity(activity_data)
    print(synopsis)

    step("Claude: classify signals")
    signals = claude_api.classify_signal(synopsis)
    for s in signals:
        print(f"- {s}")

    step("Claude: company news (web search + rerank)")
    news = claude_api.fetch_company_news(owner)
    print(f"{len(news)} news items")

    step("Claude: company's own domains")
    own_domains = claude_api.detect_company_own_domains(owner)
    print(own_domains)

    step("Dependencies and vendors")
    deps = analyze_dependencies(github_api.fetch_dependency_files(owner, repo))
    vendors = get_vendors_for_domains(signals, owner, list(set(own_domains)))
    print(f"dependency score {deps.score}, {len(vendors)} vendor groups")

    step("Claude: outreach angle")
    print(claude_api.recommend_outreach_angle(synopsis, signals, news))

    print("\n✓ Every step completed")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
