"""Persistence for saved GitHub searches.

Each is a name, a kind (issues and pull requests, or repositories) and the
query exactly as typed. Stored as JSON beside the favorites
(``%APPDATA%\\ghmanage\\saved_searches.json`` on Windows) and listed in the
repository list, where Enter runs one.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from favorites import _app_data_dir

KIND_ISSUES = "issues"
KIND_REPOS = "repos"


@dataclass
class SavedSearch:
    name: str
    query: str
    kind: str = KIND_ISSUES


def _file() -> Path:
    return _app_data_dir() / "saved_searches.json"


def load_saved_searches() -> list[SavedSearch]:
    """Saved searches in the order they were saved. [] if missing or unreadable."""
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out: list[SavedSearch] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name, query = entry.get("name"), entry.get("query")
        kind = entry.get("kind", KIND_ISSUES)
        if isinstance(name, str) and name and isinstance(query, str) and query:
            out.append(SavedSearch(name, query, kind if kind in (KIND_ISSUES, KIND_REPOS) else KIND_ISSUES))
    return out


def save_saved_searches(searches: list[SavedSearch]) -> None:
    _file().write_text(json.dumps([asdict(s) for s in searches], indent=2), encoding="utf-8")


def add_saved_search(search: SavedSearch) -> list[SavedSearch]:
    """Add ``search``, replacing one of the same name (not case-sensitive)."""
    searches = [s for s in load_saved_searches() if s.name.lower() != search.name.lower()]
    searches.append(search)
    save_saved_searches(searches)
    return searches


def remove_saved_search(name: str) -> list[SavedSearch]:
    searches = [s for s in load_saved_searches() if s.name != name]
    save_saved_searches(searches)
    return searches
