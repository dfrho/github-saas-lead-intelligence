import os
import json
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
                    "Find (up to 8 results total):\n"
                    "1. Funding announcements or investor news (last 12 months)\n"
                    "2. Product launch announcements or press releases\n"
                    "3. Technical blog posts indicating infrastructure investment\n"
                    "4. Hiring surges or executive changes\n"
                    "5. Partnerships or acquisitions\n\n"
                    "After searching, return ONLY a JSON array (no markdown, max 8 items) of results:\n"
                    '[{"title": "...", "url": "...", "date": "YYYY-MM-DD or approximate", '
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
        return json.loads(final_text.strip())
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
