"""Data layer for ghviewer — shells out to the `gh` CLI for all operations."""

from __future__ import annotations

import json
import subprocess
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional


class GhError(RuntimeError):
    """Raised when a `gh` command fails."""


def _run_gh(args: list[str]) -> str:
    """Run a `gh` command and return stdout, raising GhError on failure."""
    # On Windows, suppress the console window that subprocess would otherwise pop up.
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            creationflags=creationflags,
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


def fetch_issues(
    repo: Optional[str], state: str = "open", limit: int = 30, label: str = ""
) -> list[Item]:
    """Fetch issues (excluding PRs) for the repo.

    ``gh issue list`` defaults to only 30 items and returns newest first.
    Pass ``limit`` to control how many are fetched.

    ``label`` restricts the list to issues carrying that label — this is what
    the Labels view drills into. Filtering server-side rather than in the app
    matters: an unfiltered page of 100 may not contain a single issue with the
    label you picked.

    If ``repo`` is a fork, issues are fetched from its upstream parent,
    since forks have issues disabled on GitHub.
    """
    effective = resolve_issue_repo(repo)
    args = ["issue", "list", "--state", state, "--limit", str(limit), "--json", ISSUE_FIELDS]
    if label:
        args += ["--label", label]
    if effective:
        args += ["--repo", effective]
    return _parse_issues(_run_gh(args))


def fetch_prs(
    repo: Optional[str], state: str = "open", limit: int = 30, label: str = ""
) -> list[Item]:
    """Fetch pull requests for the repo.

    ``gh pr list`` defaults to only 30 items and returns newest first.
    Pass ``limit`` to control how many are fetched. ``label`` restricts the
    list to PRs carrying that label.

    If ``repo`` is a fork, PRs are fetched from its upstream parent so that
    PRs opened against the upstream repo are visible. Fork-local PRs are not
    shown in this case.
    """
    effective = resolve_issue_repo(repo)
    args = ["pr", "list", "--state", state, "--limit", str(limit), "--json", PR_FIELDS]
    if label:
        args += ["--label", label]
    if effective:
        args += ["--repo", effective]
    return _parse_prs(_run_gh(args))


def fetch_item_detail(item: Item, repo: Optional[str]) -> Item:
    """Re-fetch a single item with full detail (body, comments count, etc.)."""
    effective = resolve_issue_repo(repo)
    sub = "pr" if item.is_pr else "issue"
    fields = PR_FIELDS if item.is_pr else ISSUE_FIELDS
    args = [sub, "view", str(item.number), "--json", fields]
    if effective:
        args += ["--repo", effective]
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


def fetch_item_by_number(number: int, repo: Optional[str]) -> Optional[Item]:
    """Fetch a single issue or PR by number, regardless of state.

    Tries ``gh issue view`` first; if that fails (e.g. the number is a PR,
    not an issue), falls back to ``gh pr view``. Returns ``None`` if the
    number doesn't exist as either an issue or a PR.
    """
    effective = resolve_issue_repo(repo)
    for sub, fields, parser in (
        ("issue", ISSUE_FIELDS, _parse_issues),
        ("pr", PR_FIELDS, _parse_prs),
    ):
        args = [sub, "view", str(number), "--json", fields]
        if effective:
            args += ["--repo", effective]
        try:
            raw = _run_gh(args)
        except GhError:
            continue
        if not raw.strip():
            continue
        items = parser(raw)
        if items:
            return items[0]
    return None


# ── Labels ─────────────────────────────────────────────────────────────
#
# Labels belong to whichever repo owns the issues, so every function here
# resolves through ``resolve_issue_repo``: on a fork you browse the upstream
# issues, and a label list from the fork itself would not match them.


@dataclass
class Label:
    """An issue/PR label."""
    name: str
    color: str = ""
    description: str = ""
    url: str = ""
    is_default: bool = False

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "label": self.name,
            "description": self.description,
            "color": f"#{self.color}" if self.color else "",
            "default": "Yes" if self.is_default else "No",
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


LABEL_COLUMNS = ["label", "description", "color", "default"]
LABEL_DEFAULT_COLUMNS = ["label", "description", "color"]

LABEL_FIELDS = "name,color,description,url,isDefault"


