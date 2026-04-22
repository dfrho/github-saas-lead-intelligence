import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.claude_api import summarize_activity, classify_signal, fetch_company_news, recommend_outreach_angle, detect_company_own_domains, _post_process_news, _titles_overlap, _extract_date


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


# ── hallucination controls ─────────────────────────────────────────────────

class TestExtractDate:
    def test_parses_iso_date(self):
        assert _extract_date("2026-03-01") is not None

    def test_parses_date_from_prose(self):
        assert _extract_date("approximately 2025-06-15") is not None

    def test_returns_none_for_empty(self):
        assert _extract_date("") is None

    def test_returns_none_for_unparseable(self):
        assert _extract_date("recently") is None

    def test_falls_back_to_year_only(self):
        result = _extract_date("2025")
        assert result is not None
        assert result.year == 2025


class TestTitlesOverlap:
    def test_identical_titles_overlap(self):
        assert _titles_overlap("OpenAI raises record funding round", "OpenAI raises record funding round")

    def test_similar_titles_overlap(self):
        assert _titles_overlap(
            "OpenAI Closes Record $122B Funding Round",
            "OpenAI raises $122B in historic funding round"
        )

    def test_unrelated_titles_do_not_overlap(self):
        assert not _titles_overlap("OpenAI raises funding", "Stripe launches new product")

    def test_short_titles_do_not_false_positive(self):
        assert not _titles_overlap("Raises funding", "New launch")


class TestPostProcessNews:
    def _item(self, title, date, url="https://techcrunch.com/article"):
        return {"title": title, "url": url, "date": date, "type": "funding", "snippet": "..."}

    def test_drops_items_older_than_18_months(self):
        old = self._item("Old news", "2020-01-01")
        recent = self._item("Recent news", "2026-01-01")
        result = _post_process_news([old, recent])
        titles = [r["title"] for r in result]
        assert "Old news" not in titles
        assert "Recent news" in titles

    def test_drops_future_items_beyond_30_days(self):
        future = self._item("Future event", "2030-01-01")
        result = _post_process_news([future])
        assert result == []

    def test_keeps_items_with_no_parseable_date(self):
        item = self._item("Undated news", "")
        result = _post_process_news([item])
        assert len(result) == 1

    def test_deduplicates_same_event(self):
        a = self._item("OpenAI Closes Record $122B Funding Round at $852B Valuation", "2026-03-31")
        b = self._item("OpenAI raises $122B in historic funding round valuation", "2026-04-01")
        result = _post_process_news([a, b])
        assert len(result) == 1

    def test_keeps_distinct_events(self):
        a = self._item("OpenAI raises $122B funding round", "2026-03-01")
        b = self._item("Stripe launches new payment product", "2026-03-15")
        result = _post_process_news([a, b])
        assert len(result) == 2

    def test_trusted_sources_sorted_first(self):
        trusted = self._item("TechCrunch coverage", "2026-01-01", url="https://techcrunch.com/article")
        unknown = self._item("Random blog", "2026-02-01", url="https://randomblog.io/post")
        result = _post_process_news([unknown, trusted])
        assert result[0]["title"] == "TechCrunch coverage"


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
        assert result == []

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


# ── recommend_outreach_angle ───────────────────────────────────────────────

