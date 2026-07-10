"""Persistence for user-pinned (added-by-URL) repositories.

Pinned repos are stored as a JSON file in the user's per-app data directory
(`%APPDATA%\\ghmanage\\pinned_repos.json` on Windows) so they survive across
sessions. Each entry is just ``OWNER/NAME``; the description is fetched live
when the repo list is built.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _app_data_dir() -> Path:
    """Return the per-user app data directory for ghmanage, creating it if needed."""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = Path(base) / "ghmanage"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pinned_file() -> Path:
    return _app_data_dir() / "pinned_repos.json"


def load_pinned() -> list[str]:
    """Load the list of pinned repo names (OWNER/NAME). Returns [] if missing/invalid."""
    f = _pinned_file()
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [str(r) for r in data if isinstance(r, str) and r]
    return []


def save_pinned(repos: list[str]) -> None:
    """Persist the list of pinned repo names."""
    f = _pinned_file()
    f.write_text(json.dumps(repos, indent=2), encoding="utf-8")


def add_pinned(repo: str) -> list[str]:
    """Add a repo to the pinned list (dedup, case-insensitive). Returns the new list."""
    repos = load_pinned()
    lower = [r.lower() for r in repos]
    if repo.lower() not in lower:
        repos.append(repo)
        save_pinned(repos)
    return repos


def remove_pinned(repo: str) -> list[str]:
    """Remove a repo from the pinned list (case-insensitive). Returns the new list."""
    repos = [r for r in load_pinned() if r.lower() != repo.lower()]
    save_pinned(repos)
    return repos