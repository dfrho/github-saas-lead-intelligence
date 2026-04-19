import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.github_api import (
    fetch_repo_activity,
    fetch_contributor_profiles,
    _fetch_commits,
    _fetch_pull_requests,
    _fetch_issues,
)


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


# ── fetch_contributor_profiles ─────────────────────────────────────────────

def _make_contributor(login, contributions):
    c = MagicMock()
    c.login = login
    c.contributions = contributions
    return c


def _make_user(name=None, company=None, location=None, bio=None, public_repos=5, followers=10, orgs=None):
    user = MagicMock()
    user.name = name
    user.company = company
    user.location = location
    user.bio = bio
    user.public_repos = public_repos
    user.followers = followers
    org_mocks = []
    for org_login in (orgs or []):
        org = MagicMock()
        org.login = org_login
        org_mocks.append(org)
    user.get_orgs.return_value = org_mocks
    return user


@patch("services.github_api._get_github_client")
def test_fetch_contributor_profiles_returns_profiles(mock_client):
    contributor = _make_contributor("alice", 42)
    user = _make_user(name="Alice Smith", company="Acme Corp", orgs=["acme-org"])

    repo_mock = MagicMock()
    repo_mock.get_contributors.return_value = [contributor]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock
    github.get_user.return_value = user

    profiles = fetch_contributor_profiles("acme", "api")

    assert len(profiles) == 1
    p = profiles[0]
    assert p.login == "alice"
    assert p.name == "Alice Smith"
    assert p.company == "Acme Corp"
    assert p.contributions == 42
    assert p.orgs == ["acme-org"]


@patch("services.github_api._get_github_client")
def test_fetch_contributor_profiles_fallback_on_user_lookup_failure(mock_client):
    contributor = _make_contributor("ghost", 5)

    repo_mock = MagicMock()
    repo_mock.get_contributors.return_value = [contributor]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock
    github.get_user.side_effect = Exception("User not found")

    profiles = fetch_contributor_profiles("acme", "api")

    assert len(profiles) == 1
    p = profiles[0]
    assert p.login == "ghost"
    assert p.contributions == 5
    assert p.name is None
    assert p.company is None
    assert p.orgs == []


@patch("services.github_api._get_github_client")
def test_fetch_contributor_profiles_org_failure_is_nonfatal(mock_client):
    contributor = _make_contributor("bob", 10)
    user = _make_user(name="Bob Jones", company="Initech")
    user.get_orgs.side_effect = Exception("Org lookup failed")

    repo_mock = MagicMock()
    repo_mock.get_contributors.return_value = [contributor]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock
    github.get_user.return_value = user

    profiles = fetch_contributor_profiles("acme", "api")

    assert len(profiles) == 1
    p = profiles[0]
    assert p.orgs == []
    assert p.name == "Bob Jones"
    assert p.company == "Initech"


@patch("services.github_api._get_github_client")
def test_fetch_contributor_profiles_respects_max_contributors(mock_client):
    contributors = [_make_contributor(f"user{i}", i) for i in range(20)]
    users = {f"user{i}": _make_user(name=f"User {i}") for i in range(20)}

    repo_mock = MagicMock()
    repo_mock.get_contributors.return_value = contributors

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock
    github.get_user.side_effect = lambda login: users[login]

    profiles = fetch_contributor_profiles("acme", "api", max_contributors=5)

    assert len(profiles) == 5


@patch("services.github_api._get_github_client")
def test_fetch_contributor_profiles_orgs_capped_at_10(mock_client):
    contributor = _make_contributor("alice", 1)
    user = _make_user(orgs=[f"org{i}" for i in range(20)])

    repo_mock = MagicMock()
    repo_mock.get_contributors.return_value = [contributor]

    github = mock_client.return_value
    github.get_repo.return_value = repo_mock
    github.get_user.return_value = user

    profiles = fetch_contributor_profiles("acme", "api")

    assert len(profiles[0].orgs) == 10
