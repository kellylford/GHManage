"""GitHub Pages: site config, publish history, and the pages a site serves."""

from __future__ import annotations

import pytest

import gh_data
from gh_data import GhError, PagesSite


# ── Site ───────────────────────────────────────────────────────────────


def test_fetch_pages_site(fake_gh):
    fake_gh.route("/pages", {"html_url": "https://o.github.io/r/", "status": None,
                             "source": {"branch": "main", "path": "/docs"},
                             "build_type": "workflow", "https_enforced": True,
                             "cname": None, "public": False})
    site = gh_data.fetch_pages_site("o/r")
    assert site.url == "https://o.github.io/r/"
    assert site.source_path == "/docs" and site.built_by_actions
    assert site.status_display == "built by Actions"
    assert site.cname == "" and site.public is False


def test_pages_disabled_is_none(fake_gh):
    fake_gh.route("/pages", GhError("HTTP 404: Not Found"))
    assert gh_data.fetch_pages_site("o/r") is None


def test_pages_other_errors_propagate(fake_gh):
    fake_gh.route("/pages", GhError("HTTP 403"))
    with pytest.raises(GhError):
        gh_data.fetch_pages_site("o/r")


def test_status_display():
    assert PagesSite(url="u", status="errored").status_display == "errored"
    assert PagesSite(url="u").status_display == "unknown"


# ── Publish history ────────────────────────────────────────────────────


@pytest.mark.parametrize("url, build_id", [
    ("https://api.github.com/repos/o/r/pages/builds/12345", 12345),
    ("https://api.github.com/repos/o/r/pages/builds/12345/", 12345),
    ("https://api.github.com/repos/o/r/pages/builds/latest", 0),
    ("", 0),
    (None, 0),
])
def test_build_id_from_url(url, build_id):
    assert gh_data._build_id_from_url(url) == build_id


def test_legacy_builds_are_used_when_present(fake_gh):
    fake_gh.route("pages/builds", [{"url": "https://api/x/builds/7", "status": "built",
                                    "commit": "e" * 40, "pusher": "me", "created": "2026-01-01T10:20:30Z",
                                    "duration": 4500, "error": None}])
    [b] = gh_data.fetch_pages_builds("o/r")
    assert (b.id, b.kind, b.error) == (7, "build", "")
    assert b.url == f"https://github.com/o/r/commit/{'e' * 40}"
    assert b.to_row(["date", "duration", "commit"]) == {
        "date": "2026-01-01 10:20", "duration": "4s", "commit": "e" * 8}
    # Never merged with deployments, which would list each publish twice
    assert fake_gh.called_with("deployments") == []


def test_actions_site_falls_back_to_deployments(fake_gh):
    fake_gh.route("pages/builds", [])
    fake_gh.route("deployments/1/statuses", ["success"])
    fake_gh.route("deployments/2/statuses", GhError("boom"))
    fake_gh.route("environment=github-pages", [
        {"id": 1, "sha": "a1", "creator": "bot", "created": "2026-02-01"},
        {"id": 2, "sha": "b2", "creator": "bot", "created": "2026-01-01"},
        "junk",
    ])
    first, second = gh_data.fetch_pages_builds("o/r")
    assert (first.status, first.kind, first.duration_human()) == ("success", "deployment", "")
    assert second.status == "unknown"


def test_pages_history_404_is_empty(fake_gh):
    fake_gh.route("pages/builds", GhError("HTTP 404"))
    fake_gh.route("deployments", GhError("HTTP 404"))
    assert gh_data.fetch_pages_builds("o/r") == []


# ── Served pages ───────────────────────────────────────────────────────


@pytest.mark.parametrize("path, hidden", [
    ("index.md", False),
    ("_posts/2026-01-01-hi.md", True),
    ("docs/_includes/head.html", True),
    ("_config.yml", True),
    ("sub/Gemfile", True),
    ("assets/site.css", False),
])
def test_jekyll_hides(path, hidden):
    assert gh_data._jekyll_hides(path) is hidden


@pytest.mark.parametrize("path, jekyll, served", [
    ("guide/setup.md", True, "guide/setup.html"),
    ("notes.markdown", True, "notes.html"),
    ("guide/setup.md", False, "guide/setup.md"),
    ("page.html", True, "page.html"),
])
def test_served_as(path, jekyll, served):
    assert gh_data._served_as(path, jekyll) == served


def _tree(*paths):
    return [{"path": p, "size": 10} for p in paths]


def test_pages_files_for_jekyll_site_in_docs(fake_gh):
    site = PagesSite(url="https://o.github.io/r", source_branch="main", source_path="/docs")
    fake_gh.route("git/trees/main", _tree(
        "README.md", "docs/index.md", "docs/_config.yml", "docs/_layouts/x.html",
        "docs/Guide/b.md", "docs/a.css", "docsy/other.md",
    ))
    files = gh_data.fetch_pages_files("o/r", site)
    assert [(f.path, f.url) for f in files] == [
        ("a.css", "https://o.github.io/r/a.css"),
        ("Guide/b.md", "https://o.github.io/r/Guide/b.html"),
        ("index.md", "https://o.github.io/r/index.html"),
    ]


def test_nojekyll_serves_files_as_committed(fake_gh):
    site = PagesSite(url="https://o.github.io/r/", source_branch="gh-pages")
    fake_gh.route("git/trees/gh-pages", _tree(".nojekyll", "_app/x.js", "index.md"))
    files = gh_data.fetch_pages_files("o/r", site)
    assert [f.url for f in files] == [
        "https://o.github.io/r/.nojekyll",
        "https://o.github.io/r/_app/x.js",
        "https://o.github.io/r/index.md",
    ]


def test_actions_site_lists_source_without_jekyll(fake_gh):
    site = PagesSite(url="https://s/", source_branch="main", build_type="workflow")
    fake_gh.route("git/trees/main", _tree("_site/x.md"))
    [f] = gh_data.fetch_pages_files("o/r", site)
    assert f.url == "https://s/_site/x.md"


def test_pages_files_limit_and_missing_site(fake_gh):
    site = PagesSite(url="https://s/", source_branch="main")
    fake_gh.route("git/trees/main", _tree(*(f"p{i}.html" for i in range(10))))
    assert len(gh_data.fetch_pages_files("o/r", site, limit=3)) == 3
    assert gh_data.fetch_pages_files("o/r", None) == []
    assert gh_data.fetch_pages_files("o/r", PagesSite(url="u")) == []
