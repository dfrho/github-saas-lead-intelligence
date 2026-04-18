# GitHub Lead Intelligence — Python Implementation Guide

## Architecture Overview

The project is an **MCP (Model Context Protocol) server** written in Python that monitors GitHub repositories for engineering activity and generates sales leads.

```
┌─────────────────────────────────────────────┐
│ MCP Client (Claude Code)                    │
│ Sends: watch_repo, list_watched_repos, etc  │
└────────────┬────────────────────────────────┘
             │ MCP Protocol (stdio)
             ↓
┌─────────────────────────────────────────────┐
│ src/main.py (MCP Server)                    │
│ - Initializes Server from mcp.server        │
│ - Registers 3 tools via @server.call_tool() │
└────────────┬────────────────────────────────┘
             │
      ┌──────┴────────┬─────────────┐
      ↓               ↓             ↓
   registry.py   github_api.py    cli.py
   (persistence) (GitHub API)     (CLI)
      │               │             │
      ↓               ↓             ↓
  registry.json  PyGithub     argparse
```

## File Structure

```
src/
├── main.py              MCP server entry point (async tools)
├── cli.py               CLI for managing registry
└── services/
    ├── registry.py      JSON persistence layer
    └── github_api.py    GitHub API wrapper (PyGithub)
```

## Module Breakdown

### `src/main.py` — MCP Server

**Responsibilities:**
- Initialize MCP `Server` from `mcp.server`
- Register 3 async tools via `@server.call_tool()` decorator
- Handle stdio transport via `mcp.server.stdio.stdio_server()`

**Tools defined:**
1. **`watch_repo(owner, repo, label?)`**
   - Calls `registry.add_watched_repo()`
   - Returns confirmation with timestamp
   - Idempotent: returns existing entry if already watched

2. **`list_watched_repos()`**
   - Calls `registry.list_watched_repos()`
   - Returns formatted list of all watched repos with last-checked status

3. **`fetch_repo_activity(owner, repo, since?, force?)`**
   - Calls `github_api.fetch_repo_activity()`
   - Checks registry for `last_activity_hash` (previous commit SHA)
   - Skips fetch if head commit unchanged (unless `force=True`)
   - Updates `last_checked` and `last_activity_hash` in registry
   - Returns summary + full JSON of commits, PRs, issues

**Design:**
- Async handlers allow concurrent tool calls
- Registry is consulted to skip redundant GitHub API calls
- MCP protocol handles communication with client (Claude Code)

### `src/services/registry.py` — Registry Persistence

**Data Model:**
```python
@dataclass
class RegistryEntry:
    owner: str                      # GitHub org/user
    repo: str                       # Repository name
    label: str                      # Human label (e.g., "React.js")
    added_at: str                   # ISO 8601 timestamp
    last_checked: Optional[str]     # ISO 8601 or None
    last_activity_hash: Optional[str]  # Commit SHA or None
```

**Functions:**

- **`_read_registry()`** → `List[RegistryEntry]`
  - Reads `data/registry.json`
  - Returns empty list if file doesn't exist
  - Deserializes JSON to dataclass instances

- **`_write_registry(entries)`** → `None`
  - Serializes list to JSON (indent=2)
  - Creates parent directory if missing
  - Ensures atomic writes

- **`add_watched_repo(owner, repo, label)`** → `(created: bool, entry: RegistryEntry)`
  - Case-insensitive lookup for duplicates
  - Returns existing entry if already watched (idempotent)
  - Creates new entry with `added_at` timestamp if new
  - Auto-generates ISO timestamp for consistency

- **`list_watched_repos()`** → `List[RegistryEntry]`
  - Wrapper around `_read_registry()`
  - Used by MCP tool and CLI

- **`update_registry_entry(owner, repo, **updates)`** → `None`
  - Finds entry by owner/repo (case-insensitive)
  - Updates specified fields (e.g., `last_checked`, `last_activity_hash`)
  - Persists changes to JSON
  - Silent no-op if repo not found

**Key Design Decisions:**
- **Timestamps:** All use ISO 8601 format with `Z` suffix for UTC
- **Case-insensitive lookup:** GitHub usernames/repos can be referenced inconsistently
- **JSON storage:** Simple, human-readable, easy to inspect
- **No async:** Registry uses sync I/O (fast enough for file operations)

### `src/services/github_api.py` — GitHub API Integration

**Data Models:**
```python
@dataclass
class Commit:
    sha: str
    author: Optional[str]
    date: Optional[str]
    message: str

@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    merged_at: Optional[str]

@dataclass
class Issue:
    number: int
    title: str
    state: str
    labels: List[str]
    created_at: str
    closed_at: Optional[str]
    comments: int

@dataclass
class RepoActivity:
    owner: str
    repo: str
    fetched_at: str
    since: str
    commits: List[Commit]
    pull_requests: List[PullRequest]
    issues: List[Issue]
    latest_commit_sha: Optional[str]
```

**Function:**

- **`fetch_repo_activity(owner, repo, since=None, force=False)`** → `RepoActivity`

  **Process:**
  1. Authenticate with `GITHUB_TOKEN`
  2. Fetch commits, PRs, issues **in parallel** via `ThreadPoolExecutor`
  3. Filter results and map to data classes
  4. Return aggregated `RepoActivity`

**Parallel Requests:**
- Uses `ThreadPoolExecutor` with 3 workers (one per request type)
- Improves total fetch time by ~3x

### `src/cli.py` — Command-Line Interface

**Commands:**
- `python src/cli.py add <owner> <repo> [label]` — Add repo
- `python src/cli.py list` — List all watched repos
- `python src/cli.py remove <owner> <repo>` — Remove repo

**Implementation:**
- Uses `argparse` for CLI parsing
- Delegates to `registry.*` functions
- Provides formatted output with status indicators

## Data Flow Example

### Add a Repository

```
User CLI:  python src/cli.py add facebook react "React.js"
                   ↓
         registry.add_watched_repo("facebook", "react", "React.js")
                   ↓
         Create RegistryEntry with added_at = now
                   ↓
         _write_registry([entry]) → data/registry.json
                   ↓
Output:    ✓ Added facebook/react
           Label: React.js
           Added at: 2026-04-18T10:00:00Z
```

## Configuration & Environment

**Environment Variables:**
- `GITHUB_TOKEN` — GitHub personal access token (required)
- `ANTHROPIC_API_KEY` — Anthropic API key (Phase 2+, optional)

**Registry File:**
- Location: `data/registry.json`
- Format: JSON array of RegistryEntry objects
- Auto-managed by registry module

**Timestamps:**
- All timestamps use ISO 8601 with UTC (Z suffix)
- Example: `2026-04-18T10:00:00Z`

## Design Decisions

1. **ThreadPoolExecutor:** PyGithub is synchronous; parallel requests improve performance
2. **Case-insensitive lookup:** Prevents duplicate entries for same repo
3. **Skip unchanged commits:** Saves GitHub API rate quota
4. **ISO 8601 timestamps:** Sortable, human-readable, standard format
5. **Registry.json:** Simple, human-readable, git-friendly

## Next Phases

**Phase 2 — Enrichment Tools:**
- `fetch_contributor_profiles()` — Get contributor info
- `fetch_company_news()` — Web search via Anthropic API
- `classify_signal()` — Classify activity to SaaS domain
- `summarize_activity()` — Summarize commits/PRs/issues

**Phase 3 — Report Assembly:**
- `recommend_saas_vendors()` — Domain → vendor mapping
- `generate_lead_report()` — Assemble Markdown report

**Phase 4 — Polish & Test:**
- Integration tests
- Performance benchmarks
- Example reports
