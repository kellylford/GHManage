"""Tests for scripts/build_user_guide.py, the GitHub Pages build of the guide.

Everything but the last few tests runs without pandoc. Those that need it skip
when it is not installed.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "USER-GUIDE.md"

_spec = importlib.util.spec_from_file_location(
    "build_user_guide", ROOT / "scripts" / "build_user_guide.py")
bug = importlib.util.module_from_spec(_spec)
sys.modules["build_user_guide"] = bug  # dataclasses look the module up
_spec.loader.exec_module(bug)

needs_pandoc = pytest.mark.skipif(shutil.which("pandoc") is None,
                                  reason="pandoc is not installed")


def guide_text() -> str:
    return GUIDE.read_text(encoding="utf-8")


# ── Heading ids ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("text, expected", [
    ("The Main Window", "the-main-window"),
    ("List Mode, Sorting and Columns", "list-mode-sorting-and-columns"),
    ("Keys in the `Activity` view", "keys-in-the-activity-view"),
    ("★ Favorites", "favorites"),
    ("📌 Pinned — and starred", "pinned-and-starred"),
    ("**Bold** and *italic*", "bold-and-italic"),
    ("A [link](https://example.com) here", "a-link-here"),
    ("Version 1.2 notes", "version-1.2-notes"),
    ("3 things", "things"),
    ("snake_case and kebab-case", "snake_case-and-kebab-case"),
    ("What's new?", "whats-new"),
    ("!!!", "section"),
])
def test_pandoc_id(text, expected):
    assert bug.pandoc_id(text) == expected


def test_heading_ids_number_duplicates_like_pandoc():
    md = "# Guide\n\n## Keys\n\n### Keys\n\n## Keys\n"
    assert [i for _, _, i in bug.heading_ids(md)] == ["guide", "keys", "keys-1", "keys-2"]


def test_heading_ids_ignore_code_fences_and_honour_explicit_ids():
    md = "## Real\n\n```\n## not a heading\n```\n\n## Named {#chosen}\n"
    assert bug.heading_ids(md) == [(2, "Real", "real"), (2, "Named", "chosen")]


# ── Splitting into pages ────────────────────────────────────────────────


SAMPLE = """# Sample Guide

Intro.

---

## Contents

