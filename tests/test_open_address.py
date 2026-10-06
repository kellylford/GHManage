"""Open Repository or Address: GitHub addresses and where they land."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402
from gh_data import Commit, Item, Release, WorkflowRun  # noqa: E402

Frame = ghviewer.GhViewerFrame
parse = ghviewer.parse_github_url
T = ghviewer.GitHubTarget


@pytest.mark.parametrize("text, target", [
    ("owner/name", T("owner/name")),
    ("https://github.com/owner/name", T("owner/name")),
    ("https://github.com/owner/name.git", T("owner/name")),
    ("git@github.com:owner/name.git", T("owner/name")),
    ("github.com/owner/name/", T("owner/name")),
    ("https://github.com/nvaccess/nvda/issues/11538", T("nvaccess/nvda", "item", "11538")),
    ("https://github.com/o/r/pull/12", T("o/r", "item", "12")),
    ("https://github.com/o/r/pull/12/files", T("o/r", "item", "12")),
    ("https://github.com/o/r/issues/12#issuecomment-99", T("o/r", "item", "12")),
    ("https://github.com/o/r/commit/abc1234", T("o/r", "commit", "abc1234")),
    ("https://github.com/o/r/releases/tag/v1.2.0", T("o/r", "release", "v1.2.0")),
    ("https://github.com/o/r/releases/tag/app/v1", T("o/r", "release", "app/v1")),
    ("https://github.com/o/r/actions/runs/123456", T("o/r", "run", "123456")),
    ("https://github.com/o/r/actions/runs/123456/job/9", T("o/r", "run", "123456")),
    ("https://github.com/o/r/tree/dev", T("o/r", "branch", "dev")),
    ("https://github.com/o/r/tree/main/docs", T("o/r")),
    ("https://github.com/o/r/blob/main/README.md", T("o/r")),
    ("https://github.com/o/r/releases", T("o/r", "view", "releases")),
    ("https://github.com/o/r/pulls", T("o/r", "view", "issues")),
    ("https://github.com/o/r/actions", T("o/r", "view", "workflow")),
    ("https://github.com/o/r/labels", T("o/r", "view", "labels")),
    ("https://github.com/o/r/wiki", T("o/r")),
    ("https://github.com/o/r?tab=readme", T("o/r")),
    ("https://github.com/someone", T("", "user", "someone")),
    ("https://github.com/orgs/nvaccess/repositories", T("", "user", "nvaccess")),
])
def test_parse(text, target):
    assert parse(text) == target


@pytest.mark.parametrize("text", [
    "", "   ", "owner", "https://github.com/", "https://github.com/settings/profile",
    "https://github.com/notifications", "https://github.com/issues/assigned",
])
def test_parse_rejects(text):
    assert parse(text) is None


def test_view_targets_are_real_views():
    for view in ghviewer._URL_VIEWS.values():
        assert view in ghviewer.VIEW_COLUMNS


# ── Landing on the item ─────────────────────────────────────────────────


class Later:
    """Collects wx.CallLater calls instead of running them on a timer."""

    def __init__(self):
        self.calls = []

    def __call__(self, ms, fn, *args):
        self.calls.append((fn, args))


@pytest.fixture
def later(monkeypatch):
    rec = Later()
    monkeypatch.setattr(ghviewer.wx, "CallLater", rec)
    return rec


def _frame(view, target, items):
    frame = SimpleNamespace(
        view_mode=view, _pending_target=target, _shown=list(items),
        _announce=lambda m: None, _goto_issue=lambda n: None,
        _goto_commit=lambda sha: None,
    )
    frame._row_of = lambda it: Frame._row_of(frame, it)
    frame._describe_landing = Frame._describe_landing
    return frame


ISSUES = [Item(n, f"T{n}", "open", f"u{n}", False) for n in (5, 4, 3)]


def test_lands_on_the_issue(later):
    f = _frame(ghviewer.VIEW_ISSUES, (ghviewer.VIEW_ISSUES, "item", "4"), ISSUES)
    assert Frame._take_pending_row(f, ISSUES) == 1
    assert f._pending_target is None


def test_missing_issue_is_fetched_by_number(later):
    f = _frame(ghviewer.VIEW_ISSUES, (ghviewer.VIEW_ISSUES, "item", "99"), ISSUES)
    assert Frame._take_pending_row(f, ISSUES) == 0
    assert (f._goto_issue, (99,)) in later.calls


def test_target_for_another_view_waits(later):
    target = (ghviewer.VIEW_RELEASES, "release", "v1")
    f = _frame(ghviewer.VIEW_ISSUES, target, ISSUES)
    assert Frame._take_pending_row(f, ISSUES) == 0
    assert f._pending_target == target  # still waiting for the releases load


def test_commit_matches_an_abbreviated_sha(later):
    commits = [Commit("a" * 40, "aaaaaaa", "m", "me", ""), Commit("b" * 40, "bbbbbbb", "m", "me", "")]
    f = _frame(ghviewer.VIEW_COMMITS, (ghviewer.VIEW_COMMITS, "commit", "BBBBBBB"), commits)
    assert Frame._take_pending_row(f, commits) == 1


def test_missing_commit_is_fetched(later):
    commits = [Commit("a" * 40, "aaaaaaa", "m", "me", "")]
    f = _frame(ghviewer.VIEW_COMMITS, (ghviewer.VIEW_COMMITS, "commit", "c0ffee"), commits)
    assert Frame._take_pending_row(f, commits) == 0
    assert (f._goto_commit, ("c0ffee",)) in later.calls


def test_release_and_run(later):
    rels = [Release("v2", "", False, False, ""), Release("v1", "", False, False, "")]
    f = _frame(ghviewer.VIEW_RELEASES, (ghviewer.VIEW_RELEASES, "release", "v1"), rels)
    assert Frame._take_pending_row(f, rels) == 1
    runs = [WorkflowRun("CI", "", "", "", "", "", run_id=7), WorkflowRun("CI", "", "", "", "", "", run_id=8)]
    f = _frame(ghviewer.VIEW_WORKFLOW, (ghviewer.VIEW_WORKFLOW, "run", "8"), runs)
    assert Frame._take_pending_row(f, runs) == 1


def test_no_target_lands_on_the_first_row(later):
    f = _frame(ghviewer.VIEW_ISSUES, None, ISSUES)
    assert Frame._take_pending_row(f, ISSUES) == 0
    assert later.calls == []
