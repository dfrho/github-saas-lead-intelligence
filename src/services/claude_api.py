import os
import json
import re
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        _client = Anthropic(api_key=api_key)
    return _client


def summarize_activity(activity_data: dict) -> str:
    """
    Use Claude to summarize what a team is building based on their recent GitHub activity.
    Returns a 2-3 sentence technical synopsis.
    """
    client = _get_client()

    owner = activity_data.get("owner", "")
    repo = activity_data.get("repo", "")

    commits = activity_data.get("commits", [])
    prs = activity_data.get("pull_requests", [])
    issues = activity_data.get("issues", [])

    commit_lines = "\n".join(f"- {c['message']}" for c in commits[:50])
    pr_lines = "\n".join(f"- {pr['title']}" for pr in prs[:30])
    issue_lines = "\n".join(f"- {i['title']}" for i in issues[:30])

    activity_text = (
        f"Repository: {owner}/{repo}\n\n"
        f"Recent commits ({len(commits)} total, showing first 50):\n{commit_lines}\n\n"
        f"Recent pull requests ({len(prs)} total):\n{pr_lines}\n\n"
        f"Recent issues ({len(issues)} total):\n{issue_lines}"
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are analyzing GitHub activity for a software engineering team to identify "
                    "what infrastructure or SaaS categories they are actively building toward.\n\n"
                    "Given the following recent commits, pull requests, and issues, write a concise "
                    "2-3 sentence technical synopsis of what this team is actively working on. "
                    "Focus on infrastructure domains, new integrations, and architectural shifts "
                    "rather than routine feature work.\n\n"
                    f"{activity_text}\n\n"
                    "Write a direct, factual synopsis (2-3 sentences) that identifies the key technical themes."
                ),
            }
        ],
    )

    return response.content[0].text.strip()


SAAS_DOMAINS = [
    "observability_monitoring",
    "auth_identity_sso",
    "messaging_event_streaming",
    "data_pipeline_etl",
    "cicd_devops",
    "database_data_storage",
    "security_compliance",
    "search",
    "feature_flags",
    "api_gateway_service_mesh",
    "testing_qa",
    "infrastructure_iac",
    "cdn_edge_networking",
    "payments_billing",
    "notifications_comms",
    "ml_ai_platform",
    "analytics_bi",
    "support_ticketing",
    "ecommerce",
    "marketing_communications",
]


def classify_signal(summary: str) -> list[dict]:
    """
    Use Claude to classify a synopsis into SaaS domain categories.
    Returns a list of {domain, confidence, reasoning} dicts, sorted by confidence (high first).
    """
    client = _get_client()

    domains_list = "\n".join(f"- {d}" for d in SAAS_DOMAINS)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": (
                    "Given this summary of a software team's recent GitHub activity, identify which "
                    "SaaS/infrastructure categories they are likely to be in-market for within the "
                    "next 60-120 days.\n\n"
                    f"Activity summary:\n{summary}\n\n"
                    f"Available domain categories:\n{domains_list}\n\n"
                    "Return ONLY a JSON array (no explanation, no markdown) of objects with this structure:\n"
                    '[{"domain": "...", "confidence": "high"|"medium"|"low", "reasoning": "one sentence"}]\n\n'
                    "Only include domains where there is meaningful signal. Sort by confidence (high first)."
                ),
            }
        ],
    )

    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    return json.loads(text.strip())


_TRUSTED_NEWS_DOMAINS = {
    "techcrunch.com", "bloomberg.com", "reuters.com", "wsj.com", "ft.com",
    "forbes.com", "businessinsider.com", "venturebeat.com", "theinformation.com",
    "sifted.eu", "axios.com", "cnbc.com", "wired.com", "arstechnica.com",
    "theregister.com", "infoq.com", "devops.com", "thenewstack.io",
    "crunchbase.com", "prnewswire.com", "businesswire.com", "globenewswire.com",
}


def _extract_date(date_str: str):
    """Parse a YYYY-MM-DD or approximate date string. Returns a date or None."""
    if not date_str:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    match = re.search(r"(\d{4})", date_str)
    if match:
        try:
            return datetime(int(match.group(1)), 6, 15).date()  # mid-year estimate
        except ValueError:
            return None
    return None


def _titles_overlap(a: str, b: str) -> bool:
    """Return True if two titles share enough significant words to be the same event."""
    stop = {"the", "a", "an", "and", "or", "of", "in", "at", "to", "for", "is", "on"}
    words_a = {w.lower() for w in re.findall(r"\w+", a) if w.lower() not in stop and len(w) > 3}
    words_b = {w.lower() for w in re.findall(r"\w+", b) if w.lower() not in stop and len(w) > 3}
    if not words_a or not words_b:
        return False
    overlap = words_a & words_b
    return len(overlap) >= 3