def _parse_labels(raw: str) -> list[Label]:
    if not raw.strip():
        return []
    rows = json.loads(raw)
    if not isinstance(rows, list):
        return []
    return [
        Label(
            name=row.get("name", ""),
            color=(row.get("color") or "").lstrip("#"),
            description=row.get("description") or "",
            url=row.get("url", ""),
            is_default=bool(row.get("isDefault")),
        )
        for row in rows
    ]


def fetch_labels(repo: Optional[str], limit: int = 100) -> list[Label]:
    """Fetch the repo's labels, sorted by name.

    Name order is the useful one here — a label list is something you scan for
    a name, not a feed. (``gh`` sorts by creation date by default.)
    """
    effective = resolve_issue_repo(repo)
    args = ["label", "list", "--limit", str(limit), "--sort", "name",
            "--json", LABEL_FIELDS]
    if effective:
        args += ["--repo", effective]
    try:
        return _parse_labels(_run_gh(args))
    except GhError as exc:
        # A repo with no labels at all is not an error worth surfacing —
        # `gh` exits non-zero for it, so translate that into an empty list.
        if "no labels found" in str(exc).lower():
            return []
        raise


def create_label(
    repo: Optional[str], name: str, color: str = "", description: str = ""
) -> None:
    """Create a label. An empty ``color`` lets GitHub pick one."""
    effective = resolve_issue_repo(repo)
    args = ["label", "create", name]
    if color:
        args += ["--color", color.lstrip("#")]
    if description:
        args += ["--description", description]
    if effective:
        args += ["--repo", effective]
    _run_gh(args)


def delete_label(repo: Optional[str], name: str) -> None:
    """Delete a label. ``--yes`` because the caller has already confirmed.

    Deleting a label removes it from every issue and PR that carries it, and
    GitHub offers no undo — confirm in the UI before calling this.
    """
    effective = resolve_issue_repo(repo)
    args = ["label", "delete", name, "--yes"]
    if effective:
        args += ["--repo", effective]
    _run_gh(args)


# ── Actions ────────────────────────────────────────────────────────────


def close_item(item: Item, repo: Optional[str]) -> None:
    """Close the given issue or PR via `gh`."""
    effective = resolve_issue_repo(repo)
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "close", str(item.number)]
    if effective:
        args += ["--repo", effective]
    _run_gh(args)


def reopen_item(item: Item, repo: Optional[str]) -> None:
    """Reopen the given issue or PR via `gh`."""
    effective = resolve_issue_repo(repo)
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "reopen", str(item.number)]
    if effective:
        args += ["--repo", effective]
    _run_gh(args)


def add_comment(item: Item, comment: str, repo: Optional[str]) -> None:
    """Add a comment to an issue or PR."""
    effective = resolve_issue_repo(repo)
    sub = "pr" if item.is_pr else "issue"
    args = [sub, "comment", str(item.number), "--body", comment]
    if effective:
        args += ["--repo", effective]
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
    """List the user's GitHub repositories via `gh repo list`.

    Includes ``isFork`` and ``parent`` so callers can detect forks and
    resolve the upstream repo that actually hosts issues/PRs.
    """
    args = [
        "repo", "list", "--limit", str(limit),
        "--json", "nameWithOwner,description,isArchived,isFork,parent",
    ]
    raw = _run_gh(args)
    if not raw.strip():
        return []
    return json.loads(raw)


def parent_repo(repo: Optional[str]) -> Optional[str]:
    """Return the ``OWNER/NAME`` of ``repo``'s upstream parent, or None.

    Forks on GitHub have issues disabled by default; the issues live on the
    parent (upstream) repo. Callers that fetch issues/PRs should use this to
    resolve the effective repo before calling ``gh issue list`` / ``gh pr list``.
    """
    if not repo:
        return None
    try:
        out = _run_gh(["repo", "view", repo, "--json", "isFork,parent"])
    except GhError:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not data.get("isFork"):
        return None
    parent = data.get("parent")
    if isinstance(parent, dict):
        owner = parent.get("owner", {})
        owner_login = owner.get("login") if isinstance(owner, dict) else None
        name = parent.get("name")
        if owner_login and name:
            return f"{owner_login}/{name}"
    return None


