"""Persistence for user-favorited items (issues, PRs, branches, commits, etc.).

Favorites are stored as a JSON file in the user's per-app data directory
(``%APPDATA%\\ghmanage\\favorites.json`` on Windows) so they survive across
sessions. Each entry captures enough metadata to display the favorite in a
mixed list and re-open it in the browser.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FavoriteEntry:
    """A single favorited item from any view, across any repo."""

    repo: str           # e.g. "kellylford/quickmail"
    item_type: str      # "issue", "pr", "branch", "commit", "tag", "release", "workflow"
    url: str            # GitHub URL for opening in browser
    title: str          # primary display label (e.g. "#42 — Fix login bug")
    subtitle: str = ""  # secondary info (e.g. "open", "main", "v0.1.5")
    added_at: str = ""  # ISO timestamp when favorited

    @property
    def key(self) -> str:
        """Unique key for dedup — repo + item_type + url."""
        return f"{self.repo}|{self.item_type}|{self.url}"


def _app_data_dir() -> Path:
    """Return the per-user app data directory for ghmanage, creating it if needed."""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = Path(base) / "ghmanage"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _favorites_file() -> Path:
    return _app_data_dir() / "favorites.json"


def load_favorites() -> list[FavoriteEntry]:
    """Load the list of favorited items. Returns [] if missing/invalid."""
    f = _favorites_file()
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    favorites: list[FavoriteEntry] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        try:
            favorites.append(FavoriteEntry(
                repo=entry.get("repo", ""),
                item_type=entry.get("item_type", ""),
                url=entry.get("url", ""),
                title=entry.get("title", ""),
                subtitle=entry.get("subtitle", ""),
                added_at=entry.get("added_at", ""),
            ))
        except (TypeError, ValueError):
            continue
    return favorites


def save_favorites(favorites: list[FavoriteEntry]) -> None:
    """Persist the list of favorites."""
    f = _favorites_file()
    f.write_text(
        json.dumps([asdict(fav) for fav in favorites], indent=2),
        encoding="utf-8",
    )


def is_favorite(url: str, favorites: list[FavoriteEntry]) -> bool:
    """Check if an item with the given URL is already in favorites."""
    return any(fav.url == url for fav in favorites)


def add_favorite(entry: FavoriteEntry, favorites: list[FavoriteEntry]) -> list[FavoriteEntry]:
    """Add a favorite (dedup by URL). Returns the new list."""
    if not is_favorite(entry.url, favorites):
        favorites.append(entry)
        save_favorites(favorites)
    return favorites


def remove_favorite(url: str, favorites: list[FavoriteEntry]) -> list[FavoriteEntry]:
    """Remove a favorite by URL. Returns the new list."""
    favorites = [fav for fav in favorites if fav.url != url]
    save_favorites(favorites)
    return favorites


def toggle_favorite(entry: FavoriteEntry, favorites: list[FavoriteEntry]) -> tuple[list[FavoriteEntry], bool]:
    """Toggle favorite status. Returns (new_list, was_added)."""
    if is_favorite(entry.url, favorites):
        favorites = remove_favorite(entry.url, favorites)
        return favorites, False
    else:
        favorites = add_favorite(entry, favorites)
        return favorites, True