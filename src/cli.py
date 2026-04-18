#!/usr/bin/env python3
"""
CLI interface for managing the GitHub Lead Intelligence registry.

Usage:
    python src/cli.py add <owner> <repo> [label]     Add a repo to watch
    python src/cli.py list                            List all watched repos
    python src/cli.py remove <owner> <repo>           Remove a repo from watch list
"""

import argparse
import sys
from services import registry


def add_repo(owner: str, repo: str, label: str = None):
    """Add a repository to the registry."""
    resolved_label = label or f"{owner}/{repo}"
    created, entry = registry.add_watched_repo(owner, repo, resolved_label)

    if created:
        print(f"✓ Added {owner}/{repo}")
        print(f"  Label: {resolved_label}")
        print(f"  Added at: {entry.added_at}")
    else:
        print(f"ℹ {owner}/{repo} is already being watched")
        print(f"  Label: {entry.label}")
        print(f"  Added at: {entry.added_at}")


def list_repos():
    """List all repositories in the registry."""
    entries = registry.list_watched_repos()

    if not entries:
        print("No repositories are currently being watched.")
        return

    print(f"Watched repositories ({len(entries)} total):\n")
    for entry in entries:
        status = "never checked" if not entry.last_checked else f"checked {entry.last_checked}"
        print(f"  • {entry.owner}/{entry.repo}")
        print(f"    Label: {entry.label}")
        print(f"    Status: {status}")
        if entry.last_activity_hash:
            print(f"    Latest SHA: {entry.last_activity_hash[:12]}")
        print()


def remove_repo(owner: str, repo: str):
    """Remove a repository from the registry."""
    entries = registry.list_watched_repos()
    original_count = len(entries)

    # Filter out the repo to remove
    updated_entries = [
        e
        for e in entries
        if not (e.owner.lower() == owner.lower() and e.repo.lower() == repo.lower())
    ]

    if len(updated_entries) == original_count:
        print(f"✗ {owner}/{repo} not found in registry")
        sys.exit(1)

    registry._write_registry(updated_entries)
    print(f"✓ Removed {owner}/{repo} from watch list")


def main():
    parser = argparse.ArgumentParser(
        description="Manage GitHub Lead Intelligence registry",
        prog="python src/cli.py",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a repository to watch")
    add_parser.add_argument("owner", help="GitHub organization or user")
    add_parser.add_argument("repo", help="Repository name")
    add_parser.add_argument(
        "label", nargs="?", help='Human-readable label (defaults to "owner/repo")'
    )

    # List command
    subparsers.add_parser("list", help="List all watched repositories")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a repository from watch list")
    remove_parser.add_argument("owner", help="GitHub organization or user")
    remove_parser.add_argument("repo", help="Repository name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "add":
        add_repo(args.owner, args.repo, args.label)
    elif args.command == "list":
        list_repos()
    elif args.command == "remove":
        remove_repo(args.owner, args.repo)


if __name__ == "__main__":
    main()
