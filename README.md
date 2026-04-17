# GitHub Lead Intelligence

Enriches GitHub repositories with signals that predict whether a repo owner is a high-quality lead.

## Structure

```
├── CLAUDE.md                  ← Claude Code instructions
├── code_instructions/
│   ├── overview.md            ← Architecture
│   ├── mcp_tool_schema.md     ← MCP tool signatures
│   ├── report_format.md       ← Report template (JSON + Markdown)
│   └── enrichment_ideas.md    ← Signal ideas
├── src/                       ← Implementation
└── README.md
```

## Setup

```bash
export GITHUB_TOKEN=your_token_here
```

## Usage

```bash
node src/index.js owner/repo
```

## Output

Produces a lead score (0–100) and a structured report covering activity, dependencies, team size, pain points, and growth signals.
