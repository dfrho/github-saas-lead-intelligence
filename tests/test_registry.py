import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.registry import add_watched_repo, list_watched_repos, update_registry_entry


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr("services.registry.REGISTRY_PATH", registry_path)
    monkeypatch.setattr("services.registry._USE_DB", False)
    return registry_path


def test_add_new_repo():
    created, entry = add_watched_repo("acme", "api", "ACME API")
    assert created is True
    assert entry.owner == "acme"
    assert entry.repo == "api"
    assert entry.label == "ACME API"
    assert entry.last_checked is None
    assert entry.last_activity_hash is None


def test_add_duplicate_repo():
    add_watched_repo("acme", "api", "ACME API")
    created, entry = add_watched_repo("acme", "api", "Different Label")
    assert created is False
    assert entry.label == "ACME API"  # original label preserved


def test_add_duplicate_case_insensitive():
    add_watched_repo("Acme", "Api", "ACME API")
    created, _ = add_watched_repo("acme", "api", "ACME API")
    assert created is False


def test_list_watched_repos_empty():
    assert list_watched_repos() == []


def test_list_watched_repos_returns_all():
    add_watched_repo("org1", "repo1", "Repo 1")
    add_watched_repo("org2", "repo2", "Repo 2")
    entries = list_watched_repos()
    assert len(entries) == 2
    assert {e.repo for e in entries} == {"repo1", "repo2"}


def test_update_registry_entry():
    add_watched_repo("acme", "api", "ACME API")
    update_registry_entry("acme", "api", last_checked="2026-04-18T00:00:00Z", last_activity_hash="abc123")
    entries = list_watched_repos()
    assert entries[0].last_checked == "2026-04-18T00:00:00Z"
    assert entries[0].last_activity_hash == "abc123"


def test_update_nonexistent_entry_is_noop():
    update_registry_entry("ghost", "repo", last_checked="2026-04-18T00:00:00Z")
    assert list_watched_repos() == []