def resolve_issue_repo(repo: Optional[str]) -> Optional[str]:
    """Return the repo to query for issues/PRs.

    For a fork, this is the upstream parent (forks have issues disabled).
    For a non-fork or when the parent can't be determined, returns ``repo``
    unchanged.
    """
    parent = parent_repo(repo)
    return parent if parent else repo


# ── Git metadata: branches, commits, tags, releases, workflow runs ────
#
# These use `gh api` (GitHub REST API) because `gh` doesn't have first-class
# commands for browsing branches/commits/tags.  All functions accept an
# optional ``repo`` (``OWNER/NAME``); when None, the API uses the current
# git repo context.


def _api(args: list[str], repo: Optional[str]) -> str:
    """Run ``gh api`` with the given endpoint args.

    ``gh api`` doesn't support ``--repo``. Instead, we substitute the
    owner/repo into the endpoint path directly when ``repo`` is provided.
    When ``repo`` is None, ``gh api`` uses the current git repo context
    and expands ``{owner}/{repo}`` placeholders automatically.
    """
    full_args = ["api"]
    if repo:
        # Replace {owner}/{repo} in the endpoint with the actual repo path
        owner_name = repo.replace("/", "/")
        substituted = []
        for arg in args:
            substituted.append(arg.replace("{owner}/{repo}", owner_name))
        full_args += substituted
    else:
        full_args += args
    return _run_gh(full_args)


def _api_json(args: list[str], repo: Optional[str]) -> list | dict:
    """Run ``gh api`` and parse JSON (list or dict)."""
    raw = _api(args, repo)
    if not raw.strip():
        return []
    return json.loads(raw)


@dataclass
class Branch:
    """A git branch with its latest commit info."""
    name: str
    commit_sha: str
    commit_message: str
    commit_author: str
    commit_date: str
    protected: bool = False
    ahead: int = 0       # ahead of default branch (only set when comparing)
    behind: int = 0      # behind default branch
    url: str = ""

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "branch": self.name,
            "last commit": self.commit_message[:60],
            "author": self.commit_author,
            "date": self.commit_date[:10] if self.commit_date else "",
            "protected": "Yes" if self.protected else "No",
            "ahead": str(self.ahead) if self.ahead else "",
            "behind": str(self.behind) if self.behind else "",
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


BRANCH_COLUMNS = ["branch", "last commit", "author", "date", "protected", "ahead", "behind"]
BRANCH_DEFAULT_COLUMNS = ["branch", "last commit", "author", "date"]


