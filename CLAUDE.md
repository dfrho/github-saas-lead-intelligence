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

```text
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

### Phase 5 — Web UI + Scheduled Reports

Build a multi-user web application that wraps the existing `src/services/` layer in a REST API, adds a React frontend, and runs weekly reports automatically. The MCP server continues to exist unchanged — the web backend calls the same service functions directly (Option A: no MCP protocol indirection).

**Phase 5 is a free feedback phase.** All registered users have full access with no usage caps. The goal is to collect real-world feedback on report quality, UI flow, and signal accuracy before introducing pricing. Paywalls, usage limits, tier enforcement, and team workspaces are all deferred to Phase 6. Each account is a personal silo in Phase 5 — shared workspace access ships in Phase 6c.

#### New Directory Structure

```text
src/
  api/                        ← NEW: FastAPI application
    main.py                   ← App factory, CORS, router registration
    routers/
      repos.py                ← /repos endpoints (watch, list, remove)
      reports.py              ← /reports endpoints (trigger, list, fetch)
      users.py                ← /users endpoints (profile, preferences)
    deps.py                   ← FastAPI dependency injection (DB session, auth)
    auth.py                   ← JWT validation middleware (Supabase Auth tokens)
  services/                   ← UNCHANGED — shared by MCP + API
  scheduler/                  ← NEW: weekly report runner
    worker.py                 ← APScheduler setup, job definitions
    jobs.py                   ← run_full_analysis() wrapper with DB persistence

web/                          ← NEW: React + Next.js frontend
  app/
    page.tsx                  ← Dashboard: list of watched repos + latest scores
    repos/
      page.tsx                ← Add/remove repos, view registry
    reports/
      [id]/page.tsx           ← Full report viewer (renders Markdown)
  components/
    RepoCard.tsx              ← Score badge, signal chips, last-run timestamp
    ReportViewer.tsx          ← react-markdown with syntax highlighting
    AddRepoForm.tsx           ← owner/repo input → POST /repos
  lib/
    api.ts                    ← Typed fetch wrappers for all backend endpoints
    auth.ts                   ← Supabase Auth client setup

data/
  registry.json               ← REPLACED by Postgres (migration in Phase 5a)