def _post_process_news(items: list[dict]) -> list[dict]:
    """
    Apply hallucination controls to raw news items:
    1. Drop items with dates more than 18 months ago or in the future.
    2. Prefer items from trusted news domains (demote others, don't drop).
    3. Deduplicate items that reference the same event (same keywords + close dates).
    """
    today = datetime.now(timezone.utc).date()
    cutoff_past = today - timedelta(days=548)  # ~18 months
    cutoff_future = today + timedelta(days=30)  # allow slight future dates for scheduled events

    # Step 1: date filter
    dated = []
    for item in items:
        d = _extract_date(item.get("date", ""))
        if d is None or (cutoff_past <= d <= cutoff_future):
            dated.append((item, d))

    # Step 2: sort — trusted sources first, then by date descending
    def _sort_key(pair):
        item, d = pair
        url = item.get("url", "")
        trusted = any(domain in url for domain in _TRUSTED_NEWS_DOMAINS)
        date_val = d.toordinal() if d else 0
        return (not trusted, -date_val)

    dated.sort(key=_sort_key)

    # Step 3: deduplicate — skip items that are duplicates of an already-kept item
    kept = []
    for item, d in dated:
        is_dupe = False
        for kept_item, kept_d in kept:
            same_event = _titles_overlap(item.get("title", ""), kept_item.get("title", ""))
            close_dates = (
                d is not None and kept_d is not None and abs((d - kept_d).days) <= 30
            )
            if same_event and close_dates:
                is_dupe = True
                break
        if not is_dupe:
            kept.append((item, d))

    return [item for item, _ in kept]


def fetch_company_news(org: str, org_domain: str = None) -> list[dict]:
    """
    Use Claude with web_search to find recent news/press about a GitHub org.
    Returns a list of {title, url, date, type, snippet} dicts.
    """
    client = _get_client()

    search_target = org_domain if org_domain else f"{org} company"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": (
                    f'Search for recent news about the company "{search_target}" (GitHub org: {org}).\n\n'
                    "Find (up to 8 results total) from the last 18 months only:\n"
                    "1. Funding announcements or investor news\n"
                    "2. Product launch announcements or press releases\n"
                    "3. Technical blog posts indicating infrastructure investment\n"
                    "4. Hiring surges or executive changes\n"
                    "5. Partnerships or acquisitions\n\n"
                    "Prefer results from reputable sources: TechCrunch, Bloomberg, Reuters, Forbes, "
                    "VentureBeat, Axios, PR Newswire, BusinessWire, or the company's own official blog. "
                    "Only include items you are confident are about this specific company. "
                    "Do not include speculative or unverified items.\n\n"
                    "After searching, return ONLY a JSON array (no markdown, max 8 items) of results:\n"
                    '[{"title": "...", "url": "...", "date": "YYYY-MM-DD", '
                    '"type": "funding|launch|technical|hiring|partnership|other", '
                    '"snippet": "1-2 sentence summary"}]\n\n'
                    "Return an empty array [] if nothing relevant is found."
                ),
            }
        ],
    )

    # Extract the final text block (appears after any tool_use blocks)
    final_text = ""
    for block in response.content:
        if block.type == "text":
            final_text = block.text.strip()

    if not final_text or final_text == "[]":
        return []

    # Strip markdown code fences if present
    if "```" in final_text:
        final_text = final_text.split("```")[1]
        if final_text.startswith("json"):
            final_text = final_text[4:]

    # Extract JSON array even if there's surrounding prose
    start = final_text.find("[")
    end = final_text.rfind("]")
    if start != -1 and end != -1:
        final_text = final_text[start:end + 1]

    try:
        items = json.loads(final_text.strip())
        return _post_process_news(items)
    except json.JSONDecodeError:
        return []