def fetch_branches(repo: Optional[str], limit: int = 100) -> list[Branch]:
    """Fetch branches for the repo via GitHub REST API."""
    rows = _api_json(
        ["repos/{owner}/{repo}/branches", "--paginate", "-q",
         f"[.[] | {{name, sha: .commit.sha, protected}}] | .[0:{limit}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    # Fetch each branch tip's commit details concurrently. Doing this serially
    # is an N+1 that makes the Branches view slow on repos with many branches;
    # a small thread pool keeps it responsive without hammering the API.
    shas = [row.get("sha", "") for row in rows]
    infos: list[dict] = [{}] * len(rows)
    to_fetch = [(i, sha) for i, sha in enumerate(shas) if sha]
    if to_fetch:
        with ThreadPoolExecutor(max_workers=min(8, len(to_fetch))) as pool:
            futures = {pool.submit(_fetch_commit_info, repo, sha): i
                       for i, sha in to_fetch}
            for fut in as_completed(futures):
                infos[futures[fut]] = fut.result()
    branches: list[Branch] = []
    for row, sha, commit_info in zip(rows, shas, infos):
        branches.append(Branch(
            name=row.get("name", ""),
            commit_sha=sha[:8] if sha else "",
            commit_message=commit_info.get("message", ""),
            commit_author=commit_info.get("author", ""),
            commit_date=commit_info.get("date", ""),
            protected=row.get("protected", False),
            url=f"https://github.com/{repo}/tree/{row.get('name', '')}" if repo else "",
        ))
    return branches


def _fetch_commit_info(repo: Optional[str], sha: str) -> dict:
    """Fetch commit message, author, date for a single SHA."""
    try:
        row = _api_json(
            [f"repos/{{owner}}/{{repo}}/commits/{sha}",
             "-q", "{message: .commit.message, author: .commit.author.name, date: .commit.author.date}"],
            repo,
        )
        if isinstance(row, dict):
            return row
    except GhError:
        pass
    return {}


@dataclass
class Commit:
    """A git commit."""
    sha: str
    short_sha: str
    message: str
    author: str
    date: str
    url: str = ""
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    files: list[dict] = field(default_factory=list)

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "sha": self.short_sha,
            "message": self.message[:80],
            "author": self.author,
            "date": self.date[:10] if self.date else "",
            "files": str(self.files_changed) if self.files_changed else "",
            "+/-": f"+{self.additions}/-{self.deletions}" if self.additions or self.deletions else "",
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


COMMIT_COLUMNS = ["sha", "message", "author", "date", "files", "+/-"]
COMMIT_DEFAULT_COLUMNS = ["sha", "message", "author", "date"]


def fetch_commits(repo: Optional[str], branch: str = "", limit: int = 100) -> list[Commit]:
    """Fetch commits for the repo (optionally for a specific branch)."""
    endpoint = "repos/{owner}/{repo}/commits"
    if branch:
        endpoint += f"?sha={branch}"
    endpoint += f"&per_page={limit}" if branch else f"?per_page={limit}"
    rows = _api_json([endpoint, "-q",
                      f"[.[] | {{sha, message: .commit.message, author: .commit.author.name, date: .commit.author.date, url: .html_url}}]"],
                     repo)
    if not isinstance(rows, list):
        return []
    commits: list[Commit] = []
    for row in rows:
        sha = row.get("sha", "")
        msg = row.get("message", "")
        first_line = msg.split("\n")[0] if msg else ""
        commits.append(Commit(
            sha=sha,
            short_sha=sha[:8] if sha else "",
            message=first_line,
            author=row.get("author", ""),
            date=row.get("date", ""),
            url=row.get("url", ""),
        ))
    return commits


def fetch_commit_detail(repo: Optional[str], sha: str) -> Commit:
    """Fetch full commit detail including file changes."""
    row = _api_json(
        [f"repos/{{owner}}/{{repo}}/commits/{sha}",
         "-q", "{sha, message: .commit.message, author: .commit.author.name, date: .commit.author.date, url: .html_url, additions: .stats.additions, deletions: .stats.deletions, files: [.files[] | {filename, status, additions, deletions}]}"],
        repo,
    )
    if not isinstance(row, dict):
        return Commit(sha=sha, short_sha=sha[:8], message="", author="", date="")
    msg = row.get("message", "")
    return Commit(
        sha=row.get("sha", sha),
        short_sha=row.get("sha", sha)[:8],
        message=msg,
        author=row.get("author", ""),
        date=row.get("date", ""),
        url=row.get("url", ""),
        additions=row.get("additions", 0),
        deletions=row.get("deletions", 0),
        files_changed=len(row.get("files", [])),
        files=row.get("files", []),
    )


@dataclass
class Tag:
    """A git tag."""
    name: str
    commit_sha: str
    url: str = ""

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "tag": self.name,
            "commit": self.commit_sha,
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


TAG_COLUMNS = ["tag", "commit"]
TAG_DEFAULT_COLUMNS = ["tag", "commit"]


def fetch_tags(repo: Optional[str], limit: int = 100) -> list[Tag]:
    """Fetch tags for the repo."""
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/tags?per_page={limit}",
         "-q", "[.[] | {name, sha: .commit.sha}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    tags: list[Tag] = []
    for row in rows:
        sha = row.get("sha", "")
        tags.append(Tag(
            name=row.get("name", ""),
            commit_sha=sha[:8] if sha else "",
            url=f"https://github.com/{repo}/releases/tag/{row.get('name', '')}" if repo else "",
        ))
    return tags


def _size_human(size_bytes: int) -> str:
    """Format a byte count as B/KB/MB/GB."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


@dataclass
class ReleaseAsset:
    """A file attached to a release, with its download count.

    ``download_count`` is a lifetime running total kept by GitHub — it is not
    broken down by date, and there is no API that does so. To see downloads
    over time you have to snapshot these numbers yourself and diff them.
    """
    id: int
    name: str
    size_bytes: int
    download_count: int
    updated_at: str
    url: str = ""          # browser_download_url
    release_tag: str = ""

    def size_human(self) -> str:
        return _size_human(self.size_bytes)

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "name": self.name,
            "downloads": str(self.download_count),
            "size": self.size_human(),
            "date": self.updated_at[:10] if self.updated_at else "",
            "#": str(self.id),
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


ASSET_COLUMNS = ["name", "downloads", "size", "date", "#"]
ASSET_DEFAULT_COLUMNS = ["name", "downloads", "size", "date"]


@dataclass
class Release:
    """A GitHub release."""
    tag: str
    name: str
    draft: bool
    prerelease: bool
    created_at: str
    url: str = ""
    body: str = ""
    id: int = 0
    assets: list[ReleaseAsset] = field(default_factory=list)

    @property
    def downloads(self) -> int:
        """Total downloads across every asset attached to this release."""
        return sum(a.download_count for a in self.assets)

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "tag": self.tag,
            "name": self.name,
            "draft": "Yes" if self.draft else "No",
            "prerelease": "Yes" if self.prerelease else "No",
            "date": self.created_at[:10] if self.created_at else "",
            "downloads": str(self.downloads),
            "assets": str(len(self.assets)),
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


RELEASE_COLUMNS = ["tag", "name", "date", "downloads", "assets", "draft", "prerelease"]
RELEASE_DEFAULT_COLUMNS = ["tag", "name", "date", "downloads"]


def _parse_assets(rows: object, release_tag: str = "") -> list[ReleaseAsset]:
    """Build ReleaseAsset objects from the API's asset array."""
    if not isinstance(rows, list):
        return []
    assets: list[ReleaseAsset] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        assets.append(ReleaseAsset(
            id=row.get("id", 0),
            name=row.get("name", ""),
            size_bytes=row.get("size", 0) or 0,
            download_count=row.get("downloads", 0) or 0,
            updated_at=row.get("updated", "") or "",
            url=row.get("url", "") or "",
            release_tag=release_tag,
        ))
    return assets


# Shape of a single asset, shared by the releases list and the per-release fetch.
_ASSET_FIELDS = (
    "{id, name, size, downloads: .download_count, "
    "updated: .updated_at, url: .browser_download_url}"
)


def fetch_releases(repo: Optional[str], limit: int = 30) -> list[Release]:
    """Fetch releases for the repo, including each one's assets.

    Assets come back inline on the releases endpoint, so the download counts
    cost no extra API call.
    """
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/releases?per_page={limit}",
         "-q", "[.[] | {tag: .tag_name, name, draft, prerelease, created: .created_at, "
               f"url: .html_url, body: .body, id, assets: [.assets[] | {_ASSET_FIELDS}]}}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    releases: list[Release] = []
    for row in rows:
        tag = row.get("tag", "")
        releases.append(Release(
            tag=tag,
            name=row.get("name", ""),
            draft=row.get("draft", False),
            prerelease=row.get("prerelease", False),
            created_at=row.get("created", ""),
            url=row.get("url", ""),
            body=row.get("body", "") or "",
            id=row.get("id", 0),
            assets=_parse_assets(row.get("assets"), tag),
        ))
    return releases


def fetch_release_assets(
    repo: Optional[str], release_id: int, release_tag: str = "", limit: int = 100
) -> list[ReleaseAsset]:
    """Fetch the assets of a single release, newest download counts included."""
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/releases/{release_id}/assets?per_page={limit}",
         "-q", f"[.[] | {_ASSET_FIELDS}]"],
        repo,
    )
    # Most-downloaded first: the count is the reason for opening this view, so the
    # answer should be the row you land on rather than something to hunt for.
    return sorted(_parse_assets(rows, release_tag),
                  key=lambda a: a.download_count, reverse=True)


