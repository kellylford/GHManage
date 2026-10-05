"""Branches, commits, tags, releases, workflows and compare — the `gh api` views."""

from __future__ import annotations

import pytest

import gh_data
from gh_data import GhError


def test_api_substitutes_repo_into_endpoint(fake_gh):
    fake_gh.route("api", "[]")
    gh_data._api(["repos/{owner}/{repo}/tags", "-q", "."], "o/r")
    assert fake_gh.calls[-1] == ["api", "repos/o/r/tags", "-q", "."]


def test_api_without_repo_leaves_placeholders_for_gh(fake_gh):
    fake_gh.route("api", "[]")
    gh_data._api(["repos/{owner}/{repo}/tags"], None)
    assert fake_gh.calls[-1] == ["api", "repos/{owner}/{repo}/tags"]


def test_api_json_empty_output_is_empty_list(fake_gh):
    fake_gh.route("api", "  ")
    assert gh_data._api_json(["x"], "o/r") == []


# ── Branches ───────────────────────────────────────────────────────────


def test_fetch_branches_joins_commit_info_in_order(fake_gh):
    fake_gh.route("/branches", [
        {"name": "main", "sha": "a" * 40, "protected": True},
        {"name": "dev", "sha": "b" * 40},
        {"name": "orphan", "sha": ""},
    ])
    fake_gh.route("commits/" + "a" * 40, {"message": "main tip", "author": "A", "date": "2026-01-01"})
    fake_gh.route("commits/" + "b" * 40, GhError("gone"))
    main, dev, orphan = gh_data.fetch_branches("o/r")
    assert (main.name, main.commit_sha, main.commit_message, main.protected) == (
        "main", "a" * 8, "main tip", True)
    assert main.url == "https://github.com/o/r/tree/main"
    # A failed commit lookup leaves the branch listed, just without details
    assert dev.commit_message == "" and dev.commit_sha == "b" * 8
    assert orphan.commit_sha == ""
    # No lookup is made for a branch without a sha
    assert len(fake_gh.called_with("/commits/")) == 2


def test_fetch_branches_without_repo_has_no_url(fake_gh):
    fake_gh.route("/branches", [{"name": "main", "sha": ""}])
    [b] = gh_data.fetch_branches(None)
    assert b.url == ""


def test_fetch_branches_non_list_is_empty(fake_gh):
    fake_gh.route("/branches", {"message": "weird"})
    assert gh_data.fetch_branches("o/r") == []


def test_branch_row_truncates_message():
    b = gh_data.Branch("x", "sha", "m" * 100, "who", "2026-01-02T00:00:00Z", ahead=2)
    row = b.to_row(["last commit", "date", "ahead", "behind"])
    assert len(row["last commit"]) == 60
    assert row["date"] == "2026-01-02"
    assert row["ahead"] == "2" and row["behind"] == ""


# ── Commits ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("branch, endpoint", [
    ("", "repos/o/r/commits?per_page=20"),
    ("dev", "repos/o/r/commits?sha=dev&per_page=20"),
])
def test_fetch_commits_endpoint(fake_gh, branch, endpoint):
    fake_gh.route("commits", [])
    gh_data.fetch_commits("o/r", branch=branch, limit=20)
    assert fake_gh.calls[-1][1] == endpoint


def test_fetch_commits_keeps_first_line_only(fake_gh):
    fake_gh.route("commits", [{"sha": "c" * 40, "message": "Subject\n\nBody", "author": "A",
                               "date": "d", "url": "https://x"}])
    [c] = gh_data.fetch_commits("o/r")
    assert c.message == "Subject" and c.short_sha == "c" * 8 and c.url == "https://x"


def test_fetch_commit_detail(fake_gh):
    fake_gh.route("commits/abc", {"sha": "abcdef0123", "message": "M\n\nfull", "additions": 3,
                                  "deletions": 1, "files": [{"filename": "a"}, {"filename": "b"}]})
    c = gh_data.fetch_commit_detail("o/r", "abc")
    assert c.message == "M\n\nfull"          # detail keeps the whole message
    assert c.short_sha == "abcdef01" and c.files_changed == 2


def test_fetch_commit_detail_bad_payload(fake_gh):
    fake_gh.route("commits/abc", [])
    c = gh_data.fetch_commit_detail("o/r", "abc")
    assert c.sha == "abc" and c.message == ""