_DOMAIN_DESCRIPTIONS = {
    "observability_monitoring": "APM, metrics, tracing, logging infrastructure (Datadog, New Relic, OpenTelemetry)",
    "auth_identity_sso": "authentication, authorization, SSO, identity management (Auth0, Okta, Clerk)",
    "messaging_event_streaming": "message queues, event streaming, pub/sub (Kafka, RabbitMQ, Pub/Sub)",
    "data_pipeline_etl": "ETL, data movement, pipeline orchestration (Fivetran, dbt, Airbyte)",
    "cicd_devops": "CI/CD, build systems, developer tooling (CircleCI, GitHub Actions, Buildkite)",
    "database_data_storage": "databases, object storage, caching (Postgres, MySQL, S3, Redis)",
    "security_compliance": "security scanning, compliance automation, vulnerability management (Snyk, Vanta)",
    "search": "search infrastructure, full-text or vector search (Algolia, Elasticsearch, Typesense)",
    "feature_flags": "feature flags, A/B testing, experimentation (LaunchDarkly, Statsig, Unleash)",
    "api_gateway_service_mesh": "API gateway, rate limiting, service mesh (Kong, Apigee, Traefik)",
    "testing_qa": "test automation, QA infrastructure, browser testing (Playwright, Sauce Labs, Mabl)",
    "infrastructure_iac": "infrastructure as code, cloud provisioning (Terraform, Pulumi, Spacelift)",
    "cdn_edge_networking": "CDN, edge compute, DDoS protection (Cloudflare, Fastly, Bunny.net)",
    "payments_billing": "payment processing, subscriptions, billing (Stripe, Paddle, Lago)",
    "notifications_comms": "notifications, transactional email, SMS (Knock, Novu, Resend)",
    "ml_ai_platform": "ML training, model serving, LLM infrastructure (Weights & Biases, Modal, Replicate)",
    "analytics_bi": "product analytics, BI, dashboards (Mixpanel, Amplitude, Metabase, PostHog)",
    "support_ticketing": "customer support, ticketing, helpdesk (Intercom, Zendesk, Plain)",
    "ecommerce": "ecommerce platform, storefront, cart (Shopify, Medusa, Commerce Layer)",
    "marketing_communications": "marketing automation, email campaigns (Customer.io, Braze, Iterable)",
}


def detect_company_own_domains(org: str, org_domain: str = None) -> list[str]:
    """
    Use Claude with web_search to determine which of our 20 SaaS domain categories
    the company itself operates in as a vendor or product.

    Returns a list of domain keys from SAAS_DOMAINS. These should be excluded from
    vendor recommendations to avoid recommending a company's own products back to them.
    """
    client = _get_client()

    search_target = org_domain if org_domain else f"{org}.com"
    domain_lines = "\n".join(
        f"- {key}: {desc}" for key, desc in _DOMAIN_DESCRIPTIONS.items()
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[
            {
                "role": "user",
                "content": (
                    f'Visit the website for "{search_target}" (GitHub org: {org}) — '
                    f"check their homepage, solutions page, or product navigation.\n\n"
                    f"Identify which of the following SaaS categories describe products or services "
                    f"that this company itself sells or provides:\n\n"
                    f"{domain_lines}\n\n"
                    f"Return ONLY a JSON array of matching domain keys (no explanation, no markdown). "
                    f'Example: ["analytics_bi", "feature_flags"]\n\n'
                    f"Return [] if the company does not sell products in any of these categories."
                ),
            }
        ],
    )

    final_text = ""
    for block in response.content:
        if block.type == "text":
            final_text = block.text.strip()

    if not final_text or final_text == "[]":
        return []

    if "```" in final_text:
        final_text = final_text.split("```")[1]
        if final_text.startswith("json"):
            final_text = final_text[4:]

    start = final_text.find("[")
    end = final_text.rfind("]")
    if start != -1 and end != -1:
        final_text = final_text[start:end + 1]

    try:
        result = json.loads(final_text.strip())
        # Filter to only valid domain keys
        return [d for d in result if d in SAAS_DOMAINS]
    except json.JSONDecodeError:
        return []


def recommend_outreach_angle(
    synopsis: str,
    signals: list[dict],
    news: list[dict],
) -> str:
    """
    Use Claude to write a personalized 1-paragraph outreach angle for a sales rep.
    Combines the activity synopsis, domain signals, and company news into a
    specific, non-generic pitch hook.
    """
    client = _get_client()

    top_signals = [
        f"  - {s['domain']} ({s['confidence']} confidence): {s.get('reasoning', '')}"
        for s in signals[:5]
    ]
    top_news = [
        f"  - [{n.get('type', 'other').upper()}] {n.get('title', '')} ({n.get('date', '')})"
        for n in news[:5]
    ]

    signals_text = "\n".join(top_signals) if top_signals else "  - No domain signals detected"
    news_text = "\n".join(top_news) if top_news else "  - No recent news found"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a senior enterprise sales strategist. Write a 1-paragraph outreach angle "
                    "for a sales rep to use when cold-contacting this company. It should be specific, "
                    "timely, and reference concrete signals — not generic.\n\n"
                    f"What the team is building:\n{synopsis}\n\n"
                    f"Infrastructure signals (SaaS categories they are likely evaluating):\n{signals_text}\n\n"
                    f"Recent company news:\n{news_text}\n\n"
                    "Write a single paragraph (3-5 sentences) that a sales rep could use as an email opener. "
                    "Be direct, reference the specific technical work and/or news, and connect it to a "
                    "concrete pain or inflection point. Do not start with 'I' or use filler phrases like "
                    "'I noticed' or 'I came across'."
                ),
            }
        ],
    )

    return response.content[0].text.strip()
