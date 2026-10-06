"""Actions ▸ Copy: what each kind of item puts on the clipboard."""

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
from gh_data import (  # noqa: E402
    ActivityEvent, Artifact, Branch, Commit, Item, Label, PagesBuild, PagesFile,
    Release, ReleaseAsset, RepoEntry, Tag, Workflow, WorkflowRun,
)

Frame = ghviewer.GhViewerFrame
copy_values = ghviewer.copy_values
URL = "https://github.com/o/r/issues/12"


def test_issue_values():
    v = copy_values(Item(12, "Fix the thing", "open", URL, False))
    assert v.link == URL
    assert v.ident == "#12"
    assert v.ident_noun == "Number"
    assert v.title == "Fix the thing"
    assert v.markdown == f"[#12 Fix the thing]({URL})"


def test_markdown_escapes_brackets_in_the_title():
    v = copy_values(Item(3, r"Crash in [parser] \ lexer", "open", URL, False))
    assert v.markdown == rf"[#3 Crash in \[parser\] \\ lexer]({URL})"


def test_commit_copies_the_full_sha_and_first_line():
    c = Commit("a" * 40, "aaaaaaa", "Fix it\n\nLong body", "me", "", url="u")
    v = copy_values(c)
    assert v.ident == "a" * 40
    assert v.ident_noun == "SHA"
    assert v.title == "Fix it"
    assert v.markdown == "[aaaaaaa Fix it](u)"


def test_release_text_names_tag_and_title_once_each():
    assert copy_values(Release("v1", "One", False, False, "", url="u")).markdown == "[v1 One](u)"
    assert copy_values(Release("v1", "v1", False, False, "", url="u")).markdown == "[v1](u)"
    assert copy_values(Release("v1", "", False, False, "", url="u")).title == "v1"


def test_artifact_has_no_link_so_no_markdown():
    v = copy_values(Artifact(1, "build", 10, False, "", 9))
    assert v.link == ""
    assert v.markdown == ""
    assert v.ident == "build"


@pytest.mark.parametrize("item, ident, noun", [
    (Branch("main", "s", "m", "a", "d", url="u"), "main", "Branch Name"),
    (Tag("v2", "s", url="u"), "v2", "Tag"),
    (ReleaseAsset(1, "a.exe", 1, 1, "", url="u"), "a.exe", "File Name"),
    (Workflow(1, "CI", ".github/workflows/ci.yml", "active", url="u"),
     ".github/workflows/ci.yml", "File Path"),
    (WorkflowRun("CI", "completed", "success", "main", "push", "", url="u",
                 run_number=4, run_id=99), "99", "Run ID"),
    (Label("bug", url="u"), "bug", "Label Name"),
    (PagesBuild(1, "built", "abc123", "me", "", url="u"), "abc123", "Commit"),
    (PagesFile("docs/index.md", "u"), "docs/index.md", "Path"),
    (RepoEntry("o/r", url="u"), "o/r", "Repository Name"),
    (FavoriteEntry("o/r", "issue", "u", "#4 — T"), "#4 — T", "Name"),
], ids=lambda x: type(x).__name__ if not isinstance(x, str) else "")
def test_ident_per_kind(item, ident, noun):
    v = copy_values(item)
    assert (v.ident, v.ident_noun) == (ident, noun)
    assert v.link == "u"


def test_every_view_noun_matches_its_items():
    # The menu label is chosen by view, the copied value by item; they
    # must name the same thing.
    nouns = Frame._COPY_IDENT_NOUNS
    assert nouns[ghviewer.VIEW_ISSUES] == "Number"
    assert nouns[ghviewer.VIEW_COMMITS] == "SHA"
    assert nouns[ghviewer.VIEW_WORKFLOW] == "Run ID"
    assert set(nouns) == set(ghviewer.VIEW_COLUMNS)


def test_activity_event_about_an_issue_copies_the_issue():
    ev = ActivityEvent("IssuesEvent", "bob", "o/r", "opened issue #7", title="Bug",
                       url="https://github.com/o/r/issues/7#c", subject_kind="issue",
                       number=7, subject_url="https://github.com/o/r/issues/7")
    v = copy_values(ev)
    assert v.link == "https://github.com/o/r/issues/7"
    assert v.ident == "#7"
    assert v.markdown == "[#7 Bug](https://github.com/o/r/issues/7)"


def test_activity_event_about_a_repo_copies_the_repo():
    ev = ActivityEvent("WatchEvent", "bob", "o/r", "starred", url="https://github.com/o/r")
    v = copy_values(ev)
    assert v.ident == "o/r"
    assert v.ident_noun == "Repository Name"
    assert v.markdown == "[bob starred o/r](https://github.com/o/r)"


def test_unknown_item_gives_none():
    assert copy_values(object()) is None


def test_repo_copy_values():
    v = ghviewer.repo_copy_values("o/r")
    assert v.link == "https://github.com/o/r"
    assert v.markdown == "[o/r](https://github.com/o/r)"


# ── The command itself ────────────────────────────────────────────────


class FakeText:
    def __init__(self, value=""):
        self.value = value

    def GetValue(self):
        return self.value


def _frame(item=None, details="", focus=None):
    announced: list[str] = []
    clipboard: list[str] = []
    frame = SimpleNamespace(
        details_text=FakeText(details),
        repo_list=object(),
        _announce=announced.append,
        announced=announced,
        clipboard=clipboard,
        _focused_item=lambda: item,
        _current_focus=lambda: focus,
        _set_clipboard=lambda text: clipboard.append(text) or True,
        _COPY_WHAT=Frame._COPY_WHAT,
    )
    frame._copy_target = lambda: Frame._copy_target(frame)
    return frame


@pytest.mark.parametrize("what, expected", [
    ("link", URL),
    ("markdown", f"[#12 Fix]({URL})"),
    ("title", "Fix"),
    ("ident", "#12"),
])
def test_copy_puts_the_value_on_the_clipboard(what, expected):
    f = _frame(Item(12, "Fix", "open", URL, False))
    Frame._copy(f, what)
    assert f.clipboard == [expected]
    assert expected in f.announced[-1]


def test_copy_details_copies_the_panel():
    f = _frame(details="All of it\nline two")
    Frame._copy(f, "details")
    assert f.clipboard == ["All of it\nline two"]
    assert f.announced[-1] == "Copied details."


def test_copy_with_nothing_selected_says_so():
    f = _frame(None)
    Frame._copy(f, "link")
    assert f.clipboard == []
    assert f.announced == ["Nothing selected to copy."]


def test_copy_link_of_an_artifact_says_there_is_none():
    f = _frame(Artifact(1, "build", 10, False, "", 9))
    Frame._copy(f, "link")
    assert f.clipboard == []
    assert f.announced == ["This item has no link to copy."]


def test_copy_from_the_repo_list_copies_the_repository():
    class RepoList:
        def GetSelection(self): return 2
        def GetClientData(self, i): return "o/r"
    rl = RepoList()
    f = _frame(Item(12, "Fix", "open", URL, False), focus=rl)
    f.repo_list = rl
    Frame._copy(f, "link")
    assert f.clipboard == ["https://github.com/o/r"]


def test_copy_from_a_category_entry_copies_nothing():
    class RepoList:
        def GetSelection(self): return 0
        def GetClientData(self, i): return ghviewer.FAVORITES_ENTRY
    rl = RepoList()
    f = _frame(focus=rl)
    f.repo_list = rl
    Frame._copy(f, "link")
    assert f.clipboard == []
