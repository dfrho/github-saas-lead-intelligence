import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from github import Github, Auth


@dataclass
class Commit:
    """Represents a commit in a repository."""
    sha: str
    author: Optional[str]  # Author name or login
    date: Optional[str]  # ISO 8601 timestamp
    message: str  # Subject line (first line) only


@dataclass
class PullRequest:
    """Represents a pull request in a repository."""
    number: int
    title: str
    state: str  # "open", "closed"
    merged_at: Optional[str]  # ISO 8601 timestamp if merged


@dataclass
class Issue:
    """Represents an issue in a repository."""
    number: int
    title: str
    state: str  # "open", "closed"
    labels: list[str]
    created_at: str  # ISO 8601 timestamp
    closed_at: Optional[str]  # ISO 8601 timestamp if closed
    comments: int


@dataclass
class RepoActivity:
    """Aggregated activity data for a repository."""
    owner: str
    repo: str
    fetched_at: str  # ISO 8601 timestamp of when data was fetched
    since: str  # The query date (resolved default or provided)
    commits: list[Commit]
    pull_requests: list[PullRequest]
    issues: list[Issue]
    latest_commit_sha: Optional[str]  # SHA of the most recent commit


@dataclass
class ContributorProfile:
    """GitHub profile data for a repository contributor."""
    login: str
    name: Optional[str]
    company: Optional[str]
    location: Optional[str]
    bio: Optional[str]
    public_repos: int
    followers: int
    contributions: int  # contributions to this specific repo
    orgs: list[str]    # public org memberships (logins)


def _get_github_client() -> Github:
    """Create and return a GitHub API client."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return Github(auth=Auth.Token(token))


def _fetch_commits(github: Github, owner: str, repo: str, since_str: str) -> list[Commit]:
    """Fetch commits for a repository since a given date."""
    repo_obj = github.get_repo(f"{owner}/{repo}")

    # Parse since_str to datetime
    since_dt = datetime.fromisoformat(since_str.replace("Z", "+00:00"))

    commits = []
    for commit in repo_obj.get_commits(since=since_dt)[:500]:
        author_name = None
        if commit.commit.author:
            author_name = commit.commit.author.name
        if not author_name and commit.author:
            author_name = commit.author.login

        # Get subject line (first line of message)
        message = commit.commit.message.split("\n")[0]

        commits.append(
            Commit(
                sha=commit.sha,
                author=author_name,
                date=commit.commit.author.date.isoformat() if commit.commit.author else None,
                message=message,
            )
        )

    return commits


def _fetch_pull_requests(github: Github, owner: str, repo: str, since_str: str) -> list[PullRequest]:
    """Fetch pull requests for a repository."""
    repo_obj = github.get_repo(f"{owner}/{repo}")
    since_dt = datetime.fromisoformat(since_str.replace("Z", "+00:00"))

    prs = []
    for pr in repo_obj.get_pulls(state="all", sort="updated", direction="desc"):
        if pr.updated_at and pr.updated_at < since_dt:
            break  # sorted descending — nothing older will match

        prs.append(
            PullRequest(
                number=pr.number,
                title=pr.title,
                state=pr.state,
                merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
            )
        )

    return prs


def _fetch_issues(github: Github, owner: str, repo: str, since_str: str) -> list[Issue]:
    """Fetch issues (excluding PRs) for a repository since a given date."""
    repo_obj = github.get_repo(f"{owner}/{repo}")
    since_dt = datetime.fromisoformat(since_str.replace("Z", "+00:00"))

    issues = []
    for item in repo_obj.get_issues(state="all", since=since_dt):
        # Skip if it's actually a PR
        if item.pull_request:
            continue

        labels = [label.name for label in item.labels] if item.labels else []

        issues.append(
            Issue(
                number=item.number,
                title=item.title,
                state=item.state,
                labels=labels,
                created_at=item.created_at.isoformat(),
                closed_at=item.closed_at.isoformat() if item.closed_at else None,
                comments=item.comments,
            )
        )

    return issues


def fetch_repo_activity(
    owner: str,
    repo: str,
    since: Optional[str] = None,
) -> RepoActivity:
    """
    Fetch recent commits, pull requests, and issues for a repository.

    Args:
        owner: GitHub organization or user name
        repo: Repository name
        since: ISO 8601 date string to fetch activity since (defaults to 30 days ago)

    Returns:
        RepoActivity object with commits, PRs, issues, and latest commit SHA
    """
    github = _get_github_client()

    # Resolve since date (default to 30 days ago)
    if since is None:
        from datetime import timedelta
        since_dt = datetime.now(timezone.utc) - timedelta(days=30)
        since = since_dt.isoformat().replace("+00:00", "Z")
    else:
        since = since if since.endswith("Z") else since.replace("Z", "") + "Z"

    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Fetch in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        commits_future = executor.submit(_fetch_commits, github, owner, repo, since)
        prs_future = executor.submit(_fetch_pull_requests, github, owner, repo, since)
        issues_future = executor.submit(_fetch_issues, github, owner, repo, since)

        commits = commits_future.result()
        pull_requests = prs_future.result()
        issues = issues_future.result()

    # Extract latest commit SHA
    latest_commit_sha = commits[0].sha if commits else None

    return RepoActivity(
        owner=owner,
        repo=repo,
        fetched_at=fetched_at,
        since=since,
        commits=commits,
        pull_requests=pull_requests,
        issues=issues,
        latest_commit_sha=latest_commit_sha,
    )


def fetch_contributor_profiles(
    owner: str,
    repo: str,
    max_contributors: int = 10,
) -> list[ContributorProfile]:
    """
    Fetch GitHub profile data for the top contributors of a repository.

    Args:
        owner: GitHub organization or user name
        repo: Repository name
        max_contributors: Maximum number of contributors to fetch (default 10)

    Returns:
        List of ContributorProfile objects sorted by contribution count (descending)
    """
    github = _get_github_client()
    repo_obj = github.get_repo(f"{owner}/{repo}")

    contributors = list(repo_obj.get_contributors()[:max_contributors])

    def _fetch_profile(contributor) -> ContributorProfile:
        try:
            user = github.get_user(contributor.login)
            orgs: list[str] = []
            try:
                orgs = [org.login for org in user.get_orgs()][:10]
            except Exception:
                pass
            return ContributorProfile(
                login=contributor.login,
                name=user.name,
                company=user.company,
                location=user.location,
                bio=user.bio,
                public_repos=user.public_repos,
                followers=user.followers,
                contributions=contributor.contributions,
                orgs=orgs,
            )
        except Exception:
            return ContributorProfile(
                login=contributor.login,
                name=None,
                company=None,
                location=None,
                bio=None,
                public_repos=0,
                followers=0,
                contributions=contributor.contributions,
                orgs=[],
            )

    with ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(_fetch_profile, contributors))
