# Report Format

Each report is produced in two formats: structured JSON and a human-readable Markdown summary.

## JSON Schema

```json
{
  "repo": "owner/repo",
  "generated_at": "ISO8601",
  "lead_score": 0,
  "score_breakdown": {
    "activity":      { "score": 0, "weight": 0.25, "signals": [] },
    "dependencies":  { "score": 0, "weight": 0.20, "signals": [] },
    "team_size":     { "score": 0, "weight": 0.15, "signals": [] },
    "pain_points":   { "score": 0, "weight": 0.25, "signals": [] },
    "growth":        { "score": 0, "weight": 0.15, "signals": [] }
  },
  "enrichment": {
    "repo_meta":      {},
    "commit_velocity": {},
    "open_issues":     [],
    "top_contributors": [],
    "ci_cd":           {},
    "dependency_flags": []
  },
  "summary": "",
  "recommended_angle": ""
}
```

## Markdown Template

```markdown
# Lead Report: {owner}/{repo}

**Lead Score:** {lead_score}/100  
**Generated:** {generated_at}

## Score Breakdown
| Domain       | Score | Weight |
|--------------|-------|--------|
| Activity     | ...   | 25%    |
| Dependencies | ...   | 20%    |
| Team Size    | ...   | 15%    |
| Pain Points  | ...   | 25%    |
| Growth       | ...   | 15%    |

## Key Signals
- ...

## Enrichment Highlights
### Commit Velocity
...

### Open Issues / Pain Points
...

### CI/CD Setup
...

### Dependency Red Flags
...

## Summary
{summary}

## Recommended Outreach Angle
{recommended_angle}
```

## Score Bands

| Score | Label |
|-------|-------|
| 80–100 | Hot lead |
| 60–79  | Warm lead |
| 40–59  | Lukewarm |
| 0–39   | Low priority |