def test_commit_row():
    c = gh_data.Commit("s", "short", "msg", "me", "2026-03-04T00:00Z", additions=0, deletions=0)
    assert c.to_row(["sha", "+/-", "files"]) == {"sha": "short", "+/-": "", "files": ""}
    c.additions, c.files_changed = 4, 2
    assert c.to_row(["+/-", "files"]) == {"+/-": "+4/-0", "files": "2"}


# ── Tags ───────────────────────────────────────────────────────────────


def test_fetch_tags(fake_gh):
    fake_gh.route("tags", [{"name": "v1.0", "sha": "d" * 40}])
    [t] = gh_data.fetch_tags("o/r")
    assert (t.name, t.commit_sha) == ("v1.0", "d" * 8)
    assert t.url == "https://github.com/o/r/releases/tag/v1.0"


# ── Releases and assets ────────────────────────────────────────────────


@pytest.mark.parametrize("size, text", [
    (0, "0 B"),
    (1023, "1023 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (5 * 1024 ** 2, "5.0 MB"),
    (3 * 1024 ** 3, "3.0 GB"),
    (2048 * 1024 ** 3, "2048.0 GB"),     # GB is the ceiling
])
def test_size_human(size, text):
    assert gh_data._size_human(size) == text


def _asset(name, downloads, size=100):
    return {"id": hash(name) % 1000, "name": name, "size": size, "downloads": downloads,
            "updated": "2026-01-01T00:00:00Z", "url": f"https://dl/{name}"}


def test_fetch_releases_with_assets(fake_gh):
    fake_gh.route("releases", [{
        "tag": "v1", "name": "One", "draft": False, "prerelease": True, "created": "2026-01-01",
        "url": "https://rel", "body": None, "id": 42,
        "assets": [_asset("a.exe", 10), _asset("b.zip", 5)],
    }])
    [rel] = gh_data.fetch_releases("o/r")
    assert rel.body == "" and rel.id == 42 and rel.prerelease
    assert rel.downloads == 15
    assert [a.release_tag for a in rel.assets] == ["v1", "v1"]
    assert gh_data.total_downloads([rel, rel]) == 30


def test_parse_assets_skips_junk_and_nulls():
    assets = gh_data._parse_assets([_asset("x", None, size=None), "junk", None])
    assert len(assets) == 1
    assert assets[0].download_count == 0 and assets[0].size_bytes == 0
    assert gh_data._parse_assets(None) == []


def test_fetch_release_assets_most_downloaded_first(fake_gh):
    fake_gh.route("releases/7/assets", [_asset("low", 1), _asset("high", 99), _asset("mid", 50)])
    assets = gh_data.fetch_release_assets("o/r", 7, "v7")
    assert [a.name for a in assets] == ["high", "mid", "low"]
    assert all(a.release_tag == "v7" for a in assets)


def test_release_row():
    rel = gh_data.Release("v1", "One", draft=True, prerelease=False, created_at="2026-05-06T00:00Z",
                          assets=[gh_data.ReleaseAsset(1, "a", 1, 3, "")])
    assert rel.to_row(["draft", "date", "downloads", "assets"]) == {
        "draft": "Yes", "date": "2026-05-06", "downloads": "3", "assets": "1"}


# ── Workflows, runs, artifacts ─────────────────────────────────────────


def test_fetch_workflow_runs_null_conclusion_is_running(fake_gh):
    fake_gh.route("actions/runs", [{"name": "CI", "status": "in_progress", "conclusion": None,
                                    "branch": "main", "event": "push", "created": "2026-01-01",
                                    "number": 12, "id": 999}])
    [run] = gh_data.fetch_workflow_runs("o/r")
    assert run.conclusion == "" and run.run_id == 999
    assert run.to_row(["result", "#"]) == {"result": "(running)", "#": "12"}


def test_fetch_run_artifacts(fake_gh):
    fake_gh.route("runs/5/artifacts", [{"id": 1, "name": "dist", "size": 2048, "expired": True,
                                        "created": "2026-01-01"}])
    [art] = gh_data.fetch_run_artifacts("o/r", 5)
    assert art.run_id == 5 and art.size_human() == "2.0 KB"
    assert art.to_row(["expired"]) == {"expired": "Yes"}


def test_download_artifact_and_delete_run_commands(fake_gh):
    fake_gh.route("run ", "")
    gh_data.download_artifact("o/r", 5, "dist", r"C:\out")
    gh_data.delete_workflow_run(None, 6)
    assert fake_gh.calls == [
        ["run", "download", "5", "-n", "dist", "-D", r"C:\out", "-R", "o/r"],
        ["run", "delete", "6"],
    ]


def test_fetch_workflows(fake_gh):
    fake_gh.route("actions/workflows", [{"id": 3, "name": "Build", "path": ".github/workflows/b.yml",
                                         "state": "active", "url": "https://wf"}])
    [wf] = gh_data.fetch_workflows("o/r")
    assert (wf.id, wf.path, wf.url) == (3, ".github/workflows/b.yml", "https://wf")


# ── Manual workflow runs ───────────────────────────────────────────────


@pytest.mark.parametrize("yaml_text, supported", [
    ("on: workflow_dispatch\n", True),
    ("on: [push, workflow_dispatch]\n", True),
    ("on: [push]\n", False),
    ("on:\n  push:\n  workflow_dispatch:\n", True),
    ("on:\n  push:\n    branches: [main]\n", False),
    ("just a string", False),
    ("on: [unclosed\n  workflow_dispatch", True),    # unparseable: substring fallback
])
def test_dispatch_support(yaml_text, supported):
    spec = gh_data._parse_dispatch_spec(yaml_text)
    assert spec.supports_dispatch is supported
    assert spec.inputs == []


def test_dispatch_inputs_are_parsed_as_text():
    spec = gh_data._parse_dispatch_spec("""
on:
  workflow_dispatch:
    inputs:
      level:
        type: choice
        description: "  Log level  "
        options: [info, 2, debug]
        default: info
        required: true
      dry_run:
        type: boolean
        default: false
      count:
        type: number
        default: 3
      plain:
      empty_default:
        default: null
""")
    by_name = {i.name: i for i in spec.inputs}
    assert list(by_name) == ["level", "dry_run", "count", "plain", "empty_default"]
    assert by_name["level"].options == ["info", "2", "debug"]
    assert by_name["level"].required is True
    assert by_name["level"].label == "Log level"
    assert by_name["dry_run"].default == "false"
    assert by_name["count"].default == "3"
    assert by_name["plain"].type == "string" and by_name["plain"].label == "plain"
    assert by_name["empty_default"].default == ""


def test_fetch_dispatch_spec_fills_environment_choices(fake_gh):
    fake_gh.route("contents/", "on:\n  workflow_dispatch:\n    inputs:\n      env:\n        type: environment\n")
    fake_gh.route("environments", ["staging", "prod"])
    spec = gh_data.fetch_dispatch_spec("o/r", ".github/workflows/d.yml", ref="feature")
    assert spec.inputs[0].options == ["staging", "prod"]
    [contents_call] = fake_gh.called_with("contents/")
    assert contents_call[1].endswith("?ref=feature")


def test_fetch_dispatch_spec_skips_environment_lookup_when_not_needed(fake_gh):
    fake_gh.route("contents/", "on: workflow_dispatch\n")
    assert gh_data.workflow_supports_dispatch("o/r", "x.yml") is True
    assert fake_gh.called_with("environments") == []


def test_fetch_environments_unavailable_is_empty(fake_gh):
    fake_gh.route("environments", GhError("HTTP 404"))
    assert gh_data.fetch_environments("o/r") == []


def test_dispatch_workflow_sends_inputs(fake_gh):
    fake_gh.route("dispatches", "")
    gh_data.dispatch_workflow("o/r", 3, "main", {"level": "debug", "dry_run": "true"})
    call = fake_gh.calls[-1]
    assert "repos/o/r/actions/workflows/3/dispatches" in call
    fields = [call[i + 1] for i, a in enumerate(call) if a == "-f"]
    assert fields == ["ref=main", "inputs[level]=debug", "inputs[dry_run]=true"]


# ── Compare ────────────────────────────────────────────────────────────


def test_fetch_compare(fake_gh):
    fake_gh.route("compare/main...dev", {"ahead": 2, "behind": 1, "commits": [{"sha": "s"}], "files": []})
    result = gh_data.fetch_compare("o/r", "main", "dev")
    assert (result.ahead_by, result.behind_by, result.commits) == (2, 1, [{"sha": "s"}])
    # The slash before "compare" is required — the API 404s without it
    assert fake_gh.calls[-1][1] == "repos/o/r/compare/main...dev"


def test_fetch_compare_bad_payload(fake_gh):
    fake_gh.route("compare", [])
    result = gh_data.fetch_compare("o/r", "a", "b")
    assert (result.ahead_by, result.behind_by) == (0, 0)
