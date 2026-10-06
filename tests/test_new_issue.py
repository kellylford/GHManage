"""New Issue: the flow around the dialog, run without a window."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402

Frame = ghviewer.GhViewerFrame
ISSUES = ghviewer.VIEW_ISSUES


@pytest.fixture
def inline(monkeypatch):
    """Run worker threads and CallAfter at once, in order."""
    monkeypatch.setattr(ghviewer.wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))

    class Thread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()
    monkeypatch.setattr(ghviewer.threading, "Thread", Thread)


def _dialog(result, title="T", body="B"):
    class Dialog:
        def __init__(self, parent, repo, t="", b=""):
            Dialog.opened_with = (repo, t, b)

        def ShowModal(self): return result
        def values(self): return title, body
        def Destroy(self): pass
    return Dialog


def _frame(view=ISSUES):
    announced, events = [], []
    f = SimpleNamespace(
        repo="me/fork", view_mode=view, _issue_drafts={}, _issue_busy=False,
        filter_text="x", current_limit=200, page_size=100, _fetch_token=1,
        _pending_target=None, announced=announced, events=events,
    )
    f._announce = announced.append
    f._show_new_issue_dialog = lambda r, t: Frame._show_new_issue_dialog(f, r, t)
    f._on_issue_created = lambda *a: Frame._on_issue_created(f, *a)
    f._on_issue_error = lambda m: events.append(("error", m)) or Frame._on_issue_error(f, m)
    f._load_items = lambda: events.append("load")
    f._switch_view = lambda v: events.append(("switch", v))
    f._set_pending_target = lambda *a: Frame._set_pending_target(f, *a)
    return f


def test_creates_on_the_resolved_repo_and_lands_on_it(monkeypatch, inline):
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: "up/r")
    monkeypatch.setattr(ghviewer, "NewIssueDialog", _dialog(ghviewer.wx.ID_OK))
    made = []
    monkeypatch.setattr(ghviewer, "create_issue",
                        lambda repo, t, b, effective=None: made.append((repo, t, b, effective)) or (42, "u"))
    f = _frame()
    Frame._do_new_issue(f)
    assert made == [("me/fork", "T", "B", "up/r")]
    assert f.events == ["load"] and f.filter_text == ""
    assert f._pending_target == (1, ISSUES, "item", "42")
    assert f._issue_busy is False and f._issue_drafts == {}
    assert f.announced[-1] == "Created issue #42 — T"


def test_a_second_ctrl_n_while_busy_does_nothing(monkeypatch, inline):
    f = _frame()
    f._issue_busy = True
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: pytest.fail("no second form"))
    Frame._do_new_issue(f)
    assert f.announced == ["Already creating an issue — wait for it to finish."]


def test_cancel_with_text_keeps_a_draft(monkeypatch, inline):
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: None)
    monkeypatch.setattr(ghviewer, "NewIssueDialog", _dialog(ghviewer.wx.ID_CANCEL, "Half", ""))
    f = _frame()
    Frame._do_new_issue(f)
    assert f._issue_drafts == {"me/fork": ("Half", "")}
    assert f._issue_busy is False


def test_the_draft_comes_back(monkeypatch, inline):
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: None)
    dialog = _dialog(ghviewer.wx.ID_CANCEL, "", "")
    monkeypatch.setattr(ghviewer, "NewIssueDialog", dialog)
    f = _frame()
    f._issue_drafts["me/fork"] = ("Half", "body")
    Frame._do_new_issue(f)
    assert dialog.opened_with == ("me/fork", "Half", "body")
    assert f._issue_drafts == {}   # cancelled empty this time: nothing to keep


def test_a_failure_keeps_the_draft_and_frees_ctrl_n(monkeypatch, inline):
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: None)
    monkeypatch.setattr(ghviewer, "NewIssueDialog", _dialog(ghviewer.wx.ID_OK))
    monkeypatch.setattr(ghviewer.wx, "MessageBox", lambda *a, **k: None)

    def fail(*a, **k):
        raise ghviewer.GhError("HTTP 410: Issues are disabled")
    monkeypatch.setattr(ghviewer, "create_issue", fail)
    f = _frame()
    Frame._do_new_issue(f)
    assert f._issue_drafts == {"me/fork": ("T", "B")}
    assert f._issue_busy is False


def test_created_without_a_number_still_drops_the_draft(monkeypatch, inline):
    monkeypatch.setattr(ghviewer, "parent_repo", lambda r: None)
    monkeypatch.setattr(ghviewer, "NewIssueDialog", _dialog(ghviewer.wx.ID_OK))

    def unreadable(*a, **k):
        raise ghviewer.IssueCreatedUnreadable("odd reply")
    monkeypatch.setattr(ghviewer, "create_issue", unreadable)
    f = _frame()
    Frame._do_new_issue(f)
    assert f._issue_drafts == {} and f._pending_target is None
    assert f.announced[-1] == "Created issue: T"


@pytest.mark.parametrize("change", ["view", "repo"])
def test_having_moved_on_you_are_left_where_you_are(change):
    f = _frame()
    if change == "view":
        f.view_mode = ghviewer.VIEW_BRANCHES
    else:
        f.repo = "me/other"
    Frame._on_issue_created(f, "me/fork", 42, "T", ISSUES)
    assert f.events == [] and f._pending_target is None
    assert f.announced == ["Created issue #42 — T"]


def test_from_another_view_of_the_repo_it_switches_to_issues():
    f = _frame(ghviewer.VIEW_BRANCHES)
    Frame._on_issue_created(f, "me/fork", 42, "T", ghviewer.VIEW_BRANCHES)
    assert f.events == [("switch", ISSUES)]


def test_new_issue_needs_a_repository():
    f = _frame(ghviewer.VIEW_ACTIVITY)
    Frame._do_new_issue(f)
    assert f.announced == ["Select a repository first."]