- [Alpha](#alpha)
- [Beta, Gamma](#beta-gamma)

---

## Alpha

See [the detail](#detail) and [the top](#alpha) and [Beta](#beta-gamma).

### Detail

Text.

```
## not a section
```

---

## Beta, Gamma

Back to [Alpha's detail](#detail) or the [contents](#contents).

---
"""


def test_split_guide_skips_contents_and_slugs_titles():
    preamble, sections = bug.split_guide(SAMPLE)
    assert "Intro." in preamble
    assert [(s.title, s.filename) for s in sections] == [
        ("Alpha", "alpha.html"), ("Beta, Gamma", "beta-gamma.html")]
    assert "## not a section" in sections[0].body


def test_page_slug_matches_quickmail():
    assert bug.page_slug("Signing In with the GitHub CLI") == "signing-in-with-the-github-cli"
    assert bug.page_slug("List Mode, Sorting and Columns") == "list-mode-sorting-and-columns"


def test_split_guide_refuses_a_section_that_would_overwrite_a_page():
    with pytest.raises(ValueError, match="index.html"):
        bug.split_guide("## Index\n\nx\n")
    with pytest.raises(ValueError, match="both make"):
        bug.split_guide("## Same\n\n## Same!\n")


def test_anchor_pages_maps_each_heading_to_its_page():
    _, sections = bug.split_guide(SAMPLE)
    pages = bug.anchor_pages(SAMPLE, sections)
    assert pages == {
        "sample-guide": "index.html",
        "contents": "index.html",
        "alpha": "alpha.html",
        "detail": "alpha.html",
        "beta-gamma": "beta-gamma.html",
    }


def test_rewrite_anchors_points_cross_section_links_at_the_other_page():
    _, sections = bug.split_guide(SAMPLE)
    pages = bug.anchor_pages(SAMPLE, sections)
    alpha = bug.section_markdown(sections[0], pages)
    # Same page: left alone. Another section's top: just its page.
    assert "[the detail](#detail)" in alpha
    assert "[the top](#alpha)" in alpha
    assert "[Beta](beta-gamma.html)" in alpha
    beta = bug.section_markdown(sections[1], pages)
    # A heading inside another section: that page, at that heading.
    assert "[Alpha's detail](alpha.html#detail)" in beta
    # Contents is the index page on the web.
    assert "[contents](index.html)" in beta


def test_rewrite_anchors_rejects_a_link_to_no_heading():
    with pytest.raises(ValueError, match="#nowhere"):
        bug.rewrite_anchors("[x](#nowhere)", "a.html", {"here": "a.html"})


def test_rewrite_anchors_leaves_other_links_alone():
    md = "[site](https://example.com/#frag) and [page](other.html#x)"
    assert bug.rewrite_anchors(md, "a.html", {}) == md


def test_section_markdown_makes_the_title_h1_and_promotes_subheadings():
    _, sections = bug.split_guide(SAMPLE)
    md = bug.section_markdown(sections[0], bug.anchor_pages(SAMPLE, sections))
    assert md.startswith("# Alpha\n")
    assert "\n## Detail\n" in md
    assert "## not a section" in md        # code is not a heading
    assert not md.rstrip().endswith("---")  # the separator to the next section


def test_nav_links_first_middle_last():
    sections = [bug.Section(t, "", bug.page_slug(t)) for t in ("One", "Two", "Three")]
    assert bug.nav_links(sections, 0) == [
        ("Contents", "index.html", ""), ("Single Page", "full.html", ""),
        ("Next: Two", "two.html", "next")]
    assert bug.nav_links(sections, 1)[2:] == [
        ("Previous: One", "one.html", "prev"), ("Next: Three", "three.html", "next")]
    assert bug.nav_links(sections, 2)[2:] == [("Previous: Two", "two.html", "prev")]


# ── Page markup ─────────────────────────────────────────────────────────


def test_page_has_landmarks_skip_link_and_title():
    out = bug.page("Labels - GHManage User Guide", "<h1>Labels</h1>",
                   [("Contents", "index.html", ""), ("Next: X", "x.html", "next")])
    assert '<html lang="en">' in out
    assert "<title>Labels - GHManage User Guide</title>" in out
    assert '<a class="skip" href="#content">Skip to content</a>' in out
    assert '<main id="content">' in out
    assert '<nav aria-label="Guide">' in out
    assert out.count("<nav ") == 2
    assert '<a href="x.html" rel="next">Next: X</a>' in out
    assert "prefers-color-scheme: dark" in out


def test_add_header_scope_marks_only_header_row_cells():
    table = ("<table><thead><tr><th>Key</th><th style=\"x\">Action</th></tr></thead>"
             "<tbody><tr><td>F</td><th>odd</th></tr></tbody></table>")
    out = bug.add_header_scope(table)
    assert out.count('scope="col"') == 2
    assert "<td>F</td><th>odd</th>" in out


def test_check_links_reports_missing_pages_and_anchors(tmp_path):
    (tmp_path / "a.html").write_text(
        '<a href="b.html#here">ok</a><a href="b.html#gone">x</a>'
        '<a href="c.html">x</a><a href="#self">x</a><a href="https://x.org/#y">ok</a>',
        encoding="utf-8")
    (tmp_path / "b.html").write_text('<h2 id="here">H</h2>', encoding="utf-8")
    broken = bug.check_links(str(tmp_path))
    assert broken == ["a.html: b.html#gone (no #gone on b.html)",
                      "a.html: c.html (no page c.html)",
                      "a.html: #self (no #self on a.html)"]


# ── Release history ─────────────────────────────────────────────────────


def test_parse_tag_dates_keeps_version_tags_newest_first():
    out = "v0.8.9\t2026-09-01\nv0.8.10\t2026-09-20\nnightly\t2026-09-21\nv0.1.0\t2026-07-09\n"
    assert bug.parse_tag_dates(out) == [
        ("0.8.10", date(2026, 9, 20)), ("0.8.9", date(2026, 9, 1)),
        ("0.1.0", date(2026, 7, 9))]


def test_notes_versions_reads_only_notes_files():
    names = ["release-notes-v0.8.2.md", "release-notes-v0.10.0.md", "USER-GUIDE.md",
             "release-notes-vX.md", "release-notes-v0.9.0.md.bak"]
    assert bug.notes_versions(names) == ["0.8.2", "0.10.0"]


def test_strip_trailing_footers_keeps_the_body_and_a_leading_download_table():
    md = ("# GHManage 1.0\n\n## Download\n\ntable\n\n## New\n\nstuff\n\n"
          "## Before you start\n\ngh\n\n## Downloads\n\nfiles\n\n## Requirements\n\nwin\n")
    out = bug.strip_trailing_footers(md)
    assert "## Download\n" in out and "## New" in out and "stuff" in out
    assert "Before you start" not in out and "## Downloads" not in out
    assert "Requirements" not in out


def test_every_tag_has_release_notes():
    """A released version missing its notes fails the publish; catch it here first."""
    try:
        out = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)\t%(creatordate:short)",
             "refs/tags"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    releases = bug.parse_tag_dates(out)
    if not releases:
        pytest.skip("no tags in this checkout (a shallow CI clone)")
    have = set(bug.notes_versions([p.name for p in (ROOT / "docs").iterdir()]))
    assert [v for v, _ in releases if v not in have] == []


# ── The guide itself ────────────────────────────────────────────────────


def test_every_anchor_link_in_the_guide_resolves():
    text = guide_text()
    ids = {i for _, _, i in bug.heading_ids(text)}
    links = re.findall(r"\]\(#([^)\s]+)\)", text)
    assert links, "expected the guide to link between sections"
    assert sorted(set(links) - ids) == []


def test_guide_heading_ids_are_unique():
    """A repeated heading gets "-1" in the full page but not on its own page,
    which would make the same link mean different places."""
    text = guide_text()
    bases = [bug.pandoc_id(t) for _, t, _ in bug.heading_ids(text)]
    assert sorted({b for b in bases if bases.count(b) > 1}) == []


def test_guide_contents_lists_every_section_in_order():
    text = guide_text()
    _, sections = bug.split_guide(text)
    contents = text.split("## Contents", 1)[1].split("\n---", 1)[0]
    listed = re.findall(r"^- \[([^\]]+)\]\(#([^)]+)\)", contents, flags=re.MULTILINE)
    assert [t for t, _ in listed] == [s.title for s in sections]
    assert [a for _, a in listed] == [bug.pandoc_id(s.title) for s in sections]


def test_guide_sections_all_build_without_pandoc():
    text = guide_text()
    _, sections = bug.split_guide(text)
    pages = bug.anchor_pages(text, sections)
    for section in sections:
        bug.section_markdown(section, pages)  # raises on a broken link


# ── With pandoc ─────────────────────────────────────────────────────────


@needs_pandoc
def test_pandoc_id_matches_pandoc_for_every_guide_heading():
    text = guide_text()
    html_out = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "html5"], input=text,
        capture_output=True, text=True, encoding="utf-8", check=True).stdout
    pandoc_ids = re.findall(r"<h[1-6] id=\"([^\"]+)\"", html_out)
    assert pandoc_ids == [i for _, _, i in bug.heading_ids(text)]


@needs_pandoc
def test_build_guide_writes_linked_pages(tmp_path):
    names = bug.build_guide(guide_text(), str(tmp_path), "9.9.9")
    _, sections = bug.split_guide(guide_text())
    assert set(names) == {"full.html", "index.html"} | {s.filename for s in sections}
    # releases.html is written by the release-history half of the build.
    (tmp_path / "releases.html").write_text("<p>stub</p>", encoding="utf-8")
    assert bug.check_links(str(tmp_path)) == []
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Version 9.9.9" in index
    first = (tmp_path / sections[0].filename).read_text(encoding="utf-8")
    assert f"<h1 id=\"{bug.pandoc_id(sections[0].title)}\">" in first
    assert "<h3" not in first or "<h2" in first   # no skipped heading level
    shortcuts = (tmp_path / "keyboard-shortcuts.html").read_text(encoding="utf-8")
    assert '<th scope="col"' in shortcuts
