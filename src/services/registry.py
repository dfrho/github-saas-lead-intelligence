import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Path to registry file: data/registry.json
REGISTRY_PATH = Path(__file__).parent.parent.parent / "data" / "registry.json"

# When USE_DB=true, all reads/writes go to Postgres instead of the JSON file
_USE_DB = os.environ.get("USE_DB", "").lower() == "true"


@dataclass
class RegistryEntry:
    """Represents a watched repository in the registry."""
    owner: str
    repo: str
    label: str
    added_at: str  # ISO 8601 timestamp
    last_checked: Optional[str] = None  # ISO 8601 timestamp or None
    last_activity_hash: Optional[str] = None  # Commit SHA or None


# ── JSON backend (default, MCP-only usage) ───────────────────────────────────

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


# ── Postgres backend (USE_DB=true) ───────────────────────────────────────────

def _get_conn():
    """Open a psycopg3 connection using DATABASE_URL."""
    import psycopg
    return psycopg.connect(os.environ["DATABASE_URL"])


def _row_to_entry(row: tuple) -> RegistryEntry:
    """Convert a DB row (owner, repo, label, added_at, last_checked, last_activity_hash) to RegistryEntry."""
    owner, repo, label, added_at, last_checked, last_activity_hash = row
    return RegistryEntry(
        owner=owner,
        repo=repo,
        label=label,
        added_at=added_at.isoformat().replace("+00:00", "Z") if added_at else "",
        last_checked=last_checked.isoformat().replace("+00:00", "Z") if last_checked else None,
        last_activity_hash=last_activity_hash,
    )


def _db_list(user_id: Optional[str] = None) -> list[RegistryEntry]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT owner, repo, label, added_at, last_checked, last_activity_hash "
                    "FROM watched_repos WHERE user_id = %s ORDER BY added_at",
                    (user_id,),
                )
            else:
                cur.execute(
                    "SELECT owner, repo, label, added_at, last_checked, last_activity_hash "
                    "FROM watched_repos ORDER BY added_at"
                )
            return [_row_to_entry(row) for row in cur.fetchall()]


def _db_add(owner: str, repo: str, label: str, user_id: Optional[str] = None) -> tuple[bool, RegistryEntry]:
    now = datetime.now(timezone.utc)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT owner, repo, label, added_at, last_checked, last_activity_hash "
                "FROM watched_repos "
                "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s) "
                "AND user_id IS NOT DISTINCT FROM %s",
                (owner, repo, user_id),
            )
            existing = cur.fetchone()
            if existing:
                return False, _row_to_entry(existing)

            cur.execute(
                "INSERT INTO watched_repos (user_id, owner, repo, label, added_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, owner, repo, label, now),
            )
        conn.commit()

    entry = RegistryEntry(
        owner=owner,
        repo=repo,
        label=label,
        added_at=now.isoformat().replace("+00:00", "Z"),
    )
    return True, entry


def _db_update(owner: str, repo: str, user_id: Optional[str] = None, **updates) -> None:
    allowed = {"last_checked", "last_activity_hash"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())

    with _get_conn() as conn:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    f"UPDATE watched_repos SET {set_clause} "
                    "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s) AND user_id = %s",
                    (*values, owner, repo, user_id),
                )
            else:
                cur.execute(
                    f"UPDATE watched_repos SET {set_clause} "
                    "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s)",
                    (*values, owner, repo),
                )
        conn.commit()


def _db_remove(owner: str, repo: str, user_id: Optional[str] = None) -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "DELETE FROM watched_repos "
                    "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s) AND user_id = %s",
                    (owner, repo, user_id),
                )
            else:
                cur.execute(
                    "DELETE FROM watched_repos "
                    "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s)",
                    (owner, repo),
                )
            deleted = cur.rowcount
        conn.commit()
    return deleted > 0


# ── Public API ───────────────────────────────────────────────────────────────

def add_watched_repo(owner: str, repo: str, label: str, user_id: Optional[str] = None) -> tuple[bool, RegistryEntry]:
    """
    Add a repository to the watched registry.

    Returns (created, entry) where created=True if newly added, False if already existed.
    user_id is required when USE_DB=true (web backend); ignored in JSON mode (MCP).
    """
    if _USE_DB:
        return _db_add(owner, repo, label, user_id)

    existing = next(
        (e for e in _read_registry()
         if e.owner.lower() == owner.lower() and e.repo.lower() == repo.lower()),
        None,
    )
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


def list_watched_repos(user_id: Optional[str] = None) -> list[RegistryEntry]:
    """List watched repositories. Filters by user_id when USE_DB=true."""
    if _USE_DB:
        return _db_list(user_id)
    return _read_registry()


def update_registry_entry(owner: str, repo: str, user_id: Optional[str] = None, **updates) -> None:
    """
    Update an entry in the registry with the given fields.

    Args:
        owner: Repository owner
        repo: Repository name
        user_id: Required when USE_DB=true
        **updates: Fields to update (e.g., last_checked, last_activity_hash)
    """
    if _USE_DB:
        _db_update(owner, repo, user_id, **updates)
        return

    entries = _read_registry()
    for i, entry in enumerate(entries):
        if entry.owner.lower() == owner.lower() and entry.repo.lower() == repo.lower():
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            entries[i] = entry
            _write_registry(entries)
            return


def remove_watched_repo(owner: str, repo: str, user_id: Optional[str] = None) -> bool:
    """
    Remove a repository from the registry.

    Returns True if the entry was found and deleted, False if not found.
    user_id is required when USE_DB=true.
    """
    if _USE_DB:
        return _db_remove(owner, repo, user_id)

    entries = _read_registry()
    new_entries = [
        e for e in entries
        if not (e.owner.lower() == owner.lower() and e.repo.lower() == repo.lower())
    ]
    if len(new_entries) == len(entries):
        return False
    _write_registry(new_entries)
    return True