def total_downloads(releases: list[Release]) -> int:
    """Total downloads across every asset of every release given."""
    return sum(r.downloads for r in releases)


@dataclass
class WorkflowRun:
    """A GitHub Actions workflow run."""
    name: str
    status: str       # queued, in_progress, completed
    conclusion: str   # success, failure, cancelled, None (if still running)
    branch: str
    event: str        # push, pull_request, workflow_dispatch
    created_at: str
    url: str = ""
    run_number: int = 0
    run_id: int = 0     # database id, used for the artifacts API

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "name": self.name,
            "status": self.status,
            "result": self.conclusion or "(running)",
            "branch": self.branch,
            "event": self.event,
            "date": self.created_at[:10] if self.created_at else "",
            "#": str(self.run_number),
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


WORKFLOW_COLUMNS = ["name", "status", "result", "branch", "event", "date", "#"]
WORKFLOW_DEFAULT_COLUMNS = ["name", "status", "result", "branch", "date"]


def fetch_workflow_runs(repo: Optional[str], limit: int = 30) -> list[WorkflowRun]:
    """Fetch recent workflow runs for the repo."""
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/actions/runs?per_page={limit}",
         "-q", "[.workflow_runs[] | {name, status, conclusion, branch: .head_branch, event, created: .created_at, url: .html_url, number: .run_number, id}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    runs: list[WorkflowRun] = []
    for row in rows:
        runs.append(WorkflowRun(
            name=row.get("name", ""),
            status=row.get("status", ""),
            conclusion=row.get("conclusion") or "",
            branch=row.get("branch", ""),
            event=row.get("event", ""),
            created_at=row.get("created", ""),
            url=row.get("url", ""),
            run_number=row.get("number", 0),
            run_id=row.get("id", 0),
        ))
    return runs


