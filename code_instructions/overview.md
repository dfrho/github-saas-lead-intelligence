# Architecture Overview

## High-Level Flow

```
Input: GitHub repo URL or owner/repo slug
         │
         ▼
   [Fetcher Layer]
   src/services/github.js   ← GitHub REST/GraphQL API
   src/services/npm.js       ← npm registry (if JS project)
   src/services/pypi.js      ← PyPI (if Python project)
         │
         ▼
   [Enrichment Layer]
   src/enrichers/            ← one file per signal domain
         │
         ▼
   [Scoring Layer]
   src/scoring/              ← weighted signal → lead score
         │
         ▼
   [Report Layer]
   src/report/               ← formats final output
         │
         ▼
Output: Structured JSON + human-readable Markdown report
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `src/services/` | Raw API calls, rate limiting, caching |
| `src/enrichers/` | Transform raw data into named signals |
| `src/scoring/` | Aggregate signals into a lead score (0–100) |
| `src/report/` | Render JSON + Markdown output |
| `src/index.js` | CLI entry point |

## Environment Variables
- `GITHUB_TOKEN` — Personal access token for GitHub API
- `NPM_REGISTRY_URL` — Optional custom npm registry
