"""Data layer for ghviewer — shells out to the `gh` CLI for all operations."""

from __future__ import annotations

import json
import subprocess
import webbrowser
from dataclasses import dataclass, field
from typing import Optional


class GhError(RuntimeError):
    """Raised when a `gh` command fails."""


def _run_gh(args: list[str]) -> str:
    """Run a `gh` command and return stdout, raising GhError on failure."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError:
        raise GhError(
            "The `gh` CLI was not found. Install it from https://cli.github.com/"
        )
    except subprocess.CalledProcessError as exc:
        raise GhError(exc.stderr.strip() or f"`gh {' '.join(args)}` failed")
    return result.stdout


# ── Data model ─────────────────────────────────────────────────────────


@dataclass
class Item:
    """A single issue or pull request with full metadata."""

    number: int
    title: str
    state: str
    url: str
    is_pr: bool
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    comments: int = 0
    comment_list: list[dict] = field(default_factory=list)
    # PR-specific
    is_draft: bool = False
    is_merged: bool = False
    review_status: str = ""
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    base_branch: str = ""
    head_branch: str = ""

    @property
    def kind(self) -> str:
        return "PR" if self.is_pr else "ISSUE"

    @property
    def state_display(self) -> str:
        if self.is_pr and self.is_merged:
            return "MERGED"
        return self.state.upper()

    def to_row(self, columns: list[str]) -> dict[str, str]:
        """Return a dict of column-name -> display value for the given columns."""
        mapping = {
            "number": str(self.number),
            "type": self.kind,
            "state": self.state_display,
            "title": self.title,
            "author": self.author,
            "created": self.created_at[:10] if self.created_at else "",
            "updated": self.updated_at[:10] if self.updated_at else "",
            "labels": ", ".join(self.labels),
            "assignees": ", ".join(self.assignees),
            "comments": str(self.comments),
            "draft": "Yes" if self.is_draft else "No",
            "review": self.review_status,
            "+/-": f"+{self.additions}/-{self.deletions}" if self.is_pr else "",
            "files": str(self.changed_files) if self.is_pr else "",
            "base": self.base_branch if self.is_pr else "",
            "head": self.head_branch if self.is_pr else "",
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        """Return a screen-reader-friendly string with field names included."""
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


# ── Column definitions ─────────────────────────────────────────────────


ALL_COLUMNS = [
    "number", "type", "state", "title", "author", "created", "updated",
    "labels", "assignees", "comments", "draft", "review", "+/-", "files",
    "base", "head",
]

DEFAULT_COLUMNS = ["number", "type", "state", "title"]

SORT_ORDERS = [
    "Number (newest first)",
    "Number (oldest first)",
    "Title (A-Z)",
    "Title (Z-A)",
    "Created (newest first)",
    "Created (oldest first)",
    "Updated (newest first)",
    "Updated (oldest first)",
    "Comments (most first)",
]


def sort_items(items: list[Item], sort_order: str) -> list[Item]:
    """Sort items according to the named sort order."""
    if sort_order.startswith("Number (newest"):
        return sorted(items, key=lambda i: i.number, reverse=True)
    elif sort_order.startswith("Number (oldest"):
        return sorted(items, key=lambda i: i.number)
    elif sort_order.startswith("Title (A-Z"):
        return sorted(items, key=lambda i: i.title.lower())
    elif sort_order.startswith("Title (Z-A"):
        return sorted(items, key=lambda i: i.title.lower(), reverse=True)
    elif sort_order.startswith("Created (newest"):
        return sorted(items, key=lambda i: i.created_at, reverse=True)
    elif sort_order.startswith("Created (oldest"):
        return sorted(items, key=lambda i: i.created_at)
    elif sort_order.startswith("Updated (newest"):
        return sorted(items, key=lambda i: i.updated_at, reverse=True)
    elif sort_order.startswith("Updated (oldest"):
        return sorted(items, key=lambda i: i.updated_at)
    elif sort_order.startswith("Comments"):
        return sorted(items, key=lambda i: i.comments, reverse=True)
    return items


# ── Fetching ───────────────────────────────────────────────────────────


# JSON fields to request from gh for issues
ISSUE_FIELDS = "number,title,state,url,author,createdAt,updatedAt,body,labels,assignees,comments"
PR_FIELDS = "number,title,state,url,author,createdAt,updatedAt,body,labels,assignees,comments,isDraft,mergedAt,reviewDecision,additions,deletions,changedFiles,baseRefName,headRefName"


def _parse_author(row: dict) -> str:
    a = row.get("author")
    if isinstance(a, dict):
        return a.get("login", "unknown")
    return str(a) if a else "unknown"


def _parse_comments(row: dict) -> tuple[int, list[dict]]:
    """Parse the comments field — gh returns a list of comment objects.

    Returns (count, list_of_comment_dicts).
    """
    raw = row.get("comments", [])
    if isinstance(raw, list):
        comments = []
        for c in raw:
            if isinstance(c, dict):
                author = c.get("author", {})
                author_login = author.get("login", "unknown") if isinstance(author, dict) else str(author)
                comments.append({
                    "author": author_login,
                    "body": c.get("body", "") or "",
                    "created_at": c.get("createdAt", ""),
                })
        return len(comments), comments
    if isinstance(raw, int):
        return raw, []
    return 0, []


def _parse_issues(raw: str) -> list[Item]:
    if not raw.strip():
        return []
    rows = json.loads(raw)
    items: list[Item] = []
    for row in rows:
        items.append(
            Item(
                number=row["number"],
                title=row.get("title", ""),
                state=row.get("state", "open"),
                url=row.get("url", ""),
                is_pr=False,
                author=_parse_author(row),
                created_at=row.get("createdAt", ""),
                updated_at=row.get("updatedAt", ""),
                body=row.get("body", "") or "",
                labels=[l["name"] if isinstance(l, dict) else str(l) for l in row.get("labels", [])],
                assignees=[a["login"] if isinstance(a, dict) else str(a) for a in row.get("assignees", [])],
                comments=_parse_comments(row)[0],
                comment_list=_parse_comments(row)[1],
            )
        )
    return items


def _parse_prs(raw: str) -> list[Item]:
    if not raw.strip():
        return []
    rows = json.loads(raw)
    items: list[Item] = []
    for row in rows:
        items.append(
            Item(
                number=row["number"],
                title=row.get("title", ""),
                state=row.get("state", "open"),
                url=row.get("url", ""),
                is_pr=True,
                author=_parse_author(row),
                created_at=row.get("createdAt", ""),
                updated_at=row.get("updatedAt", ""),
                body=row.get("body", "") or "",
                labels=[l["name"] if isinstance(l, dict) else str(l) for l in row.get("labels", [])],
                assignees=[a["login"] if isinstance(a, dict) else str(a) for a in row.get("assignees", [])],
                comments=_parse_comments(row)[0],
                comment_list=_parse_comments(row)[1],
                is_draft=row.get("isDraft", False),
                is_merged=bool(row.get("mergedAt")),
                review_status=row.get("reviewDecision", "") or "",
                additions=row.get("additions", 0),
                deletions=row.get("deletions", 0),
                changed_files=row.get("changedFiles", 0),
                base_branch=row.get("baseRefName", ""),
                head_branch=row.get("headRefName", ""),
            )
        )
    return items


def fetch_issues(repo: Optional[str], state: str = "open") -> list[Item]:
    """Fetch issues (excluding PRs) for the repo."""
    args = ["issue", "list", "--state", state, "--json", ISSUE_FIELDS]
    if repo:
        args += ["--repo", repo]
    return _parse_issues(_run_gh(args))


def fetch_prs(repo: Optional[str], state: str = "open") -> list[Item]:
    """Fetch pull requests for the repo."""
    args = ["pr", "list", "--state", state, "--json", PR_FIELDS]
    if repo:
        args += ["--repo", repo]
    return _parse_prs(_run_gh(args))


def fetch_item_detail(item: Item, repo: Optional[str]) -> Item:
    """Re-fetch a single item with full detail (body, comments count, etc.)."""
    sub = "pr" if item.is_pr else "issue"
    fields = PR_FIELDS if item.is_pr else ISSUE_FIELDS
    args = [sub, "view", str(item.number), "--json", fields]
    if repo:
        args += ["--repo", repo]
    raw = _run_gh(args)
    if not raw.strip():
        return item
    row = json.loads(raw)
    if item.is_pr:
        updated = _parse_prs(raw)
        return updated[0] if updated else item
    else:
        updated = _parse_issues(raw)
        return updated[0] if updated else item


# ── Actions ────────────────────────────────────────────────────────────


def close_item(item: Item, repo: Optional[str]) -> None:
    """Close the given issue or PR via `gh`."""
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "close", str(item.number)]
    if repo:
        args += ["--repo", repo]
    _run_gh(args)


def reopen_item(item: Item, repo: Optional[str]) -> None:
    """Reopen the given issue or PR via `gh`."""
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "reopen", str(item.number)]
    if repo:
        args += ["--repo", repo]
    _run_gh(args)


def add_comment(item: Item, comment: str, repo: Optional[str]) -> None:
    """Add a comment to an issue or PR."""
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "comment", str(item.number), "--body", comment]
    if repo:
        args += ["--repo", repo]
    _run_gh(args)


def open_in_browser(item: Item) -> None:
    """Open the item's GitHub URL in the default browser."""
    if item.url:
        webbrowser.open(item.url)


# ── Repo helpers ───────────────────────────────────────────────────────


def detect_repo() -> Optional[str]:
    """Try to detect the owner/name of the current git repo via `gh`."""
    try:
        out = _run_gh(["repo", "view", "--json", "nameWithOwner"])
    except GhError:
        return None
    try:
        return json.loads(out).get("nameWithOwner")
    except json.JSONDecodeError:
        return None


def list_repos(limit: int = 100) -> list[dict]:
    """List the user's GitHub repositories via `gh repo list`."""
    args = [
        "repo", "list", "--limit", str(limit),
        "--json", "nameWithOwner,description,isArchived",
    ]
    raw = _run_gh(args)
    if not raw.strip():
        return []
    return json.loads(raw)