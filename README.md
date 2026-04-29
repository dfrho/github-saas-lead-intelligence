# GitHub SaaS Lead Intelligence

Monitors GitHub repositories for engineering activity and converts code changes into structured sales leads. The core insight: when an engineering team heavily commits to a new infrastructure domain (messaging, auth, observability, etc.), that company will be in-market for SaaS vendors in that space within 60–120 days.

## Clone the Repo

```bash
git clone https://github.com/dfrho/github-saas-lead-intelligence.git
cd github-saas-lead-intelligence
```

## Project Structure

![System architecture](architecture.svg)

### run_full_analysis Call Chain

```text
run_full_analysis(owner, repo)
│
├── registry.get_repo()                    ← check if repo is watched
│
├── github_api.fetch_repo_activity()       ← commits, PRs, issues delta
│
├── claude_api.summarize_activity()        ← what are they building? (Anthropic API)
│
├── claude_api.classify_signal()           ← maps synopsis → 20 domain categories (Anthropic API)
│
├── claude_api.fetch_company_news()        ← web search via Anthropic API
│
├── github_api.fetch_contributor_profiles()   ← GitHub user/org lookups
├── dep_analyzer.analyze_dependencies()       ← fetches manifests from GitHub, scores gaps
└── vendor_map.recommend_saas_vendors()       ← static domain → vendor lookup (free)
│
├── claude_api.recommend_outreach_angle()  ← writes outreach paragraph using news, signals,
│                                            and dependency findings (Anthropic API)
│
├── scoring()                              ← deterministic: activity 25%, pain points 25%,
│                                            dependencies 20%, team size 15%, growth 15%
│
├── registry.save_report()                 ← writes to Supabase Postgres
│
└── returns report_id
```

## Quick Start

### 1. Get a GitHub Token

