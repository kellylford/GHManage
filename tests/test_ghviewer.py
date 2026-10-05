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
    monkeypatch.setattr(ghviewer.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
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


# ── Starred and watched repos in the repository list ───────────────────


class FakeListBox:
    """Just enough of the repo wx.ListBox."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, object]] = []
        self.selection = -1
        self.focused = 0

    def Clear(self):
        self.rows = []
        self.selection = -1

    def Append(self, label, clientData=None): self.rows.append((label, clientData))
    def GetCount(self): return len(self.rows)
    def GetClientData(self, i): return self.rows[i][1]
    def SetSelection(self, i): self.selection = i
    def GetSelection(self): return self.selection
    def SetFocus(self): self.focused += 1
    def SetString(self, i, label): self.rows[i] = (label, self.rows[i][1])

    @property
    def labels(self) -> list[str]:
        return [label for label, _ in self.rows]


def _repo_frame(sources=(), extras=None, pinned=(), repo=None, view=ghviewer.VIEW_ISSUES,
                focus=None, loaded_once=False):
    f = _frame(
        repo=repo, view_mode=view, repo_list=FakeListBox(),
        _pinned_repos=list(pinned), _repo_sources=set(sources),
        _extra_repos=dict(extras or {}), _all_repos=[],
        _repo_token=0, _repos_loaded_once=loaded_once,
    )
    for name in ("_extra_repo_rows", "_repos_loaded_message", "_restore_repo_selection"):
        setattr(f, name, getattr(Frame, name).__get__(f))
    f._current_focus = lambda: focus
    return f


def _row(name, desc=""):
    return {"nameWithOwner": name, "description": desc}


def test_repo_list_without_extras_is_as_before():
    f = _repo_frame()
    Frame._on_repos_loaded(f, [_row("me/a", "Mine")], {}, [])
    assert f.repo_list.labels == ["★ Favorites", "Activity", "me/a — Mine"]
    assert f.repo_list.rows[1][1] == ghviewer.ACTIVITY_ENTRY
    assert f.repo_list.selection == 0
    assert f.announced[-1] == "Loaded 1 repositories. Select one to view issues and PRs."


def test_starred_and_watched_follow_your_own_and_say_why():
    extras = {
        "starred": [_row("x/star", "S"), _row("x/both"), _row("me/a")],
        "watched": [_row("x/both"), _row("x/watch"), _row("me/a")],
    }
    f = _repo_frame({"starred", "watched"}, extras, pinned=["p/pin"])
    Frame._on_repos_loaded(f, [_row("me/a")], extras, [])
    assert f.repo_list.labels == [
        "★ Favorites", "Activity", "📌 p/pin", "me/a",
        "x/star (starred) — S",
        "x/both (starred, watching)",
        "x/watch (watching)",
    ]
    # Every repo row carries just its name, for _select_repo
    assert [d for _, d in f.repo_list.rows[2:]] == [
        "p/pin", "me/a", "x/star", "x/both", "x/watch"]
    # Counted as added: your own me/a is not counted again
    assert f.announced[-1].startswith(
        "Loaded 5 repositories, including 2 starred and 2 watched.")


def test_a_list_cut_off_at_its_limit_says_so():
    starred = [_row(f"x/s{i}") for i in range(ghviewer.STARRED_LIMIT)]
    f = _repo_frame({"starred"}, {"starred": starred})
    Frame._on_repos_loaded(f, [], {"starred": starred}, [])
    assert "100 starred (from your latest 100)" in f.announced[-1]


def test_own_repos_first_while_extras_load():
    f = _repo_frame({"starred"})
    Frame._on_repos_loaded(f, [_row("me/a")], None, None, token=0)
    assert f.repo_list.labels[-1] == "me/a"
    assert f.announced[-1] == "Loaded 1 repositories. Loading starred repositories…"


def test_a_switched_off_list_is_not_shown_even_if_cached():
    extras = {"starred": [_row("x/star")], "watched": [_row("x/watch")]}
    f = _repo_frame({"watched"}, extras)
    Frame._on_repos_loaded(f, [], None, None)
    assert f.repo_list.labels[2:] == ["x/watch (watching)"]


def test_extra_list_failure_is_reported_alongside_the_rest():
    f = _repo_frame({"starred"})
    Frame._on_repos_loaded(f, [_row("me/a")], {}, ["starred repositories: HTTP 403"])
    assert f.repo_list.labels[-1] == "me/a"
    assert f.announced[-1] == (
        "Loaded 1 repositories, including 0 starred, "
        "but couldn't load starred repositories: HTTP 403")


def test_a_superseded_repo_load_is_dropped():
    f = _repo_frame({"starred", "watched"})
    f._repo_token = 2
    Frame._on_repos_loaded(f, [_row("me/a")], {"starred": [_row("x/s")]}, [], token=1)
    assert f.repo_list.rows == [] and f._extra_repos == {}


def test_rebuilt_list_keeps_the_current_repo_selected():
    extras = {"starred": [_row("x/star")]}
    f = _repo_frame({"starred"}, extras, repo="x/star")
    Frame._on_repos_loaded(f, [_row("me/a")], extras, [])
    assert f.repo_list.GetClientData(f.repo_list.selection) == "x/star"


def test_rebuilt_list_keeps_the_row_you_were_on():
    # Arrowing through the list when the starred repos arrive: stay put
    f = _repo_frame({"starred"})
    Frame._on_repos_loaded(f, [_row("me/a"), _row("me/b")], None, None)
    f.repo_list.SetSelection(3)  # me/b
    Frame._on_repos_loaded(f, [_row("me/a"), _row("me/b")], {"starred": [_row("x/s")]}, [])
    assert f.repo_list.GetClientData(f.repo_list.selection) == "me/b"


def test_rebuilt_list_selects_nothing_when_the_shown_repo_is_gone():
    # Viewing a starred repo, then switching starred off
    f = _repo_frame(repo="x/star")
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.selection == ghviewer.wx.NOT_FOUND


def test_rebuilt_list_keeps_activity_selected_in_the_activity_view():
    f = _repo_frame(view=ghviewer.VIEW_ACTIVITY, repo="me/a")
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.selection == 1


def test_first_load_takes_focus():
    f = _repo_frame(focus=object())
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.focused == 1 and f._repos_loaded_once


def test_a_later_load_leaves_focus_alone_while_the_app_is_in_the_background():
    # No focused window: what the app sees after Enter opened the browser
    f = _repo_frame(focus=None, loaded_once=True)
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.focused == 0


def test_a_later_load_leaves_focus_where_you_are():
    # A list switched on from the menu lands while you read something else
    f = _repo_frame(focus=object(), loaded_once=True)
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.focused == 0


def test_a_later_load_keeps_focus_in_the_repo_list():
    f = _repo_frame(loaded_once=True)
    f._current_focus = lambda: f.repo_list
    Frame._on_repos_loaded(f, [_row("me/a")], {}, [])
    assert f.repo_list.focused == 1


def _loader(f):
    f._on_repos_loaded = lambda *a, **k: Frame._on_repos_loaded(f, *a, **k)


def test_load_repos_fetches_only_the_lists_switched_on(monkeypatch, inline_worker):
    calls = []
    monkeypatch.setattr(ghviewer, "list_repos", lambda limit: [_row("me/a")])
    monkeypatch.setattr(ghviewer, "list_starred_repos",
                        lambda limit: calls.append(("starred", limit)) or [_row("x/s")])
    monkeypatch.setattr(ghviewer, "list_watched_repos",
                        lambda limit: calls.append(("watched", limit)) or [])
    f = _repo_frame({"starred"})
    _loader(f)
    Frame._load_repos(f)
    assert calls == [("starred", 100)]
    assert f.repo_list.labels[-1] == "x/s (starred)"


def test_watched_looks_deeper_than_starred(monkeypatch, inline_worker):
    calls = []
    monkeypatch.setattr(ghviewer, "list_repos", lambda limit: [])
    monkeypatch.setattr(ghviewer, "list_watched_repos",
                        lambda limit: calls.append(limit) or [])
    f = _repo_frame({"watched"})
    _loader(f)
    Frame._load_repos(f)
    assert calls == [ghviewer.WATCHED_LIMIT] and ghviewer.WATCHED_LIMIT > 100


def test_load_repos_survives_a_failing_extra_list(monkeypatch, inline_worker):
    def boom(limit):
        raise ghviewer.GhError("HTTP 403")
    monkeypatch.setattr(ghviewer, "list_repos", lambda limit: [_row("me/a")])
    monkeypatch.setattr(ghviewer, "list_watched_repos", boom)
    f = _repo_frame({"watched"})
    _loader(f)
    Frame._load_repos(f)
    assert f.repo_list.labels[-1] == "me/a"
    assert "couldn't load watched repositories: HTTP 403" in f.announced[-1]


def test_toggling_a_list_saves_it_and_reloads(app_data):
    import pinned_repos
    f = _repo_frame()
    reloads = []
    f._update_menu_checks = lambda: None
    f._load_repos = lambda: reloads.append("load")
    f._refresh_repo_list = lambda: reloads.append("refresh")
    Frame._toggle_repo_source(f, "starred")
    assert pinned_repos.load_repo_sources() == {"starred"}
    assert reloads == ["load"]
    # Turning it off needs no fetch, only a rebuild
    f._extra_repos = {"starred": [_row("x/s")]}
    Frame._toggle_repo_source(f, "starred")
    assert pinned_repos.load_repo_sources() == set()
    assert reloads == ["load", "refresh"]
    assert "starred" not in f._extra_repos
    assert f.announced[-1] == "Hiding starred repositories in the repository list."


@pytest.mark.parametrize("name, spoken", [
    ("me/a", "me/a is one of your own repositories"),
    ("x/s", "x/s is in the list because you star or watch it"),
    (ghviewer.ACTIVITY_ENTRY, "That entry is always in the list."),
])
def test_remove_from_list_explains_what_it_cannot_remove(name, spoken):
    f = _repo_frame()
    f._all_repos = [_row("me/a")]
    f.repo_list.Append("row", name)
    f.repo_list.SetSelection(0)
    Frame.on_remove_repo(f, None)
    assert f.announced[-1].startswith(spoken)


# ── Rows and items with a quick filter on ──────────────────────────────


class FakeItemList:
    def __init__(self, selected=-1):
        self.selected = selected

    def GetFirstSelected(self): return self.selected


def _filtered_frame(items, shown, selected):
    f = _frame(view_mode=ghviewer.VIEW_ACTIVITY, git_items=items, _shown=shown,
               list_ctrl=FakeItemList(selected))
    for name in ("_row_item", "_row_of", "_view_source", "_show_git_details",
                 "_show_issue_details", "_show_favorite_details"):
        setattr(f, name, getattr(Frame, name).__get__(f))
    return f


def _event(repo, n=0):
    return ghviewer.ActivityEvent("IssuesEvent", "a", repo, f"opened issue #{n}", title=f"T{n}",
                                  subject_kind="issue", number=n,
                                  subject_url=f"https://github.com/{repo}/issues/{n}",
                                  url=f"https://github.com/{repo}/issues/{n}")


def test_filtered_row_is_the_item_it_shows():
    a, b, c = _event("o/a", 1), _event("o/b", 2), _event("o/c", 3)
    # A filter hides a and b, so c is row 0
    f = _filtered_frame([a, b, c], [c], 0)
    assert Frame._focused_item(f) is c
    Frame._show_details(f, 0)
    assert f.details_text.lines[0].startswith("a opened issue #3 in o/c")


def test_g_with_a_filter_goes_to_the_repo_you_heard():
    a, c = _event("o/a", 1), _event("o/c", 3)
    f = _filtered_frame([a, c], [c], 0)
    f.repo_list = FakeListBox()
    f.git_items = [a, c]
    f._activity_more, f.current_limit = True, 100
    f._focused_item = lambda: Frame._focused_item(f)
    opened = []
    f._select_repo = opened.append
    Frame._go_to_event_repo(f)
    assert opened == ["o/c"]


def test_nothing_selected_is_no_item():
    f = _filtered_frame([_event("o/a")], [_event("o/a")], -1)
    assert Frame._focused_item(f) is None


# ── Favorites from the Activity view ───────────────────────────────────


def test_activity_favorite_is_what_the_event_is_about():
    ev = _event("x/proj", 9)
    entry = Frame._build_favorite_entry(_frame(repo=None), ev)
    assert (entry.repo, entry.item_type, entry.title, entry.url) == (
        "x/proj", "issue", "#9 — T9", "https://github.com/x/proj/issues/9")


def test_events_without_a_subject_cannot_be_favorited():
    star = ghviewer.ActivityEvent("WatchEvent", "a", "o/r", "starred", url="https://github.com/o/r")
    f = _frame(view_mode=ghviewer.VIEW_ACTIVITY)
    f._focused_item = lambda: star
    Frame._toggle_favorite(f)
    assert "nothing to favorite" in f.announced[-1]
    assert f.favorites == []


def test_two_events_sharing_an_address_do_not_unfavorite_each_other(app_data):
    # Before: both used the repo address, so F on the second removed the first
    star = ghviewer.ActivityEvent("WatchEvent", "a", "o/r", "starred", url="https://github.com/o/r")
    issue = _event("o/r", 4)
    f = _frame(view_mode=ghviewer.VIEW_ACTIVITY, repo=None)
    f._refresh_repo_list_fav_count = lambda: None
    f._build_favorite_entry = lambda item: Frame._build_favorite_entry(f, item)
    f._focused_item = lambda: issue
    Frame._toggle_favorite(f)
    assert [fav.url for fav in f.favorites] == [issue.subject_url]
    f._focused_item = lambda: star
    Frame._toggle_favorite(f)
    assert [fav.url for fav in f.favorites] == [issue.subject_url]


def test_star_prefix_follows_the_subject_not_the_repo():
    fav = FavoriteEntry("o/r", "issue", "https://github.com/o/r/issues/4", "#4")
    f = _frame(favorites=[fav])
    star = ghviewer.ActivityEvent("WatchEvent", "a", "o/r", "starred", url="https://github.com/o/r")
    comment = ghviewer.ActivityEvent(
        "IssueCommentEvent", "a", "o/r", "commented on issue #4",
        url="https://github.com/o/r/issues/4#issuecomment-1",
        subject_kind="issue", number=4, subject_url="https://github.com/o/r/issues/4")
    assert Frame._favorite_prefix(f, comment) == "★ "
    assert Frame._favorite_prefix(f, star) == ""


# ── Activity view ──────────────────────────────────────────────────────


EVENT = ghviewer.ActivityEvent(
    event_type="IssueCommentEvent", actor="alice", repo="x/proj",
    action="commented on issue #9", created_at="2026-10-05T14:32:00Z",
    title="Crash on start", url="https://github.com/x/proj/issues/9#c1",
    body="Same here.\nSecond line.",
)


def test_activity_details_read_as_a_sentence_then_fields():
    f = _frame(git_items=[EVENT])
    Frame._show_git_details(f, 0)
    lines = f.details_text.lines
    assert lines[0] == "alice commented on issue #9 in x/proj: Crash on start"
    assert "About: Crash on start" in lines and "Repository: x/proj" in lines
    assert _address_after(lines, "URL:") == EVENT.url
    assert "Same here." in lines and "Second line." in lines
    assert lines[-1] == "Press G to open x/proj here in GHManage."


def test_activity_details_without_title_or_body():
    ev = ghviewer.ActivityEvent("WatchEvent", "bob", "x/p", "starred", url="https://github.com/x/p")
    f = _frame(git_items=[ev])
    Frame._show_git_details(f, 0)
    lines = f.details_text.lines
    assert lines[0] == "bob starred x/p"
    assert not any(line.startswith("About:") for line in lines)


def _activity_frame(limit=100):
    f = _frame(
        view_mode=ghviewer.VIEW_ACTIVITY, repo=None, current_limit=limit,
        page_size=100, _fetch_token=1, filter_text="", _activity_focus_row=0,
        _activity_more=False, _shown=[],
    )
    f._fetch_is_current = lambda t: t == f._fetch_token
    def populate(items, use_favorite_prefix=False):
        f._shown = list(items)
        return f._shown
    f._populate_filtered_list = populate
    f._focus_list = lambda row=0: None
    f._update_title = lambda: None
    statuses = []
    f._set_view_status = lambda msg, keys="": statuses.append((msg, keys))
    f.statuses = statuses
    return f


@pytest.fixture
def call_later(monkeypatch):
    calls = []
    monkeypatch.setattr(ghviewer.wx, "CallLater", lambda ms, fn, *a: calls.append((fn, a)))
    return calls


def test_activity_loaded_status(call_later):
    f = _activity_frame()
    Frame._on_activity_loaded(f, 1, [EVENT] * 100, True)
    msg, keys = f.statuses[-1]
    assert msg == "Activity — 100 events, newest first. Ctrl++ loads older ones."
    assert "G=go to repository" in keys and "Enter=open in browser" in keys
    assert f._activity_more is True
    assert f.git_items == [EVENT] * 100
    assert call_later[-1][1] == (0,)  # focus on the newest


def test_activity_short_feed_says_that_is_everything(call_later):
    f = _activity_frame()
    Frame._on_activity_loaded(f, 1, [EVENT])
    assert f.statuses[-1][0] == "Activity — 1 event, newest first. That is all GitHub keeps."


def test_empty_activity_explains_where_events_come_from(call_later):
    f = _activity_frame()
    Frame._on_activity_loaded(f, 1, [])
    assert "repositories you star or watch" in f.statuses[-1][0]


def test_stale_activity_results_are_dropped():
    f = _activity_frame()
    Frame._on_activity_loaded(f, 0, [EVENT])
    assert f.statuses == [] and f.git_items == []


def test_view_more_stops_at_what_github_keeps():
    f = _activity_frame(limit=ghviewer.ACTIVITY_MAX)
    f._activity_more = False
    f._load_items = lambda: pytest.fail("should not reload")
    Frame.on_view_more(f, None)
    assert f.announced[-1] == (
        "No older activity. GitHub keeps only your latest 300 events, "
        "from the last 90 days.")


def test_view_more_while_loading_says_so():
    f = _activity_frame()
    f._activity_more = None
    f._load_items = lambda: pytest.fail("should not reload")
    Frame.on_view_more(f, None)
    assert f.announced[-1] == "Activity is still loading."


def test_view_more_lands_on_the_first_older_event(call_later):
    f = _activity_frame()
    f._activity_more = True
    f._shown = [EVENT] * 96
    loads = []
    f._load_items = lambda: loads.append(f.current_limit)
    Frame.on_view_more(f, None)
    assert loads == [200] and f._activity_focus_row == 96
    Frame._on_activity_loaded(f, 1, [EVENT] * 196, True, 96)
    assert call_later[-1][1] == (96,)


def _load_frame(view=ghviewer.VIEW_ACTIVITY):
    """Enough of the frame for _load_items, with the worker run inline."""
    f = _activity_frame()
    f.view_mode = view
    f.repo, f.tab_filter, f.state_filter, f.label_filter = None, "both", "open", ""
    f.list_ctrl = SimpleNamespace(DeleteAllItems=lambda: None)
    f._VIEW_LABELS = Frame._VIEW_LABELS
    f._begin_fetch = lambda: 1
    landed = []
    f._on_activity_loaded = lambda *a: landed.append(a)
    f._on_fetch_error = lambda t, m: Frame._on_fetch_error(f, t, m)
    f._on_items_error = lambda m: f._announce(f"Error: {m}")
    return f, landed


def test_the_focus_row_goes_to_one_load_only(monkeypatch, inline_worker):
    # View More's row is handed to that load and cleared at once, so a load
    # that never lands can't leave it for the next one.
    monkeypatch.setattr(ghviewer, "fetch_activity", lambda limit: ([EVENT], True))
    f, landed = _load_frame()
    f._activity_focus_row = 96
    Frame._load_items(f)
    assert landed[-1][-1] == 96 and f._activity_focus_row == 0
    Frame._load_items(f)
    assert landed[-1][-1] == 0


def test_a_failed_activity_load_does_not_stay_loading(monkeypatch, inline_worker):
    def boom(limit):
        raise ghviewer.GhError("HTTP 401")
    monkeypatch.setattr(ghviewer, "fetch_activity", boom)
    f, _ = _load_frame()
    f._fetch_is_current = lambda t: True
    Frame._load_items(f)
    assert f._activity_more is False
    assert f.announced[-1] == "Error: HTTP 401"


def test_go_to_event_repo_opens_it_and_selects_it_in_the_list():
    f = _repo_frame(view=ghviewer.VIEW_ACTIVITY)
    f.repo_list.Append("x/proj (starred)", "x/proj")
    f.list_ctrl = FakeItemList(4)
    f.git_items, f._activity_more, f.current_limit = [EVENT], True, 200
    f._focused_item = lambda: EVENT
    opened = []
    f._select_repo = opened.append
    Frame._go_to_event_repo(f)
    assert opened == ["x/proj"] and f.repo_list.selection == 0
    # Remembered for Backspace: the events, whether there are more, the event
    assert f._activity_return == ([EVENT], True, EVENT, 200)


def test_go_to_a_repo_not_in_the_list_deselects_activity():
    f = _repo_frame(view=ghviewer.VIEW_ACTIVITY)
    f.repo_list.Append("Activity", ghviewer.ACTIVITY_ENTRY)
    f.repo_list.SetSelection(0)
    f.list_ctrl = FakeItemList(0)
    f.git_items, f._activity_more, f.current_limit = [EVENT], False, 100
    f._focused_item = lambda: EVENT
    f._select_repo = lambda r: None
    Frame._go_to_event_repo(f)
    assert f.repo_list.selection == ghviewer.wx.NOT_FOUND


def test_backspace_returns_to_the_feed_without_fetching(call_later):
    f = _activity_frame()
    f.view_mode = ghviewer.VIEW_ISSUES
    f.repo, f.repo_list = "x/proj", FakeListBox()
    other = ghviewer.ActivityEvent("WatchEvent", "b", "o/r", "starred")
    f._activity_return = ([EVENT, other], True, other, 200)
    switched = []
    f._switch_view = lambda mode, load=True: (switched.append((mode, load)),
                                               setattr(f, "view_mode", mode))
    f._begin_fetch = lambda: 1
    f._restore_repo_selection = lambda prev: None
    f._row_of = lambda item: Frame._row_of(f, item)
    f._on_activity_loaded = lambda *a: Frame._on_activity_loaded(f, *a)
    Frame._return_to_activity(f)
    assert switched == [(ghviewer.VIEW_ACTIVITY, False)]
    assert f.git_items == [EVENT, other] and f.current_limit == 200
    assert call_later[-1][1] == (1,)  # back on the event you left
    assert f._activity_return is None
    assert f.announced[-1] == "Back to activity"


@pytest.mark.parametrize("mode, repo, loads", [
    (ghviewer.VIEW_ACTIVITY, None, ["items"]),       # needs no repo, and loads
    (ghviewer.VIEW_FAVORITES, None, ["favorites"]),
    (ghviewer.VIEW_BRANCHES, None, []),              # refused: no repo
    (ghviewer.VIEW_BRANCHES, "o/r", ["items"]),
])
def test_switch_view_loads_activity_without_a_repo(mode, repo, loads):
    loaded = []
    f = _frame(view_mode=ghviewer.VIEW_ISSUES, repo=repo, page_size=100, current_limit=100,
               _activity_return=None)
    for name in ("_rebuild_columns", "_rebuild_columns_menu", "_update_menu_checks"):
        setattr(f, name, lambda: None)
    f._load_items = lambda: loaded.append("items")
    f._load_favorites_view = lambda: loaded.append("favorites")
    Frame._switch_view(f, mode)
    assert loaded == loads


def test_switch_view_without_load():
    f = _frame(view_mode=ghviewer.VIEW_ISSUES, repo="o/r", page_size=100, current_limit=100,
               _activity_return=("kept",))
    for name in ("_rebuild_columns", "_rebuild_columns_menu", "_update_menu_checks"):
        setattr(f, name, lambda: None)
    f._load_items = lambda: pytest.fail("should not load")
    Frame._switch_view(f, ghviewer.VIEW_ACTIVITY, load=False)
    assert f.view_mode == ghviewer.VIEW_ACTIVITY
    # Leaving the issues list for anything else forgets the way back
    assert f._activity_return is None


def test_activity_keeps_the_current_repo():
    # Ctrl+Shift+A for a glance, then Ctrl+1 goes straight back
    f = _frame(view_mode=ghviewer.VIEW_ISSUES, repo="o/r")
    f._switch_view = lambda mode: setattr(f, "view_mode", mode)
    Frame._select_activity(f)
    assert f.view_mode == ghviewer.VIEW_ACTIVITY and f.repo == "o/r"


def test_refresh_in_favorites_reloads_favorites():
    loads = []
    f = _frame(view_mode=ghviewer.VIEW_FAVORITES, repo="o/r")
    f._load_favorites_view = lambda: loads.append("favorites")
    f._load_items = lambda: loads.append("items")
    Frame.on_refresh(f, None)
    assert loads == ["favorites"]


def test_activity_view_is_allowed_without_a_repo():
    assert ghviewer.VIEW_ACTIVITY in ghviewer.REPOLESS_VIEWS
    assert ghviewer.VIEW_ACTIVITY in ghviewer.VIEW_COLUMNS


def test_backspace_after_g_with_a_filter_lands_on_that_event(call_later):
    # G pressed on row 0 of a filtered list showing the third event; the
    # filter is gone on the way back, so row 0 would be the wrong event.
    a, b, c = _event("o/a", 1), _event("o/b", 2), _event("o/c", 3)
    f = _activity_frame()
    f.view_mode, f.repo, f.repo_list = ghviewer.VIEW_ACTIVITY, None, FakeListBox()
    f.git_items, f._shown, f.list_ctrl = [a, b, c], [c], FakeItemList(0)
    f._activity_more, f.filter_text = True, "o/c"
    f._focused_item = lambda: Frame._focused_item(f)
    f._row_item = lambda row: Frame._row_item(f, row)
    f._select_repo = lambda repo: setattr(f, "view_mode", ghviewer.VIEW_ISSUES)
    Frame._go_to_event_repo(f)

    f._switch_view = lambda mode, load=True: (setattr(f, "view_mode", mode),
                                               setattr(f, "filter_text", ""))
    f._begin_fetch = lambda: 1
    f._restore_repo_selection = lambda prev: None
    f._row_of = lambda item: Frame._row_of(f, item)
    f._on_activity_loaded = lambda *args: Frame._on_activity_loaded(f, *args)
    Frame._return_to_activity(f)
    assert call_later[-1][1] == (2,)  # c's row in the unfiltered feed
