# GitHub Lead Intelligence

Monitors GitHub repositories for engineering activity and converts code changes into structured sales leads. The core insight: when an engineering team heavily commits to a new infrastructure domain (messaging, auth, observability, etc.), that company will be in-market for SaaS vendors in that space within 60–120 days.

## Structure

```
├── CLAUDE.md                  ← Claude Code project brief
├── IMPLEMENTATION.md          ← Python architecture & design
├── code_instructions/
│   ├── mcp_tool_schema.md     ← MCP tool signatures
│   ├── report_format.md       ← Report template (JSON + Markdown)
│   └── enrichment_ideas.md    ← Phase 2+ signal ideas
├── src/
│   ├── main.py                ← MCP server entry point
│   ├── cli.py                 ← CLI for managing registry
│   └── services/
│       ├── registry.py        ← Registry persistence (data/registry.json)
│       └── github_api.py      ← GitHub API wrapper (PyGithub)
├── data/
│   └── registry.json          ← Watched repos (auto-managed, .gitignored)
├── reports/                   ← Generated lead reports (Phase 3+)
└── pyproject.toml             ← Dependencies & configuration
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

### 6. Manual Testing (Optional)

To test the server manually without Claude Code:

```bash
source venv/bin/activate
python src/main.py
```

The server listens on stdin/stdout for MCP protocol messages.

## MCP Tools (Phase 1)

### `watch_repo(owner, repo, label?)`
Add a GitHub repository to the watched registry.
```python
# Watch a repo
watch_repo("facebook", "react", "React.js")

# Returns: "Watching facebook/react (label: "React.js"). Added at 2026-04-18T10:00:00Z"
```

### `list_watched_repos()`
List all repositories in the registry with last-checked status.
```python
# Returns: All entries with timestamps, labels, and last activity hash
```

### `fetch_repo_activity(owner, repo, since?, force?)`
Fetch commits, pull requests, and issues since a date. Smart deduplication via `last_activity_hash` prevents redundant fetches.
```python
fetch_repo_activity("facebook", "react", since="2026-04-01T00:00:00Z")

# Returns: {
#   "commits": [...],
#   "pull_requests": [...],
#   "issues": [...],
#   "latest_commit_sha": "abc123...",
#   "fetched_at": "2026-04-18T10:05:00Z"
# }
```

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

## Environment Variables

- **`GITHUB_TOKEN`** (required) — GitHub personal access token with `repo` scope
- **`ANTHROPIC_API_KEY`** (optional, Phase 2+) — For summarization and classification

## Implementation Details

See **[IMPLEMENTATION.md](IMPLEMENTATION.md)** for:
- Architecture overview
- Python module structure
- How registry persistence works
- GitHub API integration (PyGithub + ThreadPoolExecutor)
- MCP server tool registration
- Data model definitions

## Next Phases

- **Phase 2** — Enrichment (fetch_contributor_profiles, fetch_company_news, classify_signal)
- **Phase 3** — Report assembly (recommend_saas_vendors, generate_lead_report)
- **Phase 4** — Testing and polish

See [CLAUDE.md](CLAUDE.md) for the full phased build plan.

