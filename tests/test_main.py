import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import main


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