reports/                      ← SUPPLEMENTED — also stored in DB reports table
```

#### 5a — Database Migration (prerequisite)

- Provision Postgres (Supabase recommended — gives auth + DB in one service)
- Create tables:
  - `watched_repos`: mirrors current `registry.json` schema + `user_id` FK
  - `reports`: `id`, `owner`, `repo`, `user_id`, `run_at`, `score_composite`, `score_activity`, `score_pain_points`, `score_dependencies`, `score_team_size`, `score_growth`, `confidence_label`, `markdown_body`, `json_body`
  - `users`: managed by Supabase Auth (no manual schema needed)
- Rewrite `src/services/registry.py` to read/write Postgres via `asyncpg` or `psycopg3`
- Keep `data/registry.json` as a fallback for local MCP-only usage (env flag: `USE_DB=true`)
- Write a one-time migration script: `scripts/migrate_registry_to_db.py`

#### 5b — FastAPI Backend

- App entry point: `src/api/main.py` — mounts routers, sets CORS for web origin
- Auth middleware: validate Supabase JWT on every request; inject `user_id` into route handlers
- Repo endpoints:
  - `POST /repos` → calls `watch_repo(owner, repo, label)`, scoped to `user_id`
  - `GET /repos` → calls `list_watched_repos()`, filtered to `user_id`
  - `DELETE /repos/{owner}/{repo}` → removes from registry for this user
- Report endpoints:
  - `POST /reports/run` → triggers `run_full_analysis(owner, repo)` as a background task; returns `report_id`
  - `GET /reports` → list all reports for `user_id`, ordered by `run_at` desc
  - `GET /reports/{id}` → fetch single report (markdown + JSON body)
  - `GET /reports/{id}/export?format=csv` → download report as CSV (one row per contributor contact + signal summary)
  - `GET /reports/{id}/export?format=txt` → download report as plain text
- Background task runner: `fastapi.BackgroundTasks` for on-demand runs; scheduler handles weekly runs
- All service calls are the same imports from `src/services/` — zero duplication

#### 5c — Weekly Scheduler

- Use APScheduler (`AsyncIOScheduler`) embedded in the FastAPI process
- Job: every Sunday at 02:00 UTC, for each distinct `(user_id, owner, repo)` in `watched_repos`:
  - Call `run_full_analysis(owner, repo)`
  - Persist result to `reports` table
  - Skip if `last_activity_hash` unchanged (already built into the service)
- Scheduler starts on app startup (`@asynccontextmanager` lifespan in `main.py`)
- Failed jobs log to stderr and are retried once after 30 minutes; no silent failures
- Configurable schedule via env var: `REPORT_CRON=0 2 * * 0` (default: weekly Sunday 02:00 UTC)

#### 5d — Next.js Frontend

- Auth: Google OAuth via Supabase Auth; registration collects work email (or Gmail), work web domain, and company name
- Pre-auth flow: unauthenticated visitors can enter `owner/repo` on the landing page and trigger a report run; they see the rotating progress indicator while it generates
- Auth gate: when the report is ready, viewing it requires registration/login — visitor is shown a sign-up prompt at the moment the report completes; their pending report is held server-side and delivered immediately after auth
- Post-auth: session tokens passed as `Authorization: Bearer` to FastAPI on all subsequent requests
- Dashboard (`/`): grid of `RepoCard` components — one per watched repo, showing score, top signals, last run date
- Repo management (`/repos`): `AddRepoForm` posts to `POST /repos`; table lists watched repos with a remove button
- Report viewer (`/reports/[id]`): leads with a structured summary card — composite score + confidence label at the top, five individual factor scores (activity 25%, pain points 25%, dependencies 20%, team size 15%, growth 15%) displayed as labeled bars or badges, outreach angle paragraph, top 3 contributor contacts, top vendor recommendations — full Markdown report rendered below the fold via `react-markdown` with `remark-gfm` and `rehype-highlight`
- While report is generating, show a rotating text-based progress indicator (e.g. "Fetching activity...", "Analyzing commits...", "Classifying signals...", "Researching news...", "Almost done...") — client polls `GET /reports/{id}` every 3s; status field in DB drives the message shown
- No custom design system — use shadcn/ui components throughout
- Data fetching: SWR for client-side fetching with auto-revalidation on focus

#### 5e — Deployment

- Backend: single Dockerfile running FastAPI + APScheduler worker (no separate worker process needed for this scale)
- Frontend: Vercel (zero-config Next.js deployment)
- Database: Supabase cloud (managed Postgres + auth)
- Recommended host for backend: Railway or Render (both support Dockerfiles, env var injection, persistent processes)
- Required new env vars:

```text
DATABASE_URL=         # Postgres connection string (Supabase)
SUPABASE_URL=         # For auth token validation
SUPABASE_ANON_KEY=    # Public key for frontend Supabase client
SUPABASE_SERVICE_KEY= # Server-side key for JWT verification in FastAPI
REPORT_CRON=          # Optional override, default: 0 2 * * 0
USE_DB=true           # Switches registry from JSON file to Postgres
```

#### Execution Order

1. **5a** — DB migration (blocks everything else)
2. **5b** — FastAPI backend (can be built against local Postgres; MCP still works in parallel)
3. **5c** — Scheduler (add after 5b endpoints are tested)
4. **5d** — Frontend (wire against 5b API; can mock data initially)
5. **5e** — Deploy (after 5d is functional end-to-end locally)

#### What Does NOT Change

- `src/services/` — untouched; shared by MCP server and web API
- `server.py` (MCP entrypoint) — continues to work for Claude Desktop users
- Report Markdown format — same output, now also stored in DB
- Lead scoring logic — unchanged from Phase 3/4

---

### Phase 6 — Monetization + Team Workspaces

Introduce pricing tiers, usage enforcement, and shared team workspaces based on feedback collected during the Phase 5 free period.

#### 6a — Pricing Tiers + Paywall

- Define usage limits per tier and enforce them server-side in FastAPI:

| Tier | Price | Repo limit | Report runs | Scheduling |
| --- | --- | --- | --- | --- |
| Free | $0 | 3 repos | Manual only | None |
| Starter | $49/mo | 25 repos | Manual + weekly auto | Weekly |
| Team | $199/mo | 100 repos | Manual + daily auto | Daily |
| Growth | $499/mo | Unlimited | Manual + daily auto | Daily |

- Add a `plan` field to the `users` table (managed via Supabase or Stripe billing)
- Gate `POST /reports/run` and `POST /repos` against the user's current plan limits
- Show upgrade prompts in the UI when a user hits their limit
- Integrate Stripe for subscription management; webhook updates `plan` field on payment events

#### 6b — Content Distribution

Launch content in parallel with pricing to drive inbound during the monetization window:

- **YouTube demo:** "How I found 50 warm leads using GitHub commits (no cold outreach)" — screen recording of the full flow: landing page → repo input → progress indicator → summary card with score breakdown and outreach angle. Target: r/sales, r/LeadGeneration, cold email Facebook groups
- **HackerNews post:** "Why commit velocity predicts SaaS purchasing intent 60–120 days out" — publish the core thesis as a technical essay. Link to a live demo or a pre-generated example report on a well-known open source org. Target: Show HN for the tool launch
- **README SEO pass:** Optimize for "github commit activity sales intelligence" and "developer activity leads" — these are low-competition, high-intent terms matching the keyword growth data (+1,334%)
- **llms.txt:** Add a `/llms.txt` file to the web root describing the product, its core thesis, and how to use it — the emerging standard (analogous to `robots.txt`) that tells LLMs how to represent your product when users ask about sales intelligence tools. Increases the chance Claude, ChatGPT, and Gemini surface this product in relevant conversations
- Publish all four before or concurrent with the Phase 6a paywall launch to maximize top-of-funnel during the pricing introduction

#### 6c — Team Workspaces

- Add a `workspaces` table: `id`, `name`, `owner_user_id`, `plan`, `created_at`
- Add a `workspace_members` table: `workspace_id`, `user_id`, `role` (owner/member)
- Scope `watched_repos` and `reports` to `workspace_id` instead of `user_id`
- Team members share a watched repo list and can all view and export reports
- Workspace owner manages billing; members inherit the workspace plan limits
- Add workspace management UI: invite by email, role management, member list

#### 6d — Org-Level Aggregation

- Add `watch_org(org_name)` MCP tool and `POST /orgs` API endpoint
- Enumerate all public repos in a GitHub org and call `run_full_analysis` on each
- Produce an org-level rollup report: aggregated domain signals across all repos, account score, named contacts across all repos
- Store org-level reports in a separate `org_reports` table

---

## Environment Variables Required

```text
GITHUB_TOKEN=        # Personal access token with repo read scope
ANTHROPIC_API_KEY=   # For summarize, classify, news, and recommend tools
```

## Key Conventions

- All tools should be idempotent where possible
- Registry entries include: `{ owner, repo, label, added_at, last_checked, last_activity_hash }`
- Reports are written to `reports/{owner}__{repo}__{YYYY-MM-DD}.md`
- Use `last_activity_hash` (SHA of most recent commit) to skip repos with no new activity
