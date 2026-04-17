# Enrichment Signal Ideas

Novel angles for predicting whether a repo owner is a high-quality lead.

## Activity Signals
- **Commit velocity trend** — is activity accelerating or decelerating over the last 90 days?
- **Commit-to-merge ratio** — high ratio of open PRs to merges may indicate a bottleneck (pain point)
- **Night/weekend commit ratio** — high ratio suggests a small/scrappy team burning hot

## Dependency Signals
- **Outdated critical dependencies** — major version lag on security-sensitive packages (e.g. auth, crypto)
- **Competing tool in deps** — presence of a direct competitor signals awareness of the problem space
- **Missing category** — no logging, no observability, no testing lib for a >1k star repo = gap to fill
- **Dependency count explosion** — rapid growth in `package.json` size over recent commits

## Team & Org Signals
- **Solo maintainer flag** — single contributor handling >80% of commits; high receptivity to tools that reduce burden
- **Contributor churn** — contributors who appeared then disappeared; may signal team scaling pain
- **Bus factor** — number of contributors who know >50% of the codebase (low = risk = pain point)
- **First-time org repo** — company's first public repo; likely exploring tooling

## Pain Point Signals (Issues / PRs)
- **Issue label mining** — frequency of labels like `bug`, `performance`, `help wanted`, `security`
- **Long-lived open issues** — issues open >90 days with high comment counts = unresolved pain
- **PR description quality** — sparse PR descriptions may indicate process immaturity
- **Stale PR count** — PRs open >30 days without activity

## Growth Signals
- **Star velocity** — stars/week over last 30 days vs. prior 30 days
- **Fork-to-star ratio** — high ratio suggests active use, not just passive interest
- **Topic tag expansion** — new topics added recently may signal a pivot or product expansion
- **Readme updates** — frequent readme edits often precede a launch or fundraise

## External Signals
- **Hacker News / Reddit mentions** — recent discussion may indicate growth moment
- **Job postings** — company hiring for roles related to the repo's domain
- **npm/PyPI download trend** — week-over-week download change for published packages