class TestRecommendOutreachAngle:
    _signals = [{"domain": "observability_monitoring", "confidence": "high", "reasoning": "Prometheus added."}]
    _news = [{"type": "funding", "title": "Acme raises $50M", "date": "2026-03-01"}]

    def test_returns_text(self):
        client = _mock_client(_text_block("Your team's recent Prometheus work..."))
        with patch("services.claude_api._get_client", return_value=client):
            result = recommend_outreach_angle("They added Prometheus.", self._signals, self._news)
        assert result == "Your team's recent Prometheus work..."

    def test_strips_whitespace(self):
        client = _mock_client(_text_block("  angle text  "))
        with patch("services.claude_api._get_client", return_value=client):
            result = recommend_outreach_angle("synopsis", self._signals, self._news)
        assert result == "angle text"

    def test_synopsis_in_prompt(self):
        client = _mock_client(_text_block("angle"))
        with patch("services.claude_api._get_client", return_value=client):
            recommend_outreach_angle("Migrating to Kafka.", self._signals, self._news)
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Migrating to Kafka." in prompt

    def test_domain_signal_in_prompt(self):
        client = _mock_client(_text_block("angle"))
        with patch("services.claude_api._get_client", return_value=client):
            recommend_outreach_angle("synopsis", self._signals, self._news)
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "observability_monitoring" in prompt

    def test_news_headline_in_prompt(self):
        client = _mock_client(_text_block("angle"))
        with patch("services.claude_api._get_client", return_value=client):
            recommend_outreach_angle("synopsis", self._signals, self._news)
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "Acme raises $50M" in prompt

    def test_handles_empty_signals_and_news(self):
        client = _mock_client(_text_block("angle"))
        with patch("services.claude_api._get_client", return_value=client):
            result = recommend_outreach_angle("synopsis", [], [])
        assert result == "angle"

    def test_caps_signals_at_5_in_prompt(self):
        client = _mock_client(_text_block("angle"))
        signals = [{"domain": f"domain_{i}", "confidence": "high", "reasoning": f"reason {i}"} for i in range(10)]
        with patch("services.claude_api._get_client", return_value=client):
            recommend_outreach_angle("synopsis", signals, [])
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "domain_4" in prompt
        assert "domain_5" not in prompt


# ── detect_company_own_domains ─────────────────────────────────────────────

class TestDetectCompanyOwnDomains:
    def test_returns_valid_domain_list(self):
        payload = '["analytics_bi", "feature_flags"]'
        client = _mock_client(_tool_block(), _text_block(payload))
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("posthog", "posthog.com")
        assert "analytics_bi" in result
        assert "feature_flags" in result

    def test_filters_out_invalid_domain_keys(self):
        # Claude returns a made-up domain — should be stripped
        payload = '["analytics_bi", "not_a_real_domain"]'
        client = _mock_client(_text_block(payload))
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("acme")
        assert "not_a_real_domain" not in result
        assert "analytics_bi" in result

    def test_returns_empty_list_for_empty_array_response(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("acme")
        assert result == []

    def test_returns_empty_list_on_json_parse_failure(self):
        client = _mock_client(_text_block("no json here"))
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("acme")
        assert result == []

    def test_returns_empty_list_when_no_text_block(self):
        client = _mock_client(_tool_block())
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("acme")
        assert result == []

    def test_strips_json_code_fence(self):
        fenced = '```json\n["analytics_bi"]\n```'
        client = _mock_client(_text_block(fenced))
        with patch("services.claude_api._get_client", return_value=client):
            result = detect_company_own_domains("acme")
        assert result == ["analytics_bi"]

    def test_uses_org_domain_in_prompt_when_provided(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            detect_company_own_domains("posthog", "posthog.com")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "posthog.com" in prompt

    def test_falls_back_to_org_com_when_no_domain(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            detect_company_own_domains("myorg")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "myorg.com" in prompt

    def test_web_search_tool_is_passed_to_api(self):
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            detect_company_own_domains("acme")
        call_kwargs = client.messages.create.call_args[1]
        tool_types = [t["type"] for t in call_kwargs["tools"]]
        assert "web_search_20250305" in tool_types

    def test_all_20_domains_described_in_prompt(self):
        from services.claude_api import SAAS_DOMAINS
        client = _mock_client(_text_block("[]"))
        with patch("services.claude_api._get_client", return_value=client):
            detect_company_own_domains("acme")
        prompt = client.messages.create.call_args[1]["messages"][0]["content"]
        for domain in SAAS_DOMAINS:
            assert domain in prompt