@dataclass
class Artifact:
    """A build artifact attached to a workflow run."""
    id: int
    name: str
    size_bytes: int
    expired: bool
    created_at: str
    run_id: int = 0

    def size_human(self) -> str:
        return _size_human(self.size_bytes)

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "name": self.name,
            "size": self.size_human(),
            "expired": "Yes" if self.expired else "No",
            "date": self.created_at[:10] if self.created_at else "",
            "#": str(self.id),
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


ARTIFACT_COLUMNS = ["name", "size", "expired", "date", "#"]
ARTIFACT_DEFAULT_COLUMNS = ["name", "size", "expired", "date"]


def fetch_run_artifacts(repo: Optional[str], run_id: int, limit: int = 100) -> list[Artifact]:
    """Fetch the artifacts produced by a single workflow run."""
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/artifacts?per_page={limit}",
         "-q", "[.artifacts[] | {id, name, size: .size_in_bytes, expired, created: .created_at}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    artifacts: list[Artifact] = []
    for row in rows:
        artifacts.append(Artifact(
            id=row.get("id", 0),
            name=row.get("name", ""),
            size_bytes=row.get("size", 0),
            expired=row.get("expired", False),
            created_at=row.get("created", ""),
            run_id=run_id,
        ))
    return artifacts


def download_artifact(repo: Optional[str], run_id: int, name: str, dest_dir: str) -> None:
    """Download a run's artifact by name, extracting its contents into ``dest_dir``.

    Uses ``gh run download`` which fetches the artifact zip and unpacks it.
    Raises GhError if the artifact is missing or expired.
    """
    args = ["run", "download", str(run_id), "-n", name, "-D", dest_dir]
    if repo:
        args += ["-R", repo]
    _run_gh(args)


def delete_workflow_run(repo: Optional[str], run_id: int) -> None:
    """Delete a workflow run by its database id.

    Uses ``gh run delete``. Raises GhError on failure.
    """
    args = ["run", "delete", str(run_id)]
    if repo:
        args += ["-R", repo]
    _run_gh(args)


@dataclass
class Workflow:
    """A GitHub Actions workflow definition (a .github/workflows/*.yml file)."""
    id: int
    name: str
    path: str
    state: str        # active, disabled_manually, disabled_inactivity
    url: str = ""     # html_url of the workflow

    def to_row(self, columns: list[str]) -> dict[str, str]:
        mapping = {
            "name": self.name,
            "state": self.state,
            "path": self.path,
            "#": str(self.id),
        }
        return {col: mapping.get(col, "") for col in columns}

    def to_accessible_string(self, columns: list[str]) -> str:
        row = self.to_row(columns)
        parts = [f"{col}: {val}" for col, val in row.items() if val]
        return ", ".join(parts)


WORKFLOW_DEF_COLUMNS = ["name", "state", "path", "#"]
WORKFLOW_DEF_DEFAULT_COLUMNS = ["name", "state", "path"]


