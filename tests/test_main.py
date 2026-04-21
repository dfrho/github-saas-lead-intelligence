import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import main
from main import _score_lead, _score_label


# ── analyze_repo ───────────────────────────────────────────────────────────

def _make_activity(owner="acme", repo="api", commits=None, prs=None, issues=None):
    activity = MagicMock()
    activity.owner = owner
    activity.repo = repo
    activity.commits = [MagicMock(message=m) for m in (commits or ["feat: add kafka"])]
    activity.pull_requests = [MagicMock(title=t) for t in (prs or ["Add Kafka producer"])]
    activity.issues = [MagicMock(title=t) for t in (issues or [])]
    return activity


_classifications = [
    {"domain": "messaging_event_streaming", "confidence": "high", "reasoning": "Kafka integration."},
    {"domain": "observability_monitoring",  "confidence": "low",  "reasoning": "Minor metrics work."},
]


@pytest.mark.asyncio
async def test_analyze_repo_chains_summarize_then_classify():
    activity = _make_activity()
    with (
        patch("main.github_api.fetch_repo_activity", return_value=activity),
        patch("main.claude_api.summarize_activity", return_value="They are adding Kafka.") as mock_summarize,
        patch("main.claude_api.classify_signal", return_value=_classifications) as mock_classify,
    ):
        result = await main.analyze_repo("acme", "api")

    mock_summarize.assert_called_once()
    # classify_signal must receive the synopsis returned by summarize_activity
    mock_classify.assert_called_once_with("They are adding Kafka.")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_analyze_repo_json_output_contains_synopsis_and_signals():
    activity = _make_activity()
    with (
        patch("main.github_api.fetch_repo_activity", return_value=activity),
        patch("main.claude_api.summarize_activity", return_value="They are adding Kafka."),
        patch("main.claude_api.classify_signal", return_value=_classifications),
    ):
        result = await main.analyze_repo("acme", "api")

    output = json.loads(result[1].text)
    assert output["synopsis"] == "They are adding Kafka."
    assert output["signals"] == _classifications
    assert output["owner"] == "acme"
    assert output["repo"] == "api"


@pytest.mark.asyncio
async def test_analyze_repo_summary_text_lists_domains():
    activity = _make_activity()
    with (
        patch("main.github_api.fetch_repo_activity", return_value=activity),
        patch("main.claude_api.summarize_activity", return_value="They are adding Kafka."),
        patch("main.claude_api.classify_signal", return_value=_classifications),
    ):
        result = await main.analyze_repo("acme", "api")

    summary = result[0].text
    assert "messaging_event_streaming" in summary
    assert "observability_monitoring" in summary
    assert "HIGH" in summary
    assert "LOW" in summary


@pytest.mark.asyncio
async def test_analyze_repo_passes_since_to_fetch():
    activity = _make_activity()
    with (
        patch("main.github_api.fetch_repo_activity", return_value=activity) as mock_fetch,
        patch("main.claude_api.summarize_activity", return_value="synopsis"),
        patch("main.claude_api.classify_signal", return_value=[]),
    ):
        await main.analyze_repo("acme", "api", since="2026-01-01T00:00:00Z")

    mock_fetch.assert_called_once_with("acme", "api", "2026-01-01T00:00:00Z")


# ── _score_lead ────────────────────────────────────────────────────────────

class TestScoreLead:
    def _commits(self, n): return [MagicMock()] * n
    def _prs(self, n): return [MagicMock()] * n
    def _issues(self, n, labeled=0):
        issues = [{"state": "open", "labels": []} for _ in range(n - labeled)]
        issues += [{"state": "open", "labels": ["bug"]} for _ in range(labeled)]
        return issues
    def _contributors(self, n): return [{"contributions": 10}] * n
    def _news(self, types): return [{"type": t} for t in types]

    def test_returns_score_and_breakdown(self):
        score, breakdown = _score_lead(
            self._commits(10), self._prs(5), self._issues(5), self._contributors(5), [], []
        )
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert set(breakdown.keys()) == {"activity", "pain_points", "dependencies", "team_size", "growth"}

    def test_dependencies_always_zero(self):
        _, breakdown = _score_lead(
            self._commits(10), self._prs(5), self._issues(5), self._contributors(5), [], []
        )
        assert breakdown["dependencies"]["score"] == 0

    def test_high_activity_raises_score(self):
        score_high, _ = _score_lead(
            self._commits(50), self._prs(20), [], self._contributors(5), [], []
        )
        score_low, _ = _score_lead(
            self._commits(1), self._prs(0), [], self._contributors(5), [], []
        )
        assert score_high > score_low

    def test_pain_labels_increase_pain_score(self):
        _, bd_labeled = _score_lead([], [], self._issues(10, labeled=8), self._contributors(5), [], [])
        _, bd_clean = _score_lead([], [], self._issues(10, labeled=0), self._contributors(5), [], [])
        assert bd_labeled["pain_points"]["score"] >= bd_clean["pain_points"]["score"]

    def test_funding_news_raises_growth_score(self):
        _, bd_funded = _score_lead([], [], [], self._contributors(5), self._news(["funding", "funding"]), [])
        _, bd_empty = _score_lead([], [], [], self._contributors(5), [], [])
        assert bd_funded["growth"]["score"] > bd_empty["growth"]["score"]

    def test_sweet_spot_team_size_scores_higher(self):
        _, bd_good = _score_lead([], [], [], self._contributors(10), [], [])
        _, bd_solo = _score_lead([], [], [], self._contributors(1), [], [])
        _, bd_huge = _score_lead([], [], [], self._contributors(100), [], [])
        assert bd_good["team_size"]["score"] > bd_solo["team_size"]["score"]
        assert bd_good["team_size"]["score"] > bd_huge["team_size"]["score"]


