"""Pull request actions: checks, review, merge, draft, reviewers, update branch."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

import gh_data
from gh_data import Check, Item


@pytest.fixture
def no_fork(monkeypatch):
    monkeypatch.setattr(gh_data, "parent_repo", lambda r: None)


def _checks_output(monkeypatch, rows, code=0, stderr=""):
    monkeypatch.setattr(gh_data.subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout=json.dumps(rows) if rows is not None else "", stderr=stderr, returncode=code))


def test_checks_are_read_even_when_gh_exits_non_zero(monkeypatch, no_fork):
    # gh exits 1 when a check failed, 8 while one runs, and prints them anyway
    _checks_output(monkeypatch, [
        {"name": "lint", "state": "SUCCESS", "bucket": "pass", "workflow": "CI"},
        {"name": "test", "state": "FAILURE", "bucket": "fail", "workflow": "CI"},
        {"name": "build", "state": "PENDING", "bucket": "pending", "workflow": "CI"},
    ], code=1)
    checks = gh_data.fetch_pr_checks("o/r", 5)
    assert [c.name for c in checks] == ["test", "build", "lint"]


def test_no_checks(monkeypatch, no_fork):
    _checks_output(monkeypatch, None, code=1, stderr="no checks reported on the 'x' branch")
    assert gh_data.fetch_pr_checks("o/r", 5) == []


def test_checks_error(monkeypatch, no_fork):
    _checks_output(monkeypatch, None, code=1, stderr="HTTP 404")
    with pytest.raises(gh_data.GhError, match="404"):
        gh_data.fetch_pr_checks("o/r", 5)


@pytest.mark.parametrize("method, delete, expected", [
    ("squash", False, ["pr", "merge", "5", "--repo", "o/r", "--squash"]),
    ("rebase", True, ["pr", "merge", "5", "--repo", "o/r", "--rebase", "--delete-branch"]),
])
def test_merge(fake_gh, no_fork, method, delete, expected):
    fake_gh.route("pr merge", "")
    gh_data.merge_pr("o/r", 5, method, delete)
    assert fake_gh.calls == [expected]


def test_merge_rejects_an_unknown_method(no_fork):
    with pytest.raises(ValueError):
        gh_data.merge_pr("o/r", 5, "octopus")


def test_merge_goes_upstream_on_a_fork(fake_gh, monkeypatch):
    monkeypatch.setattr(gh_data, "parent_repo", lambda r: "up/r")
    fake_gh.route("pr merge", "")
    gh_data.merge_pr("me/r", 5, "merge")
    assert fake_gh.calls[0][:5] == ["pr", "merge", "5", "--repo", "up/r"]


@pytest.mark.parametrize("ready, tail", [(True, []), (False, ["--undo"])])
def test_ready_and_draft(fake_gh, no_fork, ready, tail):
    fake_gh.route("pr ready", "")
    gh_data.set_pr_ready("o/r", 5, ready)
    assert fake_gh.calls == [["pr", "ready", "5", "--repo", "o/r", *tail]]


def test_review_sends_the_message_on_stdin(fake_gh, no_fork):
    fake_gh.route("pr review", "")
    gh_data.review_pr("o/r", 5, "request-changes", "Please fix — ünïcode too")
    assert fake_gh.calls == [["pr", "review", "5", "--repo", "o/r", "--request-changes",
                              "--body-file", "-"]]
    assert fake_gh.stdin == ["Please fix — ünïcode too"]


def test_approve_without_a_message(fake_gh, no_fork):
    fake_gh.route("pr review", "")
    gh_data.review_pr("o/r", 5, "approve")
    assert fake_gh.calls == [["pr", "review", "5", "--repo", "o/r", "--approve"]]
    assert fake_gh.stdin == [None]


def test_request_reviewers(fake_gh, no_fork):
    fake_gh.route("pr edit", "")
    gh_data.request_reviewers("o/r", 5, ["alice", "org/team"])
    assert fake_gh.calls == [["pr", "edit", "5", "--repo", "o/r", "--add-reviewer", "alice,org/team"]]


def test_update_branch(fake_gh, no_fork):
    fake_gh.route("update-branch", "{}")
    gh_data.update_pr_branch("o/r", 5)
    assert fake_gh.calls == [["api", "-X", "PUT", "repos/o/r/pulls/5/update-branch"]]


def test_allowed_merge_methods(fake_gh, no_fork):
    fake_gh.route("repo view", {"mergeCommitAllowed": False, "squashMergeAllowed": True,
                                "rebaseMergeAllowed": True})
    assert gh_data.allowed_merge_methods("o/r") == ["squash", "rebase"]


# ── The window ──────────────────────────────────────────────────────────

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402

Frame = ghviewer.GhViewerFrame


def test_format_checks():
    text = ghviewer.format_checks("#5 Fix", [
        Check("test", "FAILURE", "fail", "CI", "https://x/1", "3 failed"),
        Check("lint", "SUCCESS", "pass", "CI"),
        Check("lint2", "SUCCESS", "pass", ""),
    ])
    lines = text.splitlines()
    assert lines[:2] == ["Checks for #5 Fix", "1 failed, 2 passed"]
    assert "failed: CI / test" in lines and "    3 failed" in lines and "passed: lint2" in lines
    assert "L on its run" in lines[-1]


def test_format_no_checks():
    assert ghviewer.format_checks("#5 Fix", []).splitlines()[1] == "No checks have run."


def _frame(item, view=ghviewer.VIEW_ISSUES):
    f = SimpleNamespace(view_mode=view, repo="o/r", announced=[])
    f._announce = f.announced.append
    f._focused_item = lambda: item
    f._focused_pr = lambda: Frame._focused_pr(f)
    return f


def test_pr_actions_need_a_pull_request():
    f = _frame(Item(1, "An issue", "OPEN", "u", False))
    Frame._pr_checks(f)
    assert f.announced == ["Select a pull request in Issues & PRs first."]


def test_a_draft_cannot_be_merged():
    f = _frame(Item(2, "Draft", "OPEN", "u", True, is_draft=True))
    Frame._pr_merge(f)
    assert f.announced == ["#2 is a draft; mark it ready for review first (D)."]


def test_a_merged_pr_cannot_be_merged_again():
    f = _frame(Item(3, "Done", "MERGED", "u", True, is_merged=True))
    Frame._pr_merge(f)
    assert f.announced == ["#3 is merged, so it can't be merged."]


@pytest.mark.parametrize("draft, ready", [(True, True), (False, False)])
def test_d_flips_draft(draft, ready):
    f = _frame(Item(4, "T", "OPEN", "u", True, is_draft=draft))
    calls = []
    f._pr_in_background = lambda call, done, error, reload=True: calls.append(done)
    Frame._pr_toggle_draft(f)
    assert calls == ["#4 is ready for review" if ready else "#4 is back to a draft"]