Generate a personal access token at https://github.com/settings/tokens:
- Click "Generate new token (classic)"
- Select scope: **`repo`** (read access to repositories)
- Copy the token (you won't see it again)

### 2. Set Up Python Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .
```

### 3. Configure Environment

```bash
# Copy the template
cp .env.example .env

# Edit and add your token
nano .env
# GITHUB_TOKEN=ghp_your_token_here
# ANTHROPIC_API_KEY=sk-ant-your_key_here (for Phase 2+)
```

### 4. Register with Claude Code

To use this MCP server with Claude Code (Anthropic's CLI tool), register it in your Claude Code configuration:

**Edit your Claude Code config file** at `~/.claude/claude_config.json`:
```json
{
  "mcpServers": {
    "github-lead-intelligence": {
      "command": "python",
      "args": ["/full/path/to/project/src/main.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

Or **use environment variables** (cleaner — Claude Code will read from your `.env` file):
```json
{
  "mcpServers": {
    "github-lead-intelligence": {
      "command": "python",
      "args": ["/full/path/to/project/src/main.py"]
    }
  }
}
```
(Ensure `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` are in your project's `.env` file)

After registration:
- **Restart Claude Code:**
  - If using CLI: Stop the process (`Ctrl+C`) and run `claude` to start Claude Code again
  - If using IDE: Open the command palette (`Cmd+Shift+P`) and run `Developer: Reload Window`
  - Claude Code will automatically launch the MCP server on startup
- **Claude Code can now call the tools:**
  - `watch_repo("facebook", "react", "React")`
  - `list_watched_repos()`
  - `fetch_repo_activity("facebook", "react")`
  - `summarize_activity("facebook", "react")`
  - `classify_signal("They are migrating to Kafka and adding Prometheus metrics.")`
  - `fetch_contributor_profiles("facebook", "react")`
  - `fetch_company_news("facebook", org_domain="meta.com")`

### 5. Add Repositories to Watch

Use the CLI to add repositories without manually editing JSON:

```bash
# Activate venv first
source venv/bin/activate

# Add a repository with auto-generated timestamp
python src/cli.py add facebook react "React.js"

# Add with default label (owner/repo)
python src/cli.py add kubernetes kubernetes

# List all watched repositories
python src/cli.py list

# Remove a repository
python src/cli.py remove facebook react
```

**What happens:**
- `added_at` is auto-generated with current timestamp (no human error)
- Repos are stored in `data/registry.json`
- Registry persists across CLI calls

### 6. Test Each Phase

Once the MCP server is registered and Claude Code is reloaded, open a Claude Code chat and run these commands in order.

#### Test Phase 1 — Activity Collection

```python
watch_repo("facebook", "react", "React.js")
list_watched_repos()
fetch_repo_activity("facebook", "react")
```

Expected: repo appears in registry, activity returns commits/PRs/issues JSON, a second call with no new commits returns "No new activity."

#### Test Phase 2 — Enrichment

```python
analyze_repo("facebook", "react")
fetch_contributor_profiles("facebook", "react", max_contributors=5)
fetch_company_news("facebook", org_domain="meta.com")
```

Expected: `analyze_repo` returns a 2–3 sentence synopsis plus ranked domain signals; `fetch_contributor_profiles` returns names, companies, and orgs; `fetch_company_news` returns funding/launch/hiring items.

#### Test Phase 3 — Full Report

```python
run_full_analysis("facebook", "react")
```

Expected: scores the lead, writes `reports/facebook__react__YYYY-MM-DD.md`, and returns a console summary with lead score, top signals, and outreach angle. Check the file was written:

```bash
ls reports/
```

#### Test Phase 4A — Dependency Signals

Test the dependency fetcher standalone (returns raw file contents):

```python
fetch_dependency_files("facebook", "react")
```

Expected: a dict of `{filename: content}` for whichever manifest files exist in the repo (`package.json`, `requirements.txt`, `pyproject.toml`, etc.). Returns `{}` if none are found.

To see dependency scoring in action, run the full report on a repo with a known dependency file:

```python
run_full_analysis("openai", "openai-python")
```

Expected: the report's "Dependency Signals" section lists any detected flags (missing observability, version lag on security packages, competitor presence). The `score_breakdown.dependencies` field in the JSON will now be non-zero if signals were detected. Check the written report:

```bash
cat reports/openai__openai-python__YYYY-MM-DD.md
```

To test all three flag types explicitly, ask Claude to call `analyze_repo` on repos you know have specific characteristics:

- **Missing observability:** a young repo with no APM library — look for `[HIGH] No observability/APM library detected`
- **Version lag:** a repo pinning old versions of `requests`, `express`, or `django`
- **Competitor presence:** a repo that already uses `dd-trace` or `newrelic` — signals they are evaluating that space

### 7. Manual Server Test (Optional)

To verify the server starts without errors before registering it:

```bash
source venv/bin/activate
python src/main.py
```

The server listens on stdin/stdout for MCP protocol messages. `Ctrl+C` to stop.

## MCP Tools

### Phase 1 — Activity Collection

#### `watch_repo(owner, repo, label?)`

Add a GitHub repository to the watched registry.

```python
watch_repo("facebook", "react", "React.js")
# Returns: "Watching facebook/react (label: "React.js"). Added at 2026-04-18T10:00:00Z"
```

#### `list_watched_repos()`

List all repositories in the registry with last-checked status.

```python
list_watched_repos()
# Returns: All entries with timestamps, labels, and last activity hash
```

#### `fetch_repo_activity(owner, repo, since?, force?)`

Fetch commits, pull requests, and issues since a date. Smart deduplication via `last_activity_hash` skips repos with no new commits.

```python
fetch_repo_activity("facebook", "react", since="2026-04-01T00:00:00Z")
# Returns: { "commits": [...], "pull_requests": [...], "issues": [...], "latest_commit_sha": "abc123..." }
```

Parameters:

- `since` — ISO 8601 date string; defaults to 30 days ago
- `force` — set `true` to re-fetch even if head commit hasn't changed

---

### Phase 2 — Enrichment

#### `analyze_repo(owner, repo, since?)`

Shorthand that chains `summarize_activity` → `classify_signal` in a single call. Returns both the synopsis and the ranked domain list.

```python
analyze_repo("facebook", "react")
# Returns:
# Analysis for facebook/react
#
# Synopsis:
# The team is migrating the React Native renderer...
#
# Signals (3 domains matched):
#   [HIGH] messaging_event_streaming — Kafka integration in renderer pipeline.
#   [MEDIUM] observability_monitoring — New tracing hooks added.
#   [LOW] cicd_devops — Minor CI config changes.
```

Parameters:

- `since` — ISO 8601 date string; defaults to 30 days ago

---

#### `summarize_activity(owner, repo, since?, force?)`

Fetch recent GitHub activity and use Claude to produce a 2–3 sentence technical synopsis of what the team is actively building. Useful as input to `classify_signal`.

```python
summarize_activity("stripe", "stripe-python")
# Returns: "The team is actively refactoring their HTTP client layer and adding
#  structured logging throughout the SDK. Recent PRs suggest preparation for
#  async support and a new retry-with-backoff strategy."
```

#### `classify_signal(summary)`

Map a synopsis to SaaS domain categories with confidence levels (`high`, `medium`, `low`) and a one-sentence rationale for each. Pass the output of `summarize_activity` directly.

```python
classify_signal("The team is adding Prometheus metrics and OpenTelemetry tracing.")
# Returns: [
#   { "domain": "observability_monitoring", "confidence": "high", "reasoning": "..." },
#   { "domain": "infrastructure_iac",       "confidence": "low",  "reasoning": "..." }
# ]
```

Recognized domains: `observability_monitoring`, `auth_identity_sso`, `messaging_event_streaming`, `data_pipeline_etl`, `cicd_devops`, `database_data_storage`, `security_compliance`, `search`, `feature_flags`, `api_gateway_service_mesh`, `testing_qa`, `infrastructure_iac`, `cdn_edge_networking`, `payments_billing`, `notifications_comms`, `ml_ai_platform`, `analytics_bi`, `support_ticketing`, `ecommerce`, `marketing_communications`

#### `fetch_contributor_profiles(owner, repo, max_contributors?)`

Fetch GitHub profile data for the top contributors: name, company, location, bio, follower count, and public org memberships. Useful for identifying decision-makers and their prior employers.

```python
fetch_contributor_profiles("vercel", "next.js", max_contributors=5)
# Returns: [
#   { "login": "...", "name": "...", "company": "Vercel",
#     "orgs": ["vercel", "nextjs"], "contributions": 4821, ... },
#   ...
# ]
```

Parameters:

- `max_contributors` — number of top contributors to fetch; defaults to 10

#### `fetch_company_news(owner, org_domain?)`

Search for recent news about the company behind a GitHub org using Claude's web search: funding rounds, product launches, technical blog posts, hiring surges, and partnerships.

```python
fetch_company_news("stripe", org_domain="stripe.com")
# Returns: [
#   { "title": "Stripe raises $694M Series I", "type": "funding",
#     "date": "2023-03-15", "url": "...", "snippet": "..." },
#   ...
# ]
```

Parameters:

- `org_domain` — explicit company domain (e.g. `"stripe.com"`) for more targeted search; defaults to searching by org name

---

### Phase 3 — Report Assembly

#### `recommend_saas_vendors(domains)`

Map classified domain signals to curated SaaS vendor recommendations. Only returns vendors for `high` and `medium` confidence signals. Pass the `signals` list from `classify_signal` or `analyze_repo` directly.

```python
recommend_saas_vendors([
  {"domain": "observability_monitoring", "confidence": "high", "reasoning": "Prometheus added."},
  {"domain": "messaging_event_streaming", "confidence": "medium", "reasoning": "Kafka work."}
])
# Returns: [
#   { "domain": "observability_monitoring", "confidence": "high",
#     "vendors": [{"name": "Datadog", "url": "...", "pitch": "..."}, ...] },
#   ...
# ]
```

#### `generate_lead_report(owner, repo, since?, org_domain?)`

Full orchestration: fetches activity, summarizes, classifies, fetches contributor profiles and company news in parallel, recommends vendors and outreach angle, scores the lead, and writes a report to `reports/`.

```python
generate_lead_report("stripe", "stripe-python", org_domain="stripe.com")
# Writes: reports/stripe__stripe-python__YYYY-MM-DD.md
# Returns: full report JSON including lead score, signals, vendors, and outreach angle
```

#### `run_full_analysis(owner, repo, since?, org_domain?)`

Single top-level call that runs `generate_lead_report` and returns a console-friendly summary. The recommended starting point for evaluating any repo.

```python
run_full_analysis("vercel", "next.js", org_domain="vercel.com")
# Returns:
# Analysis complete for vercel/next.js
#
# Lead Score:  74/100 — Warm lead
# Top Signals:
#   [HIGH] cicd_devops
#   [HIGH] infrastructure_iac
#   [MEDIUM] observability_monitoring
#
# Outreach Angle:
# Vercel's Next.js team has been...
#
# Report: reports/vercel__next.js__YYYY-MM-DD.md
```

Parameters:

- `since` — ISO 8601 date string; defaults to 30 days ago
- `org_domain` — company domain for more targeted news search (e.g. `"vercel.com"`)

---

## Phase 5 — Web API (5a + 5b)

### Database Setup (5a)

Phase 5 adds a Postgres backend (Supabase) alongside the existing JSON registry. When `USE_DB=true` is set, all registry reads/writes go to Postgres instead of `data/registry.json`. The MCP server continues to work unchanged when `USE_DB` is not set.

**New environment variables** (add to `.env`):

```text
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
SUPABASE_URL=https://[ref].supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
USE_DB=true
FRONTEND_ORIGIN=http://localhost:3000   # or your deployed frontend URL
```

**Create the three tables** in the Supabase SQL Editor:

```sql
CREATE TABLE watched_repos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    label TEXT,
    added_at TIMESTAMPTZ DEFAULT now(),
    last_checked TIMESTAMPTZ,
    last_activity_hash TEXT,
    UNIQUE (user_id, owner, repo)
);

CREATE TABLE reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    run_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'pending',
    score_composite INTEGER,
    score_activity INTEGER,
    score_pain_points INTEGER,
    score_dependencies INTEGER,
    score_team_size INTEGER,
    score_growth INTEGER,
    confidence_label TEXT,
    markdown_body TEXT,
    json_body JSONB
);

CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    company_name TEXT,
    work_domain TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

Run with **"Run and enable RLS"** to enforce row-level security, then add the access policies:

```sql
CREATE POLICY "Users can view own watched repos" ON watched_repos FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own watched repos" ON watched_repos FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete own watched repos" ON watched_repos FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "Users can view own reports" ON reports FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own reports" ON reports FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own reports" ON reports FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can view own profile" ON user_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can insert own profile" ON user_profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON user_profiles FOR UPDATE USING (auth.uid() = id);
```

**Migrate existing `data/registry.json` entries** to Postgres (one-time):

```bash
export $(grep -v '^#' .env | xargs)
python scripts/migrate_registry_to_db.py

# Optionally assign all repos to a specific user:
python scripts/migrate_registry_to_db.py --user-id YOUR_SUPABASE_USER_UUID
```

### FastAPI Backend (5b)

A REST API layer built on top of the same `src/services/` functions used by the MCP server.

**Install new dependencies:**

```bash
pip install -e .
```

**Run the API server locally:**

```bash
uvicorn src.api.main:app --reload --port 8000
```

Interactive docs available at `http://localhost:8000/docs`.

#### Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Health check |
| `POST` | `/repos` | Required | Watch a repository |
| `GET` | `/repos` | Required | List watched repos |
| `DELETE` | `/repos/{owner}/{repo}` | Required | Remove a repo |
| `POST` | `/reports/run` | Optional | Trigger a report (pre-auth allowed) |
| `GET` | `/reports/status/{id}` | None | Poll report progress |
| `GET` | `/reports` | Required | List completed reports |
| `GET` | `/reports/{id}` | Required | Fetch full report with score breakdown |
| `GET` | `/reports/{id}/export?format=csv` | Required | Download as CSV |
| `GET` | `/reports/{id}/export?format=txt` | Required | Download as plain text |
| `GET` | `/users/me` | Required | Get user profile |
| `POST` | `/users/me` | Required | Create or update user profile |

**Auth:** All protected endpoints expect a Supabase JWT as `Authorization: Bearer <token>`. `POST /reports/run` also works without a token — the report is generated and held server-side; the auth gate fires when the user tries to view it.

**Report progress:** After triggering a report, poll `GET /reports/status/{id}` every 3 seconds. The `status` field cycles through:

```text
Fetching repository activity...
Analyzing commits...
Classifying signals...
Researching company news...
Profiling contributors...
Scoring the lead...
Almost done...
complete
```

**Report scores:** `GET /reports/{id}` returns all five individual factor scores alongside the composite:

```json
{
  "score_composite": 74,
  "score_activity": 82,
  "score_pain_points": 71,
  "score_dependencies": 55,
  "score_team_size": 90,
  "score_growth": 60,
  "confidence_label": "Warm lead"
}
```

### Weekly Scheduler (5c)

Reports run automatically every Sunday at 02:00 UTC for every watched repository. The scheduler is embedded in the FastAPI process — no separate worker needed.

**How it works:**

- APScheduler (`BackgroundScheduler`) starts on app startup and stops on shutdown
- Each Sunday it iterates all `watched_repos` rows and calls `run_full_analysis` for each
- Repos with an unchanged `last_activity_hash` are skipped (no new commits = no new report)
- On failure, the job retries once after 30 minutes; errors are logged to stderr — no silent failures
- The schedule is configurable via env var (default: weekly):

```text
REPORT_CRON=0 2 * * 0    # Sunday 02:00 UTC (default)
REPORT_CRON=0 2 * * *    # Daily 02:00 UTC
```

### Next.js Frontend (5d)

A React frontend deployed to Vercel. All data fetching goes through the FastAPI backend — the frontend holds no business logic.

**Pre-auth flow:**

1. Visitor enters `owner/repo` on the landing page and clicks **Analyze Repository**
2. `POST /reports/run` fires without a token — the report generates in the background
3. A rotating progress indicator polls `GET /reports/status/{id}` every 3 seconds, showing live status messages ("Fetching repository activity...", "Analyzing commits...", etc.)
4. When complete, the app checks for an active session:
   - **Already signed in** → redirected directly to `/reports/{id}`
   - **Not signed in** → redirected to `/login?next=/reports/{id}`
5. After sign-in, the report is claimed by the authenticated user and displayed immediately

**Authentication:**

- Google OAuth via Supabase Auth
- Registration collects work email (or Gmail), work web domain, and company name
- Session tokens are stored in `localStorage` by the Supabase client and passed as `Authorization: Bearer` on all API calls
- JWT validation on the backend supports both HS256 (legacy) and ES256 (Supabase default) tokens via the JWKS endpoint

**Report viewer (`/reports/[id]`):**

The viewer leads with a structured summary card, then renders the full Markdown report below the fold:

- **Composite score + confidence label** at the top (e.g. "74/100 — Warm lead")
- **Five factor score bars** with weights: Activity 25%, Pain Points 25%, Dependencies 20%, Team Size 15%, Growth Signals 15%
- **Outreach Angle** paragraph with a one-click copy button (shows "Outreach copied" confirmation for 5 seconds)
- **Top 3 contributors** with LinkedIn search links (GitHub `@org` prefix stripped automatically)
- **Vendor recommendations** as badge chips
- **Export buttons** — CSV (one row per contributor + signal summary) or TXT (plain Markdown)
- Full Markdown report rendered below via `react-markdown` + `remark-gfm` + `rehype-highlight`

**Frontend environment variables** (Vercel):

```text
NEXT_PUBLIC_SUPABASE_URL=https://[ref].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

### Deployment (5e)

| Component | Host | Notes |
| --- | --- | --- |
| Frontend (Next.js) | Vercel | Zero-config, auto-deploys from `main` |
| Backend (FastAPI + APScheduler) | Railway | Single Dockerfile, `$PORT` injected automatically |
| Database + Auth | Supabase | Managed Postgres + Google OAuth |

**Railway setup:**

1. Connect GitHub repo → Railway detects the `Dockerfile` automatically
2. Set environment variables in Railway dashboard (all vars from 5a, plus `PORT=8000`)
3. Use the Supabase **Transaction Pooler** connection URL (port `6543`, not `5432`) — Railway uses IPv4, the direct connection is IPv6-only
4. Set `SUPABASE_SERVICE_KEY` to the **Legacy JWT Secret** from Supabase → Authentication → JWT Settings (not the `service_role` API key)
5. Add a healthcheck: path `/health`, timeout 30s

**Vercel setup:**

1. Import the repo and set **Root Directory** to `web/`
2. Add the three `NEXT_PUBLIC_` environment variables
3. Add your Railway backend URL to Supabase → Authentication → URL Configuration → Redirect URLs

**All backend environment variables:**

```text
GITHUB_TOKEN=              # GitHub PAT with repo read scope
ANTHROPIC_API_KEY=         # For summarize, classify, news, outreach
DATABASE_URL=              # Supabase Transaction Pooler URL (port 6543)
SUPABASE_URL=              # https://[ref].supabase.co
SUPABASE_ANON_KEY=         # Public key (used by frontend Supabase client)
SUPABASE_SERVICE_KEY=      # Legacy JWT Secret (for HS256/ES256 token validation)
FRONTEND_ORIGIN=           # Your Vercel URL (for CORS)
USE_DB=true
PORT=8000
REPORT_CRON=               # Optional, default: 0 2 * * 0
```

---

## Registry Schema

Each watched repo is stored in `data/registry.json` (auto-managed via CLI or MCP tools).

**Fields:**
- **`owner`** (string) — GitHub organization or user name
- **`repo`** (string) — Repository name
- **`label`** (string) — Human-readable label (e.g., "React.js", "Linux Kernel")
- **`added_at`** (ISO 8601) — Auto-generated when added
- **`last_checked`** (ISO 8601 or null) — Auto-updated when activity is fetched
- **`last_activity_hash`** (string or null) — Auto-updated with latest commit SHA (prevents redundant fetches)

**Don't edit manually** — use `python src/cli.py add` or `watch_repo()` tool instead.

## Hallucination Controls

Claude-generated content is validated and filtered at multiple points in the pipeline:

**News date validation** — Items from `fetch_company_news` are dropped if their date is more than 18 months in the past or more than 30 days in the future. This prevents stale or speculative items from influencing the outreach angle or growth score.

**News deduplication** — Items that share 3+ significant title keywords and dates within 30 days of each other are collapsed into a single entry, keeping the one from the more trusted source. This prevents the same funding round or launch from appearing twice under slightly different headlines.

**Source ranking** — News items from reputable outlets (TechCrunch, Bloomberg, Reuters, Forbes, VentureBeat, PR Newswire, etc.) are sorted above unverified sources. Claude is also instructed in the prompt to prefer these sources and exclude unverified items.

**Domain classification constraints** — `classify_signal` is given a fixed list of 20 domain keys and instructed to return only those keys. Claude cannot invent new categories.

**Confidence threshold warning** — If fewer than 2 high-confidence domain signals are returned by `classify_signal`, a `low_signal_warning` field is added to the report JSON flagging that the lead score may be unreliable.

**Dependency scoring is fully deterministic** — All package detection, version lag, and competitor presence checks use static lookup tables with no Claude involvement, eliminating hallucination risk in that component entirely.

## Environment Variables

- **`GITHUB_TOKEN`** (required) — GitHub personal access token with `repo` scope
- **`ANTHROPIC_API_KEY`** (required for Phase 2+) — For summarization, classification, news search, and outreach angle

## Implementation Details

See **[IMPLEMENTATION.md](IMPLEMENTATION.md)** for:
- Architecture overview
- Python module structure
- How registry persistence works
- GitHub API integration (PyGithub + ThreadPoolExecutor)
- MCP server tool registration
- Data model definitions

## Next Phase

**Phase 6** introduces monetization and team workspaces:

- **6a** — Pricing tiers ($0 / $49 / $199 / $499/mo) with usage limits enforced server-side; Stripe integration
- **6b** — Content distribution: YouTube demo, HackerNews launch post, README SEO pass, `llms.txt`
- **6c** — Team workspaces: shared repo lists, role management, workspace-scoped billing
- **6d** — Org-level aggregation: `watch_org()` enrolls all public repos in a GitHub org and produces a rollup report

See [CLAUDE.md](CLAUDE.md) for the full phased build plan.

