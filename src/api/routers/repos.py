"""
/repos endpoints — watch, list, and remove repositories for a user.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services import registry
from ..deps import get_current_user

router = APIRouter(prefix="/repos", tags=["repos"])


class WatchRepoRequest(BaseModel):
    owner: str
    repo: str
    label: str | None = None


class RepoResponse(BaseModel):
    owner: str
    repo: str
    label: str
    added_at: str
    last_checked: str | None
    last_activity_hash: str | None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RepoResponse)
def watch_repo(
    body: WatchRepoRequest,
    user_id: str = Depends(get_current_user),
):
    """Add a repository to the user's watched list."""
    resolved_label = body.label or f"{body.owner}/{body.repo}"
    created, entry = registry.add_watched_repo(body.owner, body.repo, resolved_label, user_id=user_id)

    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{body.owner}/{body.repo} is already in your watch list.",
        )

    return RepoResponse(
        owner=entry.owner,
        repo=entry.repo,
        label=entry.label,
        added_at=entry.added_at,
        last_checked=entry.last_checked,
        last_activity_hash=entry.last_activity_hash,
    )


@router.get("", response_model=list[RepoResponse])
def list_repos(user_id: str = Depends(get_current_user)):
    """List all repositories in the user's watch list."""
    entries = registry.list_watched_repos(user_id=user_id)
    return [
        RepoResponse(
            owner=e.owner,
            repo=e.repo,
            label=e.label,
            added_at=e.added_at,
            last_checked=e.last_checked,
            last_activity_hash=e.last_activity_hash,
        )
        for e in entries
    ]


@router.delete("/{owner}/{repo}", status_code=status.HTTP_204_NO_CONTENT)
def remove_repo(
    owner: str,
    repo: str,
    user_id: str = Depends(get_current_user),
):
    """Remove a repository from the user's watch list."""
    deleted = registry.remove_watched_repo(owner, repo, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{owner}/{repo} not found in your watch list.",
        )
