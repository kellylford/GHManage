"""The repository actions on the Actions menu act on the repository in front of you."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402
from favorites import FavoriteEntry  # noqa: E402
from gh_data import ActivityEvent, Item, Notification, RepoEntry  # noqa: E402

Frame = ghviewer.GhViewerFrame


class RepoList:
    def __init__(self, data):
        self.data = data

    def GetSelection(self): return 0
    def GetClientData(self, i): return self.data


def _frame(view=ghviewer.VIEW_ISSUES, item=None, pane=1, repo="o/open", listed="o/listed"):
    f = SimpleNamespace(view_mode=view, repo=repo, repo_list=RepoList(listed),
                        announced=[], events=[])
    f._pane_index = lambda w: pane
    f._current_focus = lambda: None
    f._focused_item = lambda: item
    f._announce = f.announced.append
    f._repo_in_front = lambda: Frame._repo_in_front(f)
    f._select_repo = lambda r: f.events.append(("open", r))
    f._open_repo_from_list = lambda r, it: f.events.append(("open from list", r))
    f._do_new_issue = lambda: f.events.append("new issue")
    f._search_flow = lambda prefill=None: f.events.append(("search", prefill))
    return f


@pytest.mark.parametrize("view, item, expected", [
    (ghviewer.VIEW_BRANCHES, None, "o/open"),
    (ghviewer.VIEW_NOTIFICATIONS, Notification("1", "T", "n/r"), "n/r"),
    (ghviewer.VIEW_MY_WORK, Item(1, "T", "OPEN", "u", False, repo="w/r"), "w/r"),
    (ghviewer.VIEW_SEARCH_ISSUES, Item(1, "T", "OPEN", "u", False, repo="s/r"), "s/r"),
    (ghviewer.VIEW_SEARCH_REPOS, RepoEntry("s/repo"), "s/repo"),
    (ghviewer.VIEW_STARRED, RepoEntry("st/r"), "st/r"),
    (ghviewer.VIEW_ACTIVITY, ActivityEvent("PushEvent", "a", "a/r", "pushed"), "a/r"),
    (ghviewer.VIEW_FAVORITES, FavoriteEntry("f/r", "issue", "u", "#1"), "f/r"),
    (ghviewer.VIEW_NOTIFICATIONS, None, None),
])
def test_repo_in_front(view, item, expected):
    assert Frame._repo_in_front(_frame(view, item)) == expected


def test_the_repo_list_wins_when_it_has_focus():
    assert Frame._repo_in_front(_frame(ghviewer.VIEW_NOTIFICATIONS, pane=0)) == "o/listed"


def test_a_category_entry_in_the_repo_list_is_not_a_repo():
    f = _frame(ghviewer.VIEW_BRANCHES, pane=0, listed=ghviewer.MY_WORK_ENTRY)
    assert Frame._repo_in_front(f) == "o/open"


def test_new_issue_in_a_view_of_the_open_repo_stays_there():
    f = _frame(ghviewer.VIEW_BRANCHES)
    Frame._new_issue_in_front(f)
    assert f.events == ["new issue"]


def test_new_issue_from_the_repo_list_opens_that_repo_first():
    f = _frame(ghviewer.VIEW_BRANCHES, pane=0, repo="o/listed")
    Frame._new_issue_in_front(f)
    assert f.events == [("open", "o/listed"), "new issue"]


def test_new_issue_from_a_notification_opens_its_repo_with_a_way_back():
    f = _frame(ghviewer.VIEW_NOTIFICATIONS, Notification("1", "T", "n/r"))
    Frame._new_issue_in_front(f)
    assert f.events == [("open from list", "n/r"), "new issue"]


def test_new_issue_with_no_repo_says_so():
    f = _frame(ghviewer.VIEW_NOTIFICATIONS, None, repo=None)
    Frame._new_issue_in_front(f)
    assert f.events == [] and f.announced == ["Select a repository first: New Issue needs one."]


def test_search_this_repository():
    f = _frame(ghviewer.VIEW_MY_WORK, Item(1, "T", "OPEN", "u", False, repo="w/r"))
    Frame._search_repo_in_front(f)
    assert f.events == [("search", (ghviewer.KIND_ISSUES, "repo:w/r "))]


def test_repo_actions_are_always_on_the_actions_menu():
    # Ctrl+N and Ctrl+Shift+S must never be parked by a greyed-out item.
    import inspect
    src = inspect.getsource(Frame._update_actions_menu)
    assert "self._act_new_issue.Enable(True)" in src
    assert "self._act_search_repo.Enable(True)" in src
