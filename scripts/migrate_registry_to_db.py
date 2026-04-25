"""
One-time migration: reads data/registry.json and inserts entries into the
watched_repos Postgres table.

Usage:
    python scripts/migrate_registry_to_db.py [--user-id UUID]

If --user-id is provided, all migrated repos are assigned to that user.
Without it, entries are inserted with user_id = NULL (MCP-only mode, no
web auth association).

Environment:
    DATABASE_URL must be set (or load your .env before running).

Example:
    export $(cat .env | xargs) && python scripts/migrate_registry_to_db.py
    python scripts/migrate_registry_to_db.py --user-id 123e4567-e89b-12d3-a456-426614174000
"""

import argparse
import json
import os
import sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "registry.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate data/registry.json to Postgres watched_repos table")
    parser.add_argument("--user-id", metavar="UUID", help="Assign all repos to this user UUID", default=None)
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print("No data/registry.json found — nothing to migrate.")
        return

    with open(REGISTRY_PATH) as f:
        entries = json.load(f)

    if not entries:
        print("data/registry.json is empty — nothing to migrate.")
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set.")
        print("Run: export $(grep -v '^#' .env | xargs) && python scripts/migrate_registry_to_db.py")
        sys.exit(1)

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Run: pip install 'psycopg[binary]>=3.1.0'")
        sys.exit(1)

    print(f"Migrating {len(entries)} entries from registry.json to Postgres...")
    if args.user_id:
        print(f"Assigning all repos to user_id: {args.user_id}\n")
    else:
        print("No --user-id provided; inserting with user_id = NULL\n")

    inserted = 0
    skipped = 0
    errors = 0

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for entry in entries:
                owner = entry["owner"]
                repo = entry["repo"]
                try:
                    # Check for existing row first (handles NULL user_id safely)
                    cur.execute(
                        "SELECT id FROM watched_repos "
                        "WHERE lower(owner) = lower(%s) AND lower(repo) = lower(%s) "
                        "AND user_id IS NOT DISTINCT FROM %s",
                        (owner, repo, args.user_id),
                    )
                    if cur.fetchone():
                        print(f"  - {owner}/{repo} (already exists, skipped)")
                        skipped += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO watched_repos
                            (user_id, owner, repo, label, added_at, last_checked, last_activity_hash)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            args.user_id,
                            owner,
                            repo,
                            entry.get("label", f"{owner}/{repo}"),
                            entry.get("added_at"),
                            entry.get("last_checked"),
                            entry.get("last_activity_hash"),
                        ),
                    )
                    print(f"  + {owner}/{repo}")
                    inserted += 1
                except Exception as e:
                    print(f"  x {owner}/{repo}: {e}")
                    errors += 1

        conn.commit()

    print(f"\nDone. {inserted} inserted, {skipped} skipped, {errors} errors.")


if __name__ == "__main__":
    main()
