# GitHub Lead Intelligence — Claude Code Project Brief

## What This Is
An MCP server that monitors GitHub repositories for engineering activity and converts code changes into structured sales leads. The core insight: when an engineering team starts heavily committing to a new infrastructure domain (messaging, auth, observability, etc.), that company will be in-market for SaaS vendors in that space within 60–120 days. Code changes precede the RFP.

## Tech Stack
- **Runtime:** Python 3.11+ (interpreted, no build step)
- **MCP SDK:** `mcp` (Anthropic's Python SDK)
- **GitHub API:** PyGithub (with ThreadPoolExecutor for parallel requests)
- **Type validation:** Pydantic (data models)
- **Web search/news:** Anthropic API with `web_search_20250305` tool (Phase 2+)
- **Storage:** Local JSON file (`data/registry.json`) for the watched repo registry
- **Output:** Markdown report files written to `reports/` (Phase 3+)

## Architecture Overview

```
Watched Repo Registry (data/registry.json)
        ↓
fetch_repo_activity()       ← GitHub API: commits, PRs, issues delta
        ↓
summarize_activity()        ← Claude: what are they building?
        ↓
classify_signal()           ← Claude: maps synopsis to SaaS domain category
        ↓
fetch_contributor_profiles() ← GitHub API: handles, orgs, prior employers
        ↓
fetch_company_news()        ← Web search: blog posts, press releases from repo org domain
        ↓
recommend_saas_vendors()    ← Claude: which SaaS cos want this lead?
        ↓
generate_lead_report()      ← Assembles full Markdown report to reports/
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

### Phase 2 — Enrichment Tools (Next)
- Implement `fetch_contributor_profiles` via PyGithub (user/org lookups, prior employment)
- Implement `fetch_company_news` using Anthropic API with web_search tool
- Implement `classify_signal` using Claude API (maps activity to SaaS domain categories)
- Implement `summarize_activity` using Claude API (what are they building?)

### Phase 3 — Report Assembly
- Implement `recommend_saas_vendors` with curated domain → vendor mapping
- Implement `generate_lead_report` to assemble full Markdown artifact
- Wire all tools into a single `run_full_analysis(owner, repo)` orchestration call

### Phase 4 — Polish + Test
- Test on 3–5 real repos representing different signal types
- Refine `classify_signal` categories and vendor recommendations
- Push to GitHub, update README with example report output

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
