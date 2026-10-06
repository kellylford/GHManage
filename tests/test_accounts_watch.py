"""Switching gh accounts, and how you watch a repository."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

import gh_data


def _status(monkeypatch, stdout, stderr="", code=0):
    import json as _json
    out = stdout if isinstance(stdout, str) else _json.dumps(stdout)
    monkeypatch.setattr(gh_data.subprocess, "run", lambda *a, **k: SimpleNamespace(
        stdout=out, stderr=stderr, returncode=code))


def test_list_accounts_github_com_only_in_use_first(monkeypatch):
    _status(monkeypatch, {"hosts": {
        "github.com": [
            {"login": "work", "active": False},
            {"login": "me", "active": True},
        ],
        "ghe.corp": [{"login": "corp", "active": True}],
    }})
    accounts = gh_data.list_accounts()
    assert [(a.login, a.active) for a in accounts] == [("me", True), ("work", False)]


def test_list_accounts_survives_a_stale_account(monkeypatch):
    # gh exits 1 when one stored token is bad, but still prints the list.
    _status(monkeypatch, {"hosts": {"github.com": [
        {"login": "me", "active": True}, {"login": "old", "active": False, "state": "error"},
    ]}}, stderr="token invalid", code=1)
    assert [a.login for a in gh_data.list_accounts()] == ["me", "old"]


def test_list_accounts_on_an_old_gh(monkeypatch):
    _status(monkeypatch, "", stderr="unknown flag: --json", code=1)
    with pytest.raises(gh_data.GhError, match="newer gh"):
        gh_data.list_accounts()


def test_switch_account_forgets_who_was_signed_in(fake_gh, monkeypatch):
    monkeypatch.setattr(gh_data, "_login", "me")
    fake_gh.route("auth switch", "")
    gh_data.switch_account("work")
    assert fake_gh.calls == [["auth", "switch", "--hostname", "github.com", "--user", "work"]]
    assert gh_data._login is None


@pytest.mark.parametrize("reply, level", [
    ({"subscribed": True, "ignored": False}, gh_data.WATCH_ALL),
    ({"subscribed": False, "ignored": True}, gh_data.WATCH_IGNORE),
    (gh_data.GhError("gh: Not Found (HTTP 404)"), gh_data.WATCH_PARTICIPATING),
])
def test_get_watch_level(fake_gh, reply, level):
    fake_gh.route("repos/o/r/subscription", reply)
    assert gh_data.get_watch_level("o/r") == level


def test_missing_scope_says_how_to_add_it(fake_gh):
    fake_gh.route("subscription", gh_data.GhError(
        'Not Found (HTTP 404)\ngh: This API operation needs the "notifications" scope. '
        "To request it, run:  gh auth refresh -h github.com -s notifications"))
    with pytest.raises(gh_data.MissingScope) as info:
        gh_data.get_watch_level("o/r")
    assert info.value.scope == "notifications"
    assert "gh auth refresh -h github.com -s notifications" in str(info.value)


@pytest.mark.parametrize("level, args", [
    (gh_data.WATCH_PARTICIPATING, ["api", "-X", "DELETE", "repos/o/r/subscription"]),
    (gh_data.WATCH_ALL, ["api", "-X", "PUT", "repos/o/r/subscription", "-F", "subscribed=true"]),
    (gh_data.WATCH_IGNORE, ["api", "-X", "PUT", "repos/o/r/subscription", "-F", "ignored=true"]),
])
def test_set_watch_level(fake_gh, level, args):
    fake_gh.route("subscription", "")
    gh_data.set_watch_level("o/r", level)
    assert fake_gh.calls == [args]


def test_set_watch_level_without_the_scope(fake_gh):
    fake_gh.route("subscription", gh_data.GhError('needs the "notifications" scope'))
    with pytest.raises(gh_data.MissingScope):
        gh_data.set_watch_level("o/r", gh_data.WATCH_ALL)


# ── The window ──────────────────────────────────────────────────────────

if os.environ.get("CI"):
    import wx  # noqa: F401
else:
    pytest.importorskip("wx")

import ghviewer  # noqa: E402

Frame = ghviewer.GhViewerFrame


class RepoList:
    def __init__(self, data):
        self.data = data

    def GetSelection(self): return 0
    def GetClientData(self, i): return self.data


def _frame(view, item=None, pane=1, repo="o/open", listed="o/listed"):
    f = SimpleNamespace(view_mode=view, repo=repo, repo_list=RepoList(listed), announced=[])
    f._pane_index = lambda w: pane
    f._current_focus = lambda: None
    f._focused_item = lambda: item
    f._announce = f.announced.append
    f._repo_in_front = lambda: Frame._repo_in_front(f)
    f._repo_in_front_from = lambda: Frame._repo_in_front_from(f)
    return f


def test_watch_target_is_the_open_repo():
    assert Frame._watch_target(_frame(ghviewer.VIEW_BRANCHES)) == "o/open"


def test_watch_target_from_the_repo_list():
    assert Frame._watch_target(_frame(ghviewer.VIEW_BRANCHES, pane=0)) == "o/listed"


def test_watch_target_from_starred():
    star = gh_data.RepoEntry("o/star")
    assert Frame._watch_target(_frame(ghviewer.VIEW_STARRED, star)) == "o/star"


def test_no_watch_target_in_activity_with_nothing_selected():
    assert Frame._watch_target(_frame(ghviewer.VIEW_ACTIVITY)) is None


def test_a_category_entry_is_not_a_target():
    f = _frame(ghviewer.VIEW_ACTIVITY, pane=0, listed=ghviewer.ACTIVITY_ENTRY)
    assert Frame._watch_target(f) is None


def test_one_account_says_how_to_add_another(monkeypatch):
    shown = []
    monkeypatch.setattr(ghviewer.wx, "MessageBox", lambda msg, *a, **k: shown.append(msg))
    f = _frame(ghviewer.VIEW_ISSUES)
    Frame._choose_account(f, [gh_data.Account("me", active=True)])
    assert "gh auth login" in shown[0]
    assert f.announced == ["Only one account: me."]


def test_after_switching_everything_of_the_old_account_goes(monkeypatch):
    monkeypatch.setattr(ghviewer.wx, "CallLater", lambda *a: None)
    events = []
    f = SimpleNamespace(
        repo="o/r", _return_to=("x",), _pending_target=(1, "v", "k", "r"),
        _issue_drafts={"o/r": ("t", "b")}, _category_counts={"x": 1},
        view_mode=ghviewer.VIEW_ISSUES, current_limit=200, page_size=100, _account_gen=0,
    )
    f._load_repos = lambda: events.append("repos")
    f._switch_view = lambda v: events.append(("switch", v))
    f._update_title = lambda: None
    f._announce = lambda m: None
    Frame._on_account_switched(f, "work")
    assert f.repo is None and f._return_to is None and f._pending_target is None
    assert f._issue_drafts == {} and f._category_counts == {}
    assert events == ["repos", ("switch", ghviewer.VIEW_NOTIFICATIONS)]
    assert f._account_gen == 1
