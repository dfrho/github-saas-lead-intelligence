import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.github_api import fetch_repo_activity, _fetch_commits, _fetch_pull_requests, _fetch_issues


def _make_commit(sha, name, date_str, message):
    c = MagicMock()
    c.sha = sha
    c.commit.author.name = name
    c.commit.author.date = datetime.fromisoformat(date_str)
    c.commit.message = message
    c.author = None
    return c


def _make_pr(number, title, state, updated_at_str, merged_at=None):
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.state = state
    pr.updated_at = datetime.fromisoformat(updated_at_str).replace(tzinfo=timezone.utc)
    pr.merged_at = datetime.fromisoformat(merged_at) if merged_at else None
    return pr


def _make_issue(number, title, state, labels=None):
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.state = state
    issue.pull_request = None
    issue.labels = [MagicMock(name=l) for l in (labels or [])]
    issue.created_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    issue.closed_at = None
    issue.comments = 0
    return issue


@patch("services.github_api._get_github_client")
def test_fetch_repo_activity_returns_correct_shape(mock_client):
    since = "2026-04-01T00:00:00Z"

    commit = _make_commit("abc123", "Alice", "2026-04-10T12:00:00", "feat: add thing\ndetails")
    pr = _make_pr(42, "My PR", "open", "2026-04-10T12:00:00")
    issue = _make_issue(7, "My Issue", "open")

    repo_mock = MagicMock()
    repo_mock.get_commits.return_value = [commit]
    repo_mock.get_pulls.return_value = [pr]
    repo_mock.get_issues.return_value = [issue]

    mock_client.return_value.get_repo.return_value = repo_mock

    activity = fetch_repo_activity("acme", "api", since=since)

    assert activity.owner == "acme"
    assert activity.repo == "api"
    assert activity.since == since
    assert len(activity.commits) == 1
    assert activity.commits[0].sha == "abc123"
    assert activity.commits[0].message == "feat: add thing"  # subject line only
    assert activity.latest_commit_sha == "abc123"
    assert len(activity.pull_requests) == 1
    assert len(activity.issues) == 1


@patch("services.github_api._get_github_client")
def test_pr_fetch_breaks_on_old_pr(mock_client):
    since = "2026-04-01T00:00:00Z"
    recent_pr = _make_pr(10, "Recent", "open", "2026-04-10T00:00:00")
    old_pr = _make_pr(1, "Old", "closed", "2026-03-01T00:00:00")

    repo_mock = MagicMock()
    repo_mock.get_pulls.return_value = [recent_pr, old_pr]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock

    result = _fetch_pull_requests(github, "acme", "api", since)
    assert len(result) == 1
    assert result[0].number == 10


@patch("services.github_api._get_github_client")
def test_issues_excludes_pull_requests(mock_client):
    since = "2026-04-01T00:00:00Z"
    real_issue = _make_issue(1, "Real issue", "open")
    pr_as_issue = _make_issue(2, "A PR", "open")
    pr_as_issue.pull_request = MagicMock()  # marks it as a PR

    repo_mock = MagicMock()
    repo_mock.get_issues.return_value = [real_issue, pr_as_issue]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock

    result = _fetch_issues(github, "acme", "api", since)
    assert len(result) == 1
    assert result[0].number == 1
