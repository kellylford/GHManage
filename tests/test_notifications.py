"""Notifications: parsing GitHub's threads, and what the view does with them."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

import gh_data
from gh_data import Notification, parse_notification


def _raw(n=1, kind="PullRequest", path="pulls/12", unread=True, reason="review_requested",
         repo="o/r", title="Fix it"):
    return {
        "id": str(n), "unread": unread, "reason": reason,
        "updated_at": "2026-10-05T12:00:00Z",
        "subject": {"title": title, "type": kind,
                    "url": f"https://api.github.com/repos/{repo}/{path}" if path else None},
        "repository": {"full_name": repo},
    }


@pytest.mark.parametrize("kind, path, url, number", [
    ("PullRequest", "pulls/12", "https://github.com/o/r/pull/12", 12),
    ("Issue", "issues/7", "https://github.com/o/r/issues/7", 7),
    ("Commit", "commits/abc", "https://github.com/o/r/commit/abc", 0),
    ("Release", "releases/123", "https://github.com/o/r/releases", 0),
    ("Discussion", None, "https://github.com/o/r/discussions", 0),
    ("CheckSuite", None, "https://github.com/o/r/actions", 0),
])
def test_subject_addresses_become_pages(kind, path, url, number):
    n = parse_notification(_raw(kind=kind, path=path))
    assert (n.url, n.number) == (url, number)
    assert n.is_item == (kind in ("Issue", "PullRequest"))


def test_row_and_words():
    n = parse_notification(_raw())
    row = n.to_row(gh_data.NOTIFICATION_COLUMNS)
    assert row["unread"] == "unread"
    assert row["reason"] == "review requested"
    assert row["type"] == "PR"
    assert row["title"] == "#12 Fix it"
    assert row["repo"] == "o/r"
    read = parse_notification(_raw(unread=False, reason="ci_activity", kind="CheckSuite", path=None))
    row = read.to_row(gh_data.NOTIFICATION_COLUMNS)
    assert (row["unread"], row["reason"], row["type"], row["title"]) == ("", "CI activity", "CI run", "Fix it")


def test_unknown_reason_reads_as_words():
    assert parse_notification(_raw(reason="some_new_thing")).reason_display == "some new thing"


def test_fetch_pages_fifty_at_a_time(fake_gh):
    pages = {1: [_raw(i) for i in range(50)], 2: [_raw(i) for i in range(50, 70)]}
    fake_gh.route("notifications?all=false", lambda args: pages[int(args[-1].rsplit("=", 1)[1])])
    notes, more = gh_data.fetch_notifications(100)
    assert len(notes) == 70 and more is False
    assert all("per_page=50" in c[-1] for c in fake_gh.calls)


def test_fetch_stops_at_the_limit_and_says_there_is_more(fake_gh):
    fake_gh.route("notifications", [_raw(i) for i in range(50)])
    notes, more = gh_data.fetch_notifications(30)
    assert len(notes) == 30 and more is True
    assert len(fake_gh.calls) == 1


def test_include_read_asks_for_all(fake_gh):
    fake_gh.route("notifications?all=true", [])
    assert gh_data.fetch_notifications(50, include_read=True) == ([], False)


@pytest.mark.parametrize("fn, args, expected", [
    (gh_data.mark_notification_read, ("9",), ["api", "-X", "PATCH", "notifications/threads/9"]),
    (gh_data.mark_notification_done, ("9",), ["api", "-X", "DELETE", "notifications/threads/9"]),
    (gh_data.unsubscribe_notification, ("9",),
     ["api", "-X", "DELETE", "notifications/threads/9/subscription"]),
    (gh_data.mark_all_notifications_read, (), ["api", "-X", "PUT", "notifications", "-F", "read=true"]),
])
def test_changes_call_the_right_endpoint(fake_gh, fn, args, expected):
    fake_gh.route("notifications", "")
    fn(*args)
    assert fake_gh.calls == [expected]


# ── The view ────────────────────────────────────────────────────────────

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402

Frame = ghviewer.GhViewerFrame


def _note(n, unread=True, number=0):
    return Notification(str(n), f"T{n}", "o/r", unread=unread, number=number,
                        subject_type="Issue" if number else "Release",
                        url=f"https://github.com/o/r/issues/{number}" if number else "u")


class FakeList:
    def __init__(self):
        self.cells = {}
        self.selected = 0

    def SetItem(self, row, col, text): self.cells[(row, col)] = text
    def GetFirstSelected(self): return self.selected


def _frame(notes):
    announced = []
    f = SimpleNamespace(
        view_mode=ghviewer.VIEW_NOTIFICATIONS, git_items=list(notes), _shown=list(notes),
        columns=["unread", "title"], list_mode="quick", favorites=[],
        _category_counts={ghviewer.NOTIFICATIONS_ENTRY: 10},
        list_ctrl=FakeList(), _announce=announced.append, announced=announced,
        focused=[], details_text=SimpleNamespace(Clear=lambda: None),
    )
    f._row_of = lambda it: Frame._row_of(f, it)
    f._item_label = lambda it, col: Frame._item_label(f, it, col)
    f._favorite_prefix = lambda it: ""
    f._redraw_row = lambda row, it: Frame._redraw_row(f, row, it)
    f._refresh_category_labels = lambda: None
    f._adjust_unread_count = lambda d: Frame._adjust_unread_count(f, d)
    f._show_details = lambda row: None
    f._focus_list = lambda row=0: f.focused.append(row)

    def populate(items, use_favorite_prefix=False):
        f._shown = list(items)
        return f._shown
    f._populate_filtered_list = populate
    return f


def test_read_updates_the_row_and_the_count():
    notes = [_note(1), _note(2)]
    f = _frame(notes)
    Frame._on_notification_changed(f, notes[1], "read", "Marked read: T2")
    assert notes[1].unread is False
    assert f.list_ctrl.cells[(1, 0)] == ""        # the "unread" cell is now empty
    assert f._category_counts[ghviewer.NOTIFICATIONS_ENTRY] == 9
    assert f.announced == ["Marked read: T2"]


def test_done_removes_it_and_stays_in_place():
    notes = [_note(1), _note(2), _note(3)]
    f = _frame(notes)
    Frame._on_notification_changed(f, notes[1], "done", "Done: T2")
    assert [n.id for n in f.git_items] == ["1", "3"]
    assert f.focused == [1]   # the row that was below it
    assert f._category_counts[ghviewer.NOTIFICATIONS_ENTRY] == 9


def test_done_on_the_last_row_lands_on_the_new_last():
    notes = [_note(1), _note(2)]
    f = _frame(notes)
    Frame._on_notification_changed(f, notes[1], "done", "")
    assert f.focused == [0]


def test_done_on_a_read_one_leaves_the_count():
    notes = [_note(1, unread=False)]
    f = _frame(notes)
    Frame._on_notification_changed(f, notes[0], "done", "")
    assert f._category_counts[ghviewer.NOTIFICATIONS_ENTRY] == 10


def test_unsubscribe_leaves_it_unread():
    notes = [_note(1)]
    f = _frame(notes)
    Frame._on_notification_changed(f, notes[0], "unsubscribe", "Unsubscribed")
    assert notes[0].unread is True
    assert f._category_counts[ghviewer.NOTIFICATIONS_ENTRY] == 10


def test_change_after_leaving_the_view_touches_no_list():
    notes = [_note(1)]
    f = _frame(notes)
    f.view_mode = ghviewer.VIEW_ISSUES
    Frame._on_notification_changed(f, notes[0], "read", "")
    assert notes[0].unread is False and f.list_ctrl.cells == {}


def test_enter_on_an_issue_opens_it_here_and_marks_it_read():
    note = _note(1, number=42)
    f = _frame([note])
    changes, opened = [], []
    f._run_notification_change = lambda n, c, announce=False: changes.append(c)
    f._open_repo_from_list = lambda repo, item: opened.append((repo, item))
    Frame._open_notification(f, note)
    assert changes == ["read"]
    assert opened == [("o/r", note)]
    assert f._pending_target == (ghviewer.VIEW_ISSUES, "item", "42")


def test_enter_on_a_release_opens_the_browser(monkeypatch):
    note = _note(1, unread=False)
    f = _frame([note])
    opened = []
    monkeypatch.setattr(ghviewer.webbrowser, "open", opened.append)
    f._run_notification_change = lambda *a, **k: pytest.fail("already read")
    Frame._open_notification(f, note)
    assert opened == ["u"]


def test_the_change_functions_are_looked_up_when_used(monkeypatch):
    # They are named, not held, so patching the module reaches them.
    for change, (name, _) in Frame._NOTIFICATION_CHANGES.items():
        assert callable(getattr(ghviewer, name)), change
