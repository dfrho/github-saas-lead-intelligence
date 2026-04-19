import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.claude_api import summarize_activity, classify_signal, fetch_company_news


# ── helpers ────────────────────────────────────────────────────────────────

def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_block() -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    return block


def _mock_client(*blocks) -> MagicMock:
    """Return a mock Anthropic client whose messages.create returns the given content blocks."""
    response = MagicMock()
    response.content = list(blocks)
    client = MagicMock()
    client.messages.create.return_value = response
    return client


def _activity(commits=None, prs=None, issues=None):
    return {
        "owner": "acme",
        "repo": "api",
        "commits": commits or [],
        "pull_requests": prs or [],
        "issues": issues or [],
    }


# ── summarize_activity ─────────────────────────────────────────────────────

class TestSummarizeActivity:
    def test_returns_synopsis_text(self):
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block("They are migrating to Kafka."))):
            result = summarize_activity(_activity())
        assert result == "They are migrating to Kafka."

    def test_strips_surrounding_whitespace(self):
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block("  synopsis  "))):
            result = summarize_activity(_activity())
        assert result == "synopsis"

    def test_commit_messages_appear_in_prompt(self):
        client = _mock_client(_text_block("synopsis"))
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity(commits=[{"message": "feat: add kafka producer"}]))
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "feat: add kafka producer" in prompt

    def test_pr_titles_appear_in_prompt(self):
        client = _mock_client(_text_block("synopsis"))
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity(prs=[{"title": "Add OAuth2 support"}]))
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Add OAuth2 support" in prompt

    def test_issue_titles_appear_in_prompt(self):
        client = _mock_client(_text_block("synopsis"))
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity(issues=[{"title": "Latency spikes in prod"}]))
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Latency spikes in prod" in prompt

    def test_truncates_to_50_commits(self):
        client = _mock_client(_text_block("synopsis"))
        commits = [{"message": f"commit {i}"} for i in range(100)]
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity(commits=commits))
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "commit 49" in prompt
        assert "commit 50" not in prompt

    def test_truncates_to_30_prs(self):
        client = _mock_client(_text_block("synopsis"))
        prs = [{"title": f"pr {i}"} for i in range(50)]
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity(prs=prs))
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "pr 29" in prompt
        assert "pr 30" not in prompt

    def test_owner_and_repo_appear_in_prompt(self):
        client = _mock_client(_text_block("synopsis"))
        with patch("services.claude_api._get_client", return_value=client):
            summarize_activity(_activity())
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "acme/api" in prompt


# ── classify_signal ────────────────────────────────────────────────────────

class TestClassifySignal:
    _payload = [{"domain": "observability_monitoring", "confidence": "high", "reasoning": "Added Prometheus."}]

    def test_returns_parsed_list(self):
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block(json.dumps(self._payload)))):
            result = classify_signal("They are adding Prometheus metrics.")
        assert result == self._payload

    def test_strips_json_code_fence(self):
        fenced = f"```json\n{json.dumps(self._payload)}\n```"
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block(fenced))):
            result = classify_signal("Prometheus work.")
        assert result == self._payload

    def test_strips_plain_code_fence(self):
        fenced = f"```\n{json.dumps(self._payload)}\n```"
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block(fenced))):
            result = classify_signal("Prometheus work.")
        assert result == self._payload

    def test_raises_on_invalid_json(self):
        with patch("services.claude_api._get_client", return_value=_mock_client(_text_block("not json at all"))):
            with pytest.raises(json.JSONDecodeError):
                classify_signal("some summary")

    def test_summary_appears_in_prompt(self):
        client = _mock_client(_text_block(json.dumps(self._payload)))
        with patch("services.claude_api._get_client", return_value=client):
            classify_signal("Team is building a new auth layer.")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Team is building a new auth layer." in prompt

    def test_all_20_domains_listed_in_prompt(self):
        from services.claude_api import SAAS_DOMAINS
        client = _mock_client(_text_block(json.dumps(self._payload)))
        with patch("services.claude_api._get_client", return_value=client):
            classify_signal("summary")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        for domain in SAAS_DOMAINS:
            assert domain in prompt

    def test_ecommerce_and_marketing_in_domain_list(self):
        from services.claude_api import SAAS_DOMAINS
        assert "ecommerce" in SAAS_DOMAINS
        assert "marketing_communications" in SAAS_DOMAINS

    def test_domain_list_has_20_entries(self):
        from services.claude_api import SAAS_DOMAINS
        assert len(SAAS_DOMAINS) == 20


# ── fetch_company_news ─────────────────────────────────────────────────────

class TestFetchCompanyNews:
    _payload = [{"title": "Acme raises $50M", "url": "https://example.com", "date": "2026-03-01", "type": "funding", "snippet": "Series B round."}]

    def test_returns_parsed_news_list(self):
        client = _mock_client(_text_block(json.dumps(self._payload)))
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert result == self._payload

    def test_extracts_last_text_block_after_tool_use(self):
        client = _mock_client(_tool_block(), _tool_block(), _text_block(json.dumps(self._payload)))
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert result == self._payload

    def test_returns_empty_list_when_response_is_empty_array(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert result == []

    def test_returns_empty_list_when_no_text_block(self):
        client = _mock_client(_tool_block())
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert result == []

    def test_fallback_on_json_parse_failure(self):
        client = _mock_client(_text_block("Some unexpected prose that isn't JSON."))
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert len(result) == 1
        assert result[0]["type"] == "other"
        assert "Some unexpected prose" in result[0]["snippet"]

    def test_strips_json_code_fence(self):
        fenced = f"```json\n{json.dumps(self._payload)}\n```"
        client = _mock_client(_text_block(fenced))
        with patch("services.claude_api._get_client", return_value=client):
            result = fetch_company_news("acme")
        assert result == self._payload

    def test_uses_org_domain_in_prompt_when_provided(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            fetch_company_news("acme", org_domain="acme.com")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "acme.com" in prompt

    def test_falls_back_to_org_name_when_no_domain(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            fetch_company_news("myorg")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "myorg company" in prompt

    def test_web_search_tool_is_passed_to_api(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            fetch_company_news("acme")
        call_kwargs = client.messages.create.call_args[1]
        tool_types = [t["type"] for t in call_kwargs["tools"]]
        assert "web_search_20250305" in tool_types