def fetch_workflows(repo: Optional[str], limit: int = 100) -> list[Workflow]:
    """Fetch the workflow definitions (files) configured for the repo."""
    rows = _api_json(
        [f"repos/{{owner}}/{{repo}}/actions/workflows?per_page={limit}",
         "-q", "[.workflows[] | {id, name, path, state, url: .html_url}]"],
        repo,
    )
    if not isinstance(rows, list):
        return []
    workflows: list[Workflow] = []
    for row in rows:
        workflows.append(Workflow(
            id=row.get("id", 0),
            name=row.get("name", ""),
            path=row.get("path", ""),
            state=row.get("state", ""),
            url=row.get("url", ""),
        ))
    return workflows


@dataclass
class WorkflowInput:
    """One ``workflow_dispatch`` input declared by a workflow file.

    Mirrors what GitHub's own "Run workflow" form is built from. ``type`` is one
    of choice, boolean, string, number, environment; anything unrecognised (or
    omitted, which GitHub treats as string) is presented as a text field.
    """
    name: str
    type: str = "string"
    description: str = ""
    default: str = ""
    required: bool = False
    options: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Text to label the control with. The description when there is one —
        that is what GitHub shows — otherwise the raw input name."""
        return self.description.strip() or self.name


@dataclass
class DispatchSpec:
    """What a workflow file at a given ref says about running it manually."""
    supports_dispatch: bool
    inputs: list[WorkflowInput] = field(default_factory=list)


def _parse_dispatch_spec(raw: str) -> DispatchSpec:
    """Parse ``on.workflow_dispatch`` out of workflow YAML.

    Split out from the fetch so it can be tested without touching the network.

    Note the ``on:`` key: YAML 1.1 parses a bare ``on`` as the boolean True, so
    the block is looked up under both. PyYAML's safe_load follows YAML 1.1 here
    and every GitHub workflow in existence uses the bare form, so the True
    lookup is the one that actually fires.
    """
    import yaml  # deferred: only needed when a manual run is being set up

    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError:
        # An unparseable workflow is GitHub's problem, not ours; fall back to
        # the old substring behaviour so a manual run without inputs still works.
        return DispatchSpec(supports_dispatch="workflow_dispatch" in raw)

    if not isinstance(doc, dict):
        return DispatchSpec(supports_dispatch=False)

    triggers = doc.get("on", doc.get(True))

    # `on: workflow_dispatch` (scalar) and `on: [push, workflow_dispatch]` (list)
    # are both valid and carry no inputs.
    if triggers == "workflow_dispatch":
        return DispatchSpec(supports_dispatch=True)
    if isinstance(triggers, list):
        return DispatchSpec(supports_dispatch="workflow_dispatch" in triggers)
    if not isinstance(triggers, dict) or "workflow_dispatch" not in triggers:
        return DispatchSpec(supports_dispatch=False)

    block = triggers["workflow_dispatch"]
    # `workflow_dispatch:` with nothing under it parses as None — supported,
    # no inputs.
    if not isinstance(block, dict):
        return DispatchSpec(supports_dispatch=True)

    declared = block.get("inputs")
    if not isinstance(declared, dict):
        return DispatchSpec(supports_dispatch=True)

    inputs: list[WorkflowInput] = []
    for name, spec in declared.items():
        if not isinstance(spec, dict):
            spec = {}
        default = spec.get("default", "")
        # Booleans and numbers arrive typed from YAML; the dispatch payload and
        # every control we build want text.
        if isinstance(default, bool):
            default = "true" if default else "false"
        elif default is None:
            default = ""
        options = spec.get("options")
        inputs.append(WorkflowInput(
            name=str(name),
            type=str(spec.get("type", "string")),
            description=str(spec.get("description", "")),
            default=str(default),
            required=bool(spec.get("required", False)),
            options=[str(o) for o in options] if isinstance(options, list) else [],
        ))
    return DispatchSpec(supports_dispatch=True, inputs=inputs)


def fetch_environments(repo: Optional[str]) -> list[str]:
    """Names of the repo's configured deployment environments.

    Used to fill the choices for an ``environment``-typed input, which the
    workflow file declares without options — the web form looks them up the
    same way. Returns [] when the repo has none or the endpoint is unavailable
    (it 404s on some plans), leaving the caller with a free-text field rather
    than a dead end.
    """
    try:
        rows = _api_json(
            ["repos/{owner}/{repo}/environments", "-q", "[.environments[].name]"],
            repo,
        )
    except GhError:
        return []
    return [str(r) for r in rows] if isinstance(rows, list) else []


def fetch_dispatch_spec(
    repo: Optional[str], path: str, ref: Optional[str] = None
) -> DispatchSpec:
    """Read a workflow file and report whether/how it can be run manually.

    There is no API that returns a workflow's inputs — GitHub's own web form is
    built by parsing the workflow file at the selected ref, and this does the
    same thing. ``ref`` matters: a branch that adds an input has different
    inputs from the default branch, and running with the wrong set silently
    drops values.
    """
    endpoint = f"repos/{{owner}}/{{repo}}/contents/{path}"
    if ref:
        endpoint += f"?ref={ref}"
    raw = _api(
        [endpoint, "-H", "Accept: application/vnd.github.raw"],
        repo,
    )
    spec = _parse_dispatch_spec(raw)

    # An `environment` input declares no options; its choices are the repo's
    # environments. Only pay for the extra call when one is actually declared.
    if any(i.type == "environment" and not i.options for i in spec.inputs):
        names = fetch_environments(repo)
        if names:
            for i in spec.inputs:
                if i.type == "environment" and not i.options:
                    i.options = list(names)
    return spec


def workflow_supports_dispatch(repo: Optional[str], path: str) -> bool:
    """Return True if the workflow file declares a ``workflow_dispatch`` trigger."""
    return fetch_dispatch_spec(repo, path).supports_dispatch


def dispatch_workflow(
    repo: Optional[str],
    workflow_id: int,
    ref: str,
    inputs: Optional[dict[str, str]] = None,
) -> None:
    """Trigger a manual (workflow_dispatch) run of a workflow on ``ref``.

    ``ref`` is a branch or tag name. ``inputs`` maps declared input names to
    string values; GitHub rejects names the workflow does not declare, so pass
    only what came from its own schema.

    Raises GhError if the workflow doesn't support manual dispatch or the ref
    is invalid.
    """
    args = ["-X", "POST",
            f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow_id}/dispatches",
            "-f", f"ref={ref}"]
    # `gh api` builds nested JSON from key[subkey]=value, which is exactly the
    # {"ref": ..., "inputs": {...}} shape this endpoint wants.
    for key, value in (inputs or {}).items():
        args += ["-f", f"inputs[{key}]={value}"]
    _api(args, repo)


@dataclass
class CompareResult:
    """Result of comparing two refs (branches/tags/SHAs)."""
    base: str
    head: str
    ahead_by: int
    behind_by: int
    commits: list[dict] = field(default_factory=list)   # {sha, message}
    files: list[dict] = field(default_factory=list)      # {filename, status, additions, deletions}


def fetch_compare(repo: Optional[str], base: str, head: str) -> CompareResult:
    """Compare two refs (branches/tags/SHAs) via the GitHub compare API.

    Returns the ahead/behind counts plus the commits that are on ``head`` but
    not ``base`` and the files that differ. The commit and file lists are
    capped at 100 entries each to keep the request fast; ``ahead_by`` and
    ``behind_by`` always reflect the true totals.
    """
    # NOTE: the path must be repos/{owner}/{repo}/compare/... — the slash
    # before "compare" is required or the API 404s.
    row = _api_json(
        [f"repos/{{owner}}/{{repo}}/compare/{base}...{head}",
         "-q", "{ahead: .ahead_by, behind: .behind_by, commits: [.commits[] | {sha: .sha, message: .commit.message}][0:100], files: [(.files // [])[] | {filename, status, additions, deletions}][0:100]}"],
        repo,
    )
    if not isinstance(row, dict):
        return CompareResult(base=base, head=head, ahead_by=0, behind_by=0)
    return CompareResult(
        base=base,
        head=head,
        ahead_by=row.get("ahead", 0),
        behind_by=row.get("behind", 0),
        commits=row.get("commits", []),
        files=row.get("files", []),
    )