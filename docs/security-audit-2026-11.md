# Security audit — November 2026

- **Date:** 2026-11-03
- **Scope:** FastAPI backend (`src/api`, `src/services`, `src/scheduler`), Next.js frontend (`web/app`, `web/components`, `web/lib`, `web/next.config.ts`), `Dockerfile`, `.github/`. The MCP entry point (`src/main.py`, `src/cli.py`) and `scripts/` were only skimmed.
- **Standard:** [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
- **Method:** static review of `main` at `33bfcfc`. A few read-only HTTP requests were also sent to the production frontend and API: `GET /docs`, `GET /openapi.json`, `GET /redoc`, `GET /reports/status/not-a-uuid`, response headers, and a CORS preflight. No project code, package manager or scanner was run as part of the audit.
- **Baseline:** this is a follow-up to the remediation recorded in the README's **Security** section. Issues already fixed there are not repeated here.

## Summary

No Critical, High or Medium issues were found. The earlier remediation holds up:
- every SQL query is parameterized
- report and watch-list reads are scoped to the signed-in user
- tokens are verified against asymmetric keys only
- untrusted text is fenced before it reaches Claude
- report runs are rate-limited and capped

The seven findings below are all hardening gaps. Each is fixed in the same pull request as this report.

| Severity | Count |
| --- | --- |
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 6 |
| Informational | 1 |

| Confidence | Count |
| --- | --- |
| High | 6 |
| Medium | 1 |

## Findings

### A02 Security Misconfiguration

#### OWASP-A02-001 — API container runs as root

- **CWE:** none from A02:2025's mapped list fits exactly. The closest MITRE entry is [CWE-250](https://cwe.mitre.org/data/definitions/250.html), Execution with Unnecessary Privileges.
- **Severity:** Low. This only matters if a separate code-execution flaw exists, but it would make one more damaging: full write access to the image filesystem and to installed packages.
- **Confidence:** High that the image has no `USER` instruction. Medium on impact, because it isn't known whether Railway's runtime drops privileges on its own.
- **Location:** `Dockerfile`. There is no `USER` instruction, so `uvicorn` runs as UID 0.
- **Reachability:** any remote code execution in the API process, for example through a future dependency CVE.
- **Fix:** create an unprivileged system user (UID 10001) and switch to it before `CMD`. The API writes nothing to disk at runtime: reports and the registry live in Postgres when `USE_DB=true`.
- **Verify:** after deploy, confirm the service starts and a report run completes.

#### OWASP-A02-002 — Interactive API docs and OpenAPI schema served in production

- **CWE:** none from the mapped list fits. This is a default framework component left enabled (guide A02.9).
- **Severity:** Informational. Every endpoint enforces its own auth, so the schema only speeds up reconnaissance.
- **Confidence:** High. Production returned `200` for `/docs`, `/redoc` and `/openapi.json`.
- **Location:** `src/api/main.py`, the `FastAPI(...)` constructor with default `docs_url`, `redoc_url` and `openapi_url`.
- **Fix:** the docs are now off unless `ENABLE_API_DOCS=true` is set. Local development can still enable them.

### A06 Insecure Design

#### OWASP-A06-001 — Profile fields accept unbounded text

- **CWE:** none from A06:2025's mapped list fits.
- **Severity:** Low. A signed-in user can store arbitrarily large `company_name` / `work_domain` values in `user_profiles`. That costs storage, but the values aren't used in any prompt or shared view.
- **Confidence:** Medium. The request-body limit at Railway's edge isn't known.
- **Location:** `src/api/routers/users.py`, `UserProfileRequest`.
- **Entry point:** `POST /users/me` with a valid token.
- **Fix:** cap the fields at 200 and 253 characters. 253 is the maximum length of a DNS name.

### A07 Authentication Failures

#### OWASP-A07-001 — JWT issuer and audience not verified

- **CWE:** [CWE-287](https://cwe.mitre.org/data/definitions/287.html), Improper Authentication.
- **Severity:** Low. Signatures are already verified against this project's JWKS. So only a token signed with the project's own keys but meant for a different audience or issuer would slip through, and Supabase doesn't currently issue such tokens to clients.
- **Confidence:** High. Traced in code.
- **Location:** `src/api/auth.py`, `_decode_token`. Previously:

  ```python
  return jwt.decode(token, signing_key.key, algorithms=_ALGORITHMS_ASYMMETRIC,
                    options={"verify_aud": False})
  ```

  PyJWT also accepts tokens with no `exp` claim unless told to require it.
- **Entry point:** the `Authorization: Bearer` header on every protected route.
- **Fix:** require `iss` = `<SUPABASE_URL>/auth/v1` and `aud` = `authenticated`, and require `exp`, `sub`, `iss` and `aud` to be present. `SUPABASE_JWT_ISSUER` and `SUPABASE_JWT_AUDIENCE` override the defaults if the project moves to a custom auth domain.
- **Verify:** sign in on production right after deploy. If every request starts returning 401, compare the token's `iss` claim with `SUPABASE_URL` on Railway.

### A08 Software or Data Integrity Failures

#### OWASP-A08-001 — CI actions referenced by mutable tags

- **CWE:** [CWE-829](https://cwe.mitre.org/data/definitions/829.html), Inclusion of Functionality from Untrusted Control Sphere.
- **Severity:** Low. A moved or compromised tag would run attacker code in CI. Impact is narrow here: the workflow runs with a read-only `contents` token, holds no secrets, and doesn't deploy. Vercel and Railway build separately.
- **Confidence:** High.
- **Location:** `.github/workflows/tests.yml`, which used `actions/checkout@v4`, `actions/setup-python@v5` and `actions/setup-node@v4`.
- **Fix:** pin each action to the full commit SHA of its current release, with the version in a comment. The SHAs were checked against the upstream tags with `git ls-remote`. Also:
  - add GitHub Actions to Dependabot so the pins get updated
  - set `persist-credentials: false` on checkout

### A09 Security Logging and Alerting Failures

#### OWASP-A09-001 — Client-controlled token header written raw to logs

- **CWE:** [CWE-117](https://cwe.mitre.org/data/definitions/117.html), Improper Output Neutralization for Logs.
- **Severity:** Low. An anonymous caller can put newlines into the token's `alg` header. That header is echoed in the exception message and printed as-is, which forges extra log lines in the Railway console. The logs aren't rendered as HTML anywhere.
- **Confidence:** High.
- **Location:** `src/api/auth.py`, `get_current_user`. Previously `print(f"[AUTH DEBUG] JWT validation failed: {type(e).__name__}: {e} ...")`.
- **Entry point:** any protected route, with an `Authorization` header holding a hand-built token.
- **Fix:** log through `logging.warning` with `%r`, which escapes control characters. The message also no longer includes part of the Supabase URL.

### A10 Mishandling of Exceptional Conditions

#### OWASP-A10-001 — Malformed report IDs crash the request with a 500

- **CWE:** [CWE-754](https://cwe.mitre.org/data/definitions/754.html), Improper Check for Unusual or Exceptional Conditions.
- **Severity:** Low. The response body is FastAPI's generic `Internal Server Error`, so nothing leaks. But the unchecked value reaches Postgres, raises an unhandled error, and adds noise to the error logs on a public endpoint.
- **Confidence:** High. Production returned `500` for `GET /reports/status/not-a-uuid`.
- **Location:** `src/api/routers/reports.py`, where `report_id: str` on the status, detail and export routes is passed straight into `WHERE id = %s` against a `UUID` column.
- **Fix:** declare `report_id: uuid.UUID`, so FastAPI rejects malformed IDs with `422` before any database work.

## Reviewed with no finding

- **Access control (A01):**
  - Reports, exports and watch lists are filtered by `user_id` in SQL.
  - An anonymous report can be claimed only by someone holding its random `gen_random_uuid()` ID.
  - `safeNext()` keeps post-login redirects same-origin.
  - Repository names are validated before any GitHub call, and only public repositories are accepted.
- **CSRF (A01):** the API authenticates with a bearer header, not cookies.
- **CORS (A02):** a single allowed origin. A preview-URL preflight was rejected with `400`.
- **Injection (A05):**
  - All SQL is parameterized. The one dynamic `SET` clause in `registry._db_update` is built only from an allowlist of column names.
  - Markdown renders without raw HTML or images, and with react-markdown's default URL sanitizing.
  - CSV cells are formula-escaped.
  - Untrusted text is fenced, with `UNTRUSTED_SYSTEM` set on every Claude call.
- **Deserialization (A08):** only JSON is parsed. There's no `pickle`, YAML or native deserialization of request data.
- **SSRF (A01):** the server makes outbound requests only to the GitHub API with validated paths, to Supabase JWKS at a fixed URL, and to Anthropic. `org_domain` only reaches a web-search prompt, and must be a bare hostname.
- **Response headers:** production returns HSTS (`max-age=63072000; includeSubDomains; preload`) and `X-Frame-Options: DENY`.

## Coverage

| Category | Status | Notes |
| --- | --- | --- |
| A01 Broken Access Control | Assessed | Supabase row-level security policies can't be checked from the repo; the README documents them. |
| A02 Security Misconfiguration | Partially assessed | Railway and Vercel settings beyond observable headers weren't visible. |
| A03 Software Supply Chain Failures | Partially assessed | Lockfiles and Dependabot reviewed. No `pip-audit` / `npm audit` run (would need approval). Four Dependabot major-version PRs (#1–#4) are open and unreviewed. |
| A04 Cryptographic Failures | Assessed | Asymmetric JWT verification only; no custom cryptography. |
| A05 Injection | Assessed | Prompt injection is mitigated, not eliminated. Model output is still untrusted. |
| A06 Insecure Design | Assessed | Business intent behind anonymous report claiming taken from the README. |
| A07 Authentication Failures | Assessed | Google sign-in and session handling are Supabase-managed and out of scope. |
| A08 Software or Data Integrity Failures | Assessed | |
| A09 Security Logging and Alerting Failures | Partially assessed | Log retention and alerting live in Railway. Alerting on 401/429 spikes is still an open item. |
| A10 Mishandling of Exceptional Conditions | Assessed | |

## Open items (unchanged from the previous audit)

- Enforce the Content-Security-Policy. It is still report-only.
- Move rate-limit state to a shared store if the API runs on more than one instance.
- Add alerting on authentication and rate-limit anomalies.

## Limitations

This was a static review, plus the read-only production requests listed under **Method**. It doesn't confirm:
- runtime behaviour or deployed environment variables
- dependency CVEs
- Supabase row-level security
- the behaviour of the Google OAuth configuration