class TestScoreLabel:
    def test_hot(self): assert _score_label(85) == "Hot lead"
    def test_warm(self): assert _score_label(65) == "Warm lead"
    def test_lukewarm(self): assert _score_label(50) == "Lukewarm"
    def test_low(self): assert _score_label(30) == "Low priority"
    def test_boundaries(self):
        assert _score_label(80) == "Hot lead"
        assert _score_label(79) == "Warm lead"
        assert _score_label(60) == "Warm lead"
        assert _score_label(59) == "Lukewarm"
        assert _score_label(40) == "Lukewarm"
        assert _score_label(39) == "Low priority"


# ── recommend_saas_vendors ─────────────────────────────────────────────────

class TestRecommendSaasVendors:
    @pytest.mark.asyncio
    async def test_returns_vendors_for_high_signals(self):
        signals = [{"domain": "observability_monitoring", "confidence": "high", "reasoning": "Prometheus."}]
        result = await main.recommend_saas_vendors(signals)
        assert len(result) == 2  # summary + JSON
        data = json.loads(result[1].text)
        assert data[0]["domain"] == "observability_monitoring"

    @pytest.mark.asyncio
    async def test_returns_message_for_low_confidence_only(self):
        signals = [{"domain": "search", "confidence": "low", "reasoning": "Minor."}]
        result = await main.recommend_saas_vendors(signals)
        assert len(result) == 1
        assert "low confidence" in result[0].text.lower() or "no vendor" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_empty_signals_returns_message(self):
        result = await main.recommend_saas_vendors([])
        assert len(result) == 1


# ── generate_lead_report ───────────────────────────────────────────────────

def _make_full_activity():
    activity = MagicMock()
    activity.owner = "acme"
    activity.repo = "api"
    activity.commits = [MagicMock(message="feat: add kafka")] * 15
    activity.pull_requests = [MagicMock(title="Add Kafka producer")] * 5
    activity.issues = [MagicMock(title="Latency issue", state="open", labels=["bug"])] * 3
    return activity


_signals = [{"domain": "messaging_event_streaming", "confidence": "high", "reasoning": "Kafka work."}]
_news = [{"type": "funding", "title": "Acme raises $10M", "date": "2026-03-01", "snippet": "Series A."}]

# MagicMock(name=...) sets the mock's internal name, not the .name attribute — set explicitly
_alice = MagicMock()
_alice.login = "alice"
_alice.name = "Alice"
_alice.company = "Acme"
_alice.contributions = 42
_alice.orgs = []
_contributors = [_alice]
_vendors = [{"domain": "messaging_event_streaming", "confidence": "high", "reasoning": "Kafka work.", "vendors": [{"name": "Confluent", "url": "https://confluent.io", "pitch": "Managed Kafka."}]}]


_dep_analysis = MagicMock()
_dep_analysis.score = 60
_dep_analysis.ecosystem = "node"
_dep_analysis.detected_packages = ["express", "stripe"]
_dep_analysis.flags = []


def _patch_generate(tmp_path, outreach="Outreach.", write_return=None):
    """Return a context manager that patches all external calls in generate_lead_report."""
    from unittest.mock import patch as _patch
    from contextlib import ExitStack

    class _Stack:
        def __enter__(self):
            self._stack = ExitStack()
            activity = _make_full_activity()
            self._stack.enter_context(_patch("main.github_api.fetch_repo_activity", return_value=activity))
            self._stack.enter_context(_patch("main.claude_api.summarize_activity", return_value="They are adding Kafka."))
            self._stack.enter_context(_patch("main.claude_api.classify_signal", return_value=_signals))
            self._stack.enter_context(_patch("main.github_api.fetch_contributor_profiles", return_value=_contributors))
            self._stack.enter_context(_patch("main.claude_api.fetch_company_news", return_value=_news))
            self._stack.enter_context(_patch("main.get_vendors_for_domains", return_value=_vendors))
            self._stack.enter_context(_patch("main.claude_api.recommend_outreach_angle", return_value=outreach))
            self._stack.enter_context(_patch("main.github_api.fetch_dependency_files", return_value={}))
            self._stack.enter_context(_patch("main.analyze_dependencies", return_value=_dep_analysis))
            self._stack.enter_context(_patch("main._write_report", return_value=write_return or tmp_path / "report.md"))
            return self._stack.__enter__()

        def __exit__(self, *args):
            return self._stack.__exit__(*args)

    return _Stack()


@pytest.mark.asyncio
async def test_generate_lead_report_writes_file(tmp_path):
    with _patch_generate(tmp_path) as mocks:
        result = await main.generate_lead_report("acme", "api")
    assert len(result) == 2


@pytest.mark.asyncio
async def test_generate_lead_report_json_has_required_fields(tmp_path):
    with _patch_generate(tmp_path):
        result = await main.generate_lead_report("acme", "api")

    report = json.loads(result[1].text)
    assert report["repo"] == "acme/api"
    assert "lead_score" in report
    assert "lead_label" in report
    assert "synopsis" in report
    assert "signals" in report
    assert "vendors" in report
    assert "recommended_angle" in report
    assert "score_breakdown" in report
    assert "enrichment" in report


@pytest.mark.asyncio
async def test_run_full_analysis_returns_summary_and_json(tmp_path):
    with _patch_generate(tmp_path):
        result = await main.run_full_analysis("acme", "api")

    assert len(result) == 2
    summary = result[0].text
    assert "acme/api" in summary
    assert "Lead Score" in summary
    report = json.loads(result[1].text)
    assert report["repo"] == "acme/api"
