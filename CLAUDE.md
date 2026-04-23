# GitHub Lead Intelligence — Claude Code Project Brief

## What This Is
An MCP server that monitors GitHub repositories for engineering activity and converts code changes into structured sales leads. The core insight: when an engineering team starts heavily committing to a new infrastructure domain (messaging, auth, observability, etc.), that company will be in-market for SaaS vendors in that space within 60–120 days. Code changes precede the RFP.

## Tech Stack
- **Runtime:** Python 3.11+ (interpreted, no build step)
- **MCP SDK:** `mcp` (Anthropic's Python SDK)
- **GitHub API:** PyGithub (with ThreadPoolExecutor for parallel requests)
- **Data models:** Python `dataclasses` (DependencyFlag, DependencyAnalysis, RepoActivity, etc.)
- **Web search/news:** Anthropic API with `web_search_20250305` tool (Phase 2+)
- **Storage:** Local JSON file (`data/registry.json`) for the watched repo registry
- **Output:** Markdown report files written to `reports/` (Phase 3+)

## Architecture Overview

```
Watched Repo Registry (data/registry.json)
        ↓
fetch_repo_activity()        ← GitHub API: commits, PRs, issues delta
        ↓
summarize_activity()         ← Claude: what are they building?
        ↓
classify_signal()            ← Claude: maps synopsis to 20 SaaS domain categories
        ↓
analyze_repo()               ← Shorthand: summarize_activity → classify_signal in one call
        ↓
fetch_contributor_profiles() ← GitHub API: handles, orgs, prior employers
        ↓
fetch_company_news()         ← Web search: blog posts, press releases from repo org domain
        ↓
recommend_saas_vendors()     ← Static curated map: domain → real SaaS vendor list
        ↓
generate_lead_report()       ← Assembles full Markdown + JSON report to reports/
        ↓
run_full_analysis()          ← Single top-level orchestration call
```

## MCP Tool List
See `code_instructions/mcp_tool_schema.md` for full signatures and descriptions.

## Report Format
See `code_instructions/report_format.md` for the expected output structure.

## Enrichment Signals
See `code_instructions/enrichment_ideas.md` for advanced signal detection ideas to implement after core tools are working.

## Documentation
- **README.md** — Quick start guide, setup instructions, tool documentation
- **IMPLEMENTATION.md** — Python architecture deep-dive, module breakdown, design decisions, testing guide

## Phased Build Plan

### Phase 1 — MCP Scaffold + Core Activity Tools ✅ **COMPLETE**
- Initialize MCP server with `mcp` (Python SDK)
- Implement `watch_repo`, `list_watched_repos`, `fetch_repo_activity`
- Persist registry to `data/registry.json` with smart deduplication via `last_activity_hash`
- Registry uses Python dataclasses, JSON file storage
- GitHub API calls run in parallel via ThreadPoolExecutor (PyGithub)

### Phase 2 — Enrichment Tools ✅ **COMPLETE**

- Implement `fetch_contributor_profiles` via PyGithub (user/org lookups, prior employment)
- Implement `fetch_company_news` using Anthropic API with web_search tool
- Implement `classify_signal` using Claude API (maps activity to 20 SaaS domain categories)
- Implement `summarize_activity` using Claude API (what are they building?)
- Added `analyze_repo` shorthand: chains `summarize_activity` → `classify_signal` in one call
- SaaS domain taxonomy finalized at 20 categories (added `ecommerce`, `marketing_communications`)
- 44-test suite covering all services and tool chaining behavior

### Phase 3 — Report Assembly (Next)

- Implement `recommend_saas_vendors(domains)` as a **static curated map** in `src/services/vendor_map.py`
  (not a Claude call — deterministic domain → [{name, url, pitch}] lookup)
- Add `recommend_outreach_angle(synopsis, signals, news)` to `claude_api.py` — Claude writes the outreach paragraph
- Implement `generate_lead_report(owner, repo)` — full orchestration with parallel execution:
  - Sequential: `fetch_repo_activity` → `summarize_activity` → `classify_signal` (each depends on prior)
  - Parallel: `fetch_contributor_profiles` + `fetch_company_news` + `recommend_saas_vendors` fire concurrently via `asyncio.gather` once signals are ready
  - Sequential: `recommend_outreach_angle` (depends on news + signals) → score → write report
  - Writes `reports/{owner}__{repo}__{YYYY-MM-DD}.md`
- Implement `run_full_analysis(owner, repo, since?, org_domain?)` — single top-level MCP tool call
- **Lead scoring weights:** activity 25%, pain_points 25%, dependencies 20% (stubbed at 0), team_size 15%, growth 15%
- Dependency score stubbed at 0 pending Phase 4 implementation

### Phase 4 — Dependency Signals + Polish

- Implement dependency scoring (the stubbed 20% weight from Phase 3):
  - Fetch `requirements.txt` / `pyproject.toml` / `package.json` via GitHub API
  - Detect missing SaaS categories (no logging lib, no observability, no auth lib for a >1k star repo)
  - Flag major version lag on security-sensitive packages
  - Detect presence of a direct competitor in deps
- Test on 3–5 real repos representing different signal types:
  - Run `run_full_analysis` end-to-end and review `.md` + `.json` report output for both formats
  - Run `analyze_repo` in isolation to verify synopsis + signal quality without full report overhead
  - Review `recommend_outreach_angle` output for specificity — adjust prompt if results are generic
  - Refine `classify_signal` domain categories and vendor recommendations based on real output
- Update README with a real example report (copy from a `reports/` output)

## Environment Variables Required
```
GITHUB_TOKEN=        # Personal access token with repo read scope
ANTHROPIC_API_KEY=   # For summarize, classify, news, and recommend tools
```

## Key Conventions
- All tools should be idempotent where possible
- Registry entries include: `{ owner, repo, label, added_at, last_checked, last_activity_hash }`
- Reports are written to `reports/{owner}__{repo}__{YYYY-MM-DD}.md`
- Use `last_activity_hash` (SHA of most recent commit) to skip repos with no new activity
