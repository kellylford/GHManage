"""The window's text-building logic, exercised without opening a window.

The details panel, comment navigation and favorites are methods on the frame,
but they only touch a few attributes. Each test calls the method on a small
stand-in object carrying just those, so no wx.App or display is needed — only
an importable wx.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

if os.environ.get("CI"):
    import wx  # noqa: F401  — in CI a missing wx must fail, not quietly skip 60 tests
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402
from favorites import FavoriteEntry  # noqa: E402
from gh_data import (  # noqa: E402
    Artifact, Branch, Commit, Item, Label, PagesBuild, PagesFile, PagesSite,
    Release, ReleaseAsset, Tag, Workflow, WorkflowRun,
)

Frame = ghviewer.GhViewerFrame
URL = "https://github.com/o/r/thing"


class FakeText:
    """Just enough of the details wx.TextCtrl."""

    def __init__(self) -> None:
        self.value = ""
        self.selection = None

    def SetValue(self, v): self.value = v
    def GetValue(self): return self.value
    def Clear(self): self.value = ""
    def SetFocus(self): pass
    def SetSelection(self, a, b): self.selection = (a, b)
    def ShowPosition(self, p): pass

    @property
    def lines(self) -> list[str]:
        return self.value.split("\n")

    def selected(self) -> str:
        a, b = self.selection
        return self.value[a:b]


def _frame(**attrs):
    announced: list[str] = []
    frame = SimpleNamespace(
        details_text=FakeText(), items=[], git_items=[], favorites=[],
        commit_branch="", pages_site=None, repo="o/r",
        _comment_positions=[], _current_comment=-1,
        _announce=announced.append, announced=announced,
    )
    frame._line_to_position = lambda line: Frame._line_to_position(frame, line)
    for k, v in attrs.items():
        setattr(frame, k, v)
    return frame


SITE = PagesSite(url="https://o.github.io/r/", source_branch="main")

GIT_ITEMS = [
    Branch("main", "abc", "msg", "me", "2026-01-01", url=URL),
    Commit("c" * 40, "cccccccc", "msg", "me", "2026-01-01", url=URL),
    Tag("v1", "abc", url=URL),
    Label("bug", url=URL),
    Release("v1", "One", False, False, "2026-01-01", url=URL),
    Workflow(1, "CI", ".github/workflows/ci.yml", "active", url=URL),
    WorkflowRun("CI", "completed", "success", "main", "push", "2026-01-01", url=URL),
    ReleaseAsset(1, "a.exe", 100, 5, "2026-01-01", url=URL),
    PagesFile("index.md", URL),
]


def _address_after(lines: list[str], label: str) -> str:
    i = lines.index(label)
    return lines[i + 1]


# ── Addresses sit on their own line ────────────────────────────────────


@pytest.mark.parametrize("item", GIT_ITEMS, ids=lambda i: type(i).__name__)
def test_git_details_put_url_on_its_own_line(item):
    f = _frame(git_items=[item], pages_site=SITE)
    Frame._show_git_details(f, 0)
    lines = f.details_text.lines
    assert _address_after(lines, "URL:") == URL
    # The label is never followed by the address on the same line
    assert not any(l.startswith("URL: ") for l in lines)


def test_pages_build_shows_site_address_on_its_own_line():
    f = _frame(git_items=[PagesBuild(1, "built", "abc", "me", "2026-01-01")], pages_site=SITE)
    Frame._show_git_details(f, 0)
    assert _address_after(f.details_text.lines, "Site:") == SITE.url


def test_issue_details_url_on_its_own_line():
    f = _frame(items=[Item(1, "t", "open", URL, is_pr=True)])
    Frame._show_issue_details(f, 0)
    assert _address_after(f.details_text.lines, "URL:") == URL


@pytest.mark.parametrize("item", [Tag("v1", "abc"), Item(1, "t", "open", "", is_pr=False)],
                         ids=["tag", "issue"])
def test_missing_address_reads_none(item):
    if isinstance(item, Item):
        f = _frame(items=[item])
        Frame._show_issue_details(f, 0)
    else:
        f = _frame(git_items=[item])
        Frame._show_git_details(f, 0)
    assert _address_after(f.details_text.lines, "URL:") == "(none)"


def test_artifact_has_no_address_line():
    f = _frame(git_items=[Artifact(1, "dist", 10, False, "2026-01-01")])
    Frame._show_git_details(f, 0)
    assert "URL:" not in f.details_text.lines


@pytest.mark.parametrize("show, attr", [
    (Frame._show_git_details, "git_items"),
    (Frame._show_issue_details, "items"),
    (Frame._show_favorite_details, "favorites"),
])
@pytest.mark.parametrize("idx", [-1, 0, 5])
def test_out_of_range_clears_details(show, attr, idx):
    f = _frame()
    f.details_text.value = "stale"
    show(f, idx)
    assert f.details_text.value == ""


# ── Favorites ──────────────────────────────────────────────────────────


def test_favorite_details():
    fav = FavoriteEntry("o/r", "issue", URL, "#1 — Bug", subtitle="OPEN", added_at="2026-01-02T03:04:05")
    f = _frame(favorites=[fav])
    Frame._show_favorite_details(f, 0)
    lines = f.details_text.lines
    assert lines[0] == "★ #1 — Bug"
    assert "Detail: OPEN" in lines and "Favorited: 2026-01-02" in lines
    assert _address_after(lines, "URL:") == URL


def test_favorited_page_does_not_repeat_its_address():
    fav = FavoriteEntry("o/r", "page", URL, "index.md", subtitle=URL)
    f = _frame(favorites=[fav])
    Frame._show_favorite_details(f, 0)
    assert f.details_text.value.count(URL) == 1


@pytest.mark.parametrize("item, item_type, title", [
    (Item(4, "Bug", "open", URL, is_pr=False), "issue", "#4 — Bug"),
    (Item(5, "Fix", "open", URL, is_pr=True), "PR", "#5 — Fix"),
    (GIT_ITEMS[0], "branch", "main"),
    (GIT_ITEMS[1], "commit", "cccccccc"),
    (GIT_ITEMS[2], "tag", "v1"),
    (GIT_ITEMS[3], "label", "bug"),
    (GIT_ITEMS[4], "release", "v1"),
    (GIT_ITEMS[5], "workflow", "CI"),
    (GIT_ITEMS[6], "workflow run", "#0 CI"),
    (GIT_ITEMS[8], "page", "index.md"),
])
def test_build_favorite_entry(item, item_type, title):
    entry = Frame._build_favorite_entry(_frame(), item)
    assert (entry.repo, entry.item_type, entry.title, entry.url) == ("o/r", item_type, title, URL)
    assert entry.added_at


def test_unfavoritable_item_is_none():
    assert Frame._build_favorite_entry(_frame(), GIT_ITEMS[7]) is None   # a release asset


# ── Comment navigation ─────────────────────────────────────────────────


def _issue_with_comments(body: str) -> Item:
    return Item(1, "t", "open", URL, is_pr=False, body=body, comment_list=[
        {"author": "ann", "created_at": "2026-01-01T00:00:00Z", "body": "first\nsecond line"},
        {"author": "ben", "created_at": "", "body": "only line"},
    ])


@pytest.mark.parametrize("body", [
    "",
    "one line",
    "para one\n\npara two\nmore",
    "windows\r\nline endings\r\n",
])
def test_comment_navigation_selects_each_comment(body):
    f = _frame(items=[_issue_with_comments(body)])
    Frame._show_issue_details(f, 0)

    Frame._navigate_comment(f, 1)
    assert f.details_text.selected() == (
        "  Comment 1 of 2 — ann (2026-01-01):\n    first\n    second line\n")
    assert f.announced[-1] == "Comment 1 of 2"

    Frame._navigate_comment(f, 1)
    assert f.details_text.selected() == "  Comment 2 of 2 — ben ():\n    only line"

    Frame._navigate_comment(f, 1)
    assert f.announced[-1] == "Already at last comment."
    Frame._navigate_comment(f, -1)
    assert f.details_text.selected().startswith("  Comment 1 of 2")
    Frame._navigate_comment(f, -1)
    assert f.announced[-1] == "Already at first comment."


def test_no_comments_to_navigate():
    f = _frame(items=[Item(1, "t", "open", URL, is_pr=False)])
    Frame._show_issue_details(f, 0)
    Frame._navigate_comment(f, 1)
    assert f.announced == ["No comments to navigate."]


def test_line_to_position():
    f = _frame()
    f.details_text.value = "ab\ncde\n\nf"
    assert [Frame._line_to_position(f, n) for n in range(5)] == [0, 3, 7, 8, 9]


# ── Repo spec parsing ──────────────────────────────────────────────────


@pytest.mark.parametrize("text, repo", [
    ("owner/name", "owner/name"),
    ("  owner/name  ", "owner/name"),
    ("https://github.com/owner/name", "owner/name"),
    ("https://github.com/owner/name.git", "owner/name"),
    ("https://github.com/owner/name/", "owner/name"),
    ("https://github.com/owner/name/issues/12", "owner/name"),
    ("https://github.com/owner/name?tab=readme", "owner/name"),
    ("https://github.com/owner/name#readme", "owner/name"),
    ("git@github.com:owner/name.git", "owner/name"),
    ("github.com/Community-Access/quill", "Community-Access/quill"),
])
def test_parse_repo_spec(text, repo):
    assert ghviewer._parse_repo_spec(text) == repo


@pytest.mark.parametrize("text", ["", "   ", "owner", "owner/", "/name", "https://github.com/owner"])
def test_parse_repo_spec_rejects(text):
    assert ghviewer._parse_repo_spec(text) is None


# ── Go to Number for an item not in the list ───────────────────────────


@pytest.fixture
def inline_worker(monkeypatch):
    """Run the background fetch inline and deliver CallAfter at once."""
    class InlineThread:
        def __init__(self, target, daemon=None): self.target = target
        def start(self): self.target()

    boxes: list[str] = []
    monkeypatch.setattr(ghviewer.threading, "Thread", InlineThread)
    monkeypatch.setattr(ghviewer.wx, "CallAfter", lambda fn, *a: fn(*a))
    monkeypatch.setattr(ghviewer.wx, "MessageBox", lambda msg, *a, **k: boxes.append(msg))
    return boxes


def _goto_frame():
    f = _frame(view_mode=ghviewer.VIEW_ISSUES)
    f._goto_error = lambda n, m: Frame._goto_error(f, n, m)
    f._on_goto_fetched = lambda item, n: Frame._on_goto_fetched(f, item, n)
    return f


@pytest.mark.parametrize("error, spoken", [
    (ghviewer.GhError("HTTP 401: Bad credentials"), "Error fetching #5: HTTP 401: Bad credentials"),
    (KeyError("number"), "Error fetching #5: Unexpected error (KeyError: 'number')"),
])
def test_goto_fetch_failure_is_reported(monkeypatch, inline_worker, error, spoken):
    def fail(number, repo):
        raise error

    monkeypatch.setattr(ghviewer, "fetch_item_by_number", fail)
    f = _goto_frame()
    Frame._goto_issue(f, 5)
    assert f.announced == ["#5 not in current list, fetching…", spoken]
    assert len(inline_worker) == 1 and inline_worker[0].startswith("Could not fetch #5:")


def test_goto_missing_number_says_not_found(monkeypatch, inline_worker):
    monkeypatch.setattr(ghviewer, "fetch_item_by_number", lambda n, r: None)
    f = _goto_frame()
    Frame._goto_issue(f, 9999)
    assert f.announced[-1] == "#9999 not found in o/r."
    assert "does not exist" in inline_worker[0]
