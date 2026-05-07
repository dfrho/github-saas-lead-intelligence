import os
import json
from anthropic import Anthropic

_client = None
_RELEVANCE_THRESHOLD = 7  # out of 10; items scoring below this are dropped


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        _client = Anthropic(api_key=api_key)
    return _client


def rerank_news(org: str, items: list[dict]) -> list[dict]:
    """
    Use Claude as a cross-encoder to score each news item for relevance to org.
    A single batch call scores all items; those below _RELEVANCE_THRESHOLD are dropped.
    On parse failure the original list is returned unchanged.
    """
    if len(items) <= 1:
        return items

    client = _get_client()

    condensed = [
        {"index": i, "title": item.get("title", ""), "snippet": item.get("snippet", "")}
        for i, item in enumerate(items)
    ]

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": (
                    f'Score each news item for relevance to the company "{org}" on a 1–10 scale:\n\n'
                    f"  10 = clearly about {org} (funding, launch, hiring, acquisition, partnership)\n"
                    f"   5 = {org} briefly mentioned or tangentially related\n"
                    "   1 = unrelated or about a different company\n\n"
                    "Return ONLY a JSON array with no explanation:\n"
                    '[{"index": 0, "score": 8}, ...]\n\n'
                    f"Items:\n{json.dumps(condensed, ensure_ascii=False)}"
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
    if start == -1 or end == -1:
        return items

    try:
        scores = json.loads(text[start:end + 1])
        score_map = {entry["index"]: entry["score"] for entry in scores}
    except (json.JSONDecodeError, KeyError):
        return items

    return [item for i, item in enumerate(items) if score_map.get(i, 0) >= _RELEVANCE_THRESHOLD]
