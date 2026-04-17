# MCP Tool Schema

This file documents the MCP tools available to Claude Code during enrichment runs.

## GitHub Tools

### `github_get_repo`
```
Input:  { owner: string, repo: string }
Output: { stars, forks, open_issues, language, topics, license, created_at, pushed_at, description }
```

### `github_get_commits`
```
Input:  { owner: string, repo: string, since?: ISO8601, per_page?: number }
Output: [{ sha, author, date, message }]
```

### `github_get_contributors`
```
Input:  { owner: string, repo: string }
Output: [{ login, contributions, type }]
```

### `github_get_issues`
```
Input:  { owner: string, repo: string, state?: "open"|"closed"|"all", labels?: string[] }
Output: [{ number, title, state, labels, created_at, closed_at, comments }]
```

### `github_get_pull_requests`
```
Input:  { owner: string, repo: string, state?: "open"|"closed"|"merged" }
Output: [{ number, title, state, merged_at, additions, deletions, changed_files }]
```

### `github_get_workflows`
```
Input:  { owner: string, repo: string }
Output: [{ id, name, state, path }]
```

### `github_get_package_json`
```
Input:  { owner: string, repo: string }
Output: { dependencies, devDependencies, scripts, engines }
```

## Registry Tools

### `npm_get_package`
```
Input:  { package_name: string }
Output: { version, weekly_downloads, dependents_count, maintainers, dist_tags }
```

### `pypi_get_package`
```
Input:  { package_name: string }
Output: { version, monthly_downloads, requires_python, classifiers }
```

## Web Tools

### `web_search`
```
Input:  { query: string, max_results?: number }
Output: [{ title, url, snippet }]
```

### `web_fetch`
```
Input:  { url: string }
Output: { text: string }
```
