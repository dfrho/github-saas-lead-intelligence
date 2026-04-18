import json
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Path to registry file: data/registry.json
REGISTRY_PATH = Path(__file__).parent.parent.parent / "data" / "registry.json"


@dataclass
class RegistryEntry:
    """Represents a watched repository in the registry."""
    owner: str
    repo: str
    label: str
    added_at: str  # ISO 8601 timestamp
    last_checked: Optional[str] = None  # ISO 8601 timestamp or None
    last_activity_hash: Optional[str] = None  # Commit SHA or None


def _read_registry() -> list[RegistryEntry]:
    """Read and parse the registry file. Returns empty list if file doesn't exist."""
    if not REGISTRY_PATH.exists():
        return []

    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)

    return [RegistryEntry(**entry) for entry in data]


def _write_registry(entries: list[RegistryEntry]) -> None:
    """Write registry entries to JSON file."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(entry) for entry in entries]
    with open(REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _find_entry(owner: str, repo: str) -> Optional[RegistryEntry]:
    """Find an entry by owner/repo (case-insensitive)."""
    entries = _read_registry()
    for entry in entries:
        if entry.owner.lower() == owner.lower() and entry.repo.lower() == repo.lower():
            return entry
    return None


def add_watched_repo(owner: str, repo: str, label: str) -> tuple[bool, RegistryEntry]:
    """
    Add a repository to the watched registry.

    Returns (created, entry) where created=True if newly added, False if already existed.
    """
    existing = _find_entry(owner, repo)
    if existing:
        return False, existing

    entries = _read_registry()
    entry = RegistryEntry(
        owner=owner,
        repo=repo,
        label=label,
        added_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        last_checked=None,
        last_activity_hash=None,
    )
    entries.append(entry)
    _write_registry(entries)

    return True, entry


def list_watched_repos() -> list[RegistryEntry]:
    """List all watched repositories."""
    return _read_registry()


def update_registry_entry(owner: str, repo: str, **updates) -> None:
    """
    Update an entry in the registry with the given fields.

    Args:
        owner: Repository owner
        repo: Repository name
        **updates: Fields to update (e.g., last_checked, last_activity_hash)
    """
    entries = _read_registry()
    for i, entry in enumerate(entries):
        if entry.owner.lower() == owner.lower() and entry.repo.lower() == repo.lower():
            # Update the entry with new values
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            entries[i] = entry
            _write_registry(entries)
            return
