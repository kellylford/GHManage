#!/usr/bin/env python3
"""Build the GHManage user guide and release history for GitHub Pages.

    python scripts/build_user_guide.py --out build/docs --version 0.8.5

From docs/USER-GUIDE.md this writes:

- full.html            the whole guide on one page
- <section>.html       one page per "## " section, with Contents / Single Page /
                       Previous / Next links at the top and bottom
- index.html           the title page: version, a line about GHManage, the
                       section list, and links to the single page and releases

and from docs/release-notes-vX.Y.Z.md:

- release-notes-vX.Y.Z.html   one page per released version
- releases.html               every released version, newest first

The release history is driven by the repository's v* tags, not the files on
disk. A notes file with no tag is a version that has not shipped yet and is
left out; a tag with no notes file fails the build, because a released version
quietly missing from the history is the kind of gap nobody notices for months.

Splitting the guide into pages breaks every link from one section to a heading
in another: "#views" only resolves on the page that has that heading. Those
links are rewritten to "the-main-window.html#views". The anchors are the ids
pandoc gives headings by itself (its auto_identifiers extension), computed here
the same way so the rewriting, and the tests, need no pandoc.

Everything that decides structure is a pure function, tested in
tests/test_build_user_guide.py. Only render() and the file writing need pandoc.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser

GUIDE_TITLE = "GHManage User Guide"
DESCRIPTION = ("GHManage is a keyboard-driven desktop app for your GitHub repositories, "
               "built for screen reader users, on Windows and Apple Silicon Macs.")
REPO_URL = "https://github.com/TheIdeaPlace/GHManage"
RELEASE_TAG_URL = REPO_URL + "/releases/tag/"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

# Trailing sections every release-notes file repeats: how to install, the
# download table, the requirements. On the release's GitHub page they are
# useful; repeated on twenty-five history pages they bury what each release
# changed, and every history page links to its downloads anyway. Only a
# trailing run of them is dropped, so the early notes that open with a
# Download table keep it.
FOOTER_TITLES = {"download", "downloads", "install", "requirements", "updating",
                 "before you start", "reporting issues"}

# Page names the build writes itself; a guide section must not collide.
RESERVED_PAGES = {"index", "full", "releases"}


# ── Markdown structure (pure) ───────────────────────────────────────────


_FENCE = re.compile(r"^\s*(```|~~~)")
_ATX = re.compile(r"^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_EXPLICIT_ID = re.compile(r"\s*\{#([^}\s]+)[^}]*\}\s*$")


def _content_lines(markdown: str):
    """(line, inside_code_fence) for each line, so '#' in code is not a heading."""
    fenced = False
    for line in markdown.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            yield line, True
            continue
        yield line, fenced


def stringify(text: str) -> str:
    """Heading markdown as plain text, the way pandoc reads it for an id."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)   # links, images
    text = text.replace("`", "")
    text = re.sub(r"(\*\*|__|\*)", "", text)                 # emphasis markers
    return text


def pandoc_id(text: str) -> str:
    """The id pandoc's auto_identifiers gives a heading with this text.

    Pandoc lowercases, keeps letters, digits, '_', '-' and '.', turns each run
    of white space into one '-', and drops everything before the first letter.
    An id left empty becomes "section". Duplicates are numbered by
    heading_ids(), not here.
    """
    text = stringify(text).lower()
    kept = "".join(c for c in text if c.isalnum() or c in "_-." or c.isspace())
    ident = "-".join(kept.split())
    i = 0
    while i < len(ident) and not ident[i].isalpha():
        i += 1
    ident = ident[i:]
    return ident or "section"


def heading_ids(markdown: str) -> list[tuple[int, str, str]]:
    """Every ATX heading as (level, text, id), ids made unique as pandoc does."""
    used: set[str] = set()
    out = []
    for line, fenced in _content_lines(markdown):
        if fenced:
            continue
        m = _ATX.match(line)
        if not m:
            continue
        level, text = len(m.group(1)), m.group(2)
        explicit = _EXPLICIT_ID.search(text)
        if explicit:
            ident = explicit.group(1)
            text = text[:explicit.start()]
        else:
            base = pandoc_id(text)
            ident, n = base, 0
            while ident in used:
                n += 1
                ident = f"{base}-{n}"
        used.add(ident)
        out.append((level, text.strip(), ident))
    return out


def page_slug(title: str) -> str:
    """A section's page name, without .html: 'The Main Window' -> 'the-main-window'.

    The same rule QuickMail's guide uses, so the two sites name pages alike.
    """
    return re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")


@dataclass
class Section:
    title: str
    body: str     # everything after the "## " line, up to the next one
    slug: str

    @property
    def filename(self) -> str:
        return f"{self.slug}.html"


def split_guide(markdown: str) -> tuple[str, list[Section]]:
    """(text before the first '## ', [Section, ...]), the Contents section left out.

    Contents is the in-document list of anchor links; on the web it is the
    index page instead.
    """
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line, fenced in _content_lines(markdown):
        if not fenced and line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    result = []
    seen: dict[str, str] = {}
    for title, lines in sections:
        if title.lower() == "contents":
            continue
        slug = page_slug(title)
        if slug in RESERVED_PAGES or slug.startswith("release-notes-"):
            raise ValueError(f"Section '{title}' would overwrite the {slug}.html page")
        if slug in seen:
            raise ValueError(f"Sections '{seen[slug]}' and '{title}' both make {slug}.html")
        seen[slug] = title
        result.append(Section(title, "\n".join(lines), slug))
    return "\n".join(preamble), result


def anchor_pages(markdown: str, sections: list[Section]) -> dict[str, str]:
    """Map every heading id in the guide to the page it ends up on.

    The title and the Contents heading belong to index.html, which is what
    stands in for them on the web.
    """
    by_title = {s.title: s for s in sections}
    pages: dict[str, str] = {}
    current = "index.html"
    for level, text, ident in heading_ids(markdown):
        if level == 2:
            section = by_title.get(text)
            current = section.filename if section else "index.html"
        pages[ident] = current
    return pages


_ANCHOR_LINK = re.compile(r"\]\(#([^)\s]+)\)")


def rewrite_anchors(markdown: str, page: str, pages: dict[str, str]) -> str:
    """Point '](#id)' links at the page the heading is on, when it is another page.

    Raises ValueError naming any anchor that is no heading at all, so a broken
    link fails the build rather than shipping.
    """
    missing: list[str] = []

    def fix(m: re.Match) -> str:
        ident = m.group(1)
        target = pages.get(ident)
        if target is None:
            missing.append(ident)
            return m.group(0)
        if target == page:
            return m.group(0)
        if target == "index.html" or target == f"{ident}.html":
            # The page itself, not a place on it: no fragment to land past the nav.
            return f"]({target})"
        return f"]({target}#{ident})"

    out = _ANCHOR_LINK.sub(fix, markdown)
    if missing:
        raise ValueError("Links to headings that do not exist: "
                         + ", ".join(f"#{a}" for a in missing))
    return out


def promote_headings(markdown: str) -> str:
    """Raise every heading one level, outside code: '### x' -> '## x'.

    A section page's own title is its h1, so its subsections are h2, not h3.
    Skipping a level makes a screen reader's heading list look as though
    something is missing.
    """
    out = []
    for line, fenced in _content_lines(markdown):
        if not fenced and re.match(r"^#{2,6}[ \t]", line):
            line = line[1:]
        out.append(line)
    return "\n".join(out)


def section_markdown(section: Section, pages: dict[str, str]) -> str:
    """One section as a page of its own: its title as '# ', links rewritten."""
    body = promote_headings(section.body).strip("\n")
    # A section ends with the '---' that separated it from the next.
    body = re.sub(r"(?:\n\s*)*-{3,}\s*$", "", body)
    md = f"# {section.title}\n\n{body}\n"
    return rewrite_anchors(md, section.filename, pages)


def nav_links(sections: list[Section], index: int) -> list[tuple[str, str, str]]:
    """(label, href, rel) for a section page's navigation, rel '' when none."""
    links = [("Contents", "index.html", ""), ("Single Page", "full.html", "")]
    if index > 0:
        prev = sections[index - 1]
        links.append((f"Previous: {prev.title}", prev.filename, "prev"))
    if index < len(sections) - 1:
        nxt = sections[index + 1]
        links.append((f"Next: {nxt.title}", nxt.filename, "next"))
    return links


# ── Release notes (pure) ────────────────────────────────────────────────


def version_key(version: str) -> tuple[int, ...]:
    """'0.8.10' sorts after '0.8.9'."""
    return tuple(int(p) for p in version.split("."))


def parse_tag_dates(for_each_ref_output: str) -> list[tuple[str, date]]:
    """`git for-each-ref` lines of 'tag<TAB>YYYY-MM-DD' as (version, date), newest first.

    Only v-and-numbers tags count as releases.
    """
    found = []
    for line in for_each_ref_output.splitlines():
        if not line.strip():
            continue
        tag, _, when = line.partition("\t")
        if not re.fullmatch(r"v\d+(\.\d+)*", tag.strip()):
            continue
        y, m, d = (int(p) for p in when.strip().split("-"))
        found.append((tag.strip()[1:], date(y, m, d)))
    found.sort(key=lambda r: version_key(r[0]), reverse=True)
    return found


def notes_versions(filenames: list[str]) -> list[str]:
    """Versions that have a release-notes-vX.Y.Z.md among ``filenames``."""
    out = []
    for name in filenames:
        m = re.fullmatch(r"release-notes-v(\d+(?:\.\d+)*)\.md", name)
        if m:
            out.append(m.group(1))
    return sorted(out, key=version_key)


def split_h2(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """(text before the first '## ', [(title, whole section text), ...])."""
    parts = re.split(r"^(## .*)$", markdown, flags=re.MULTILINE)
    sections = [(parts[i][3:].strip(), parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
                for i in range(1, len(parts), 2)]
    return parts[0], sections


def strip_trailing_footers(markdown: str) -> str:
    """Drop the trailing install/download/requirements sections of a notes file."""
    preamble, sections = split_h2(markdown)
    while sections and sections[-1][0].lower() in FOOTER_TITLES:
        sections.pop()
    text = preamble + "".join(s for _, s in sections)
    text = re.sub(r"(?:\r?\n)+(?:---(?:\r?\n)+)+\Z", "\n", text)
    return text.rstrip() + "\n"


def long_date(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


# ── HTML ────────────────────────────────────────────────────────────────


CSS = """<style>
  :root {
    color-scheme: light dark;
    --bg: #ffffff; --fg: #1f2328; --muted: #57606a; --link: #0550ae;
    --rule: #d0d7de; --code-bg: #f3f4f6; --th-bg: #f6f8fa; --focus: #bc4c00;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0d1117; --fg: #e6edf3; --muted: #9da7b3; --link: #79c0ff;
      --rule: #3d444d; --code-bg: #161b22; --th-bg: #161b22; --focus: #ffa657;
    }
  }
  body { background: var(--bg); color: var(--fg); max-width: 50rem; margin: 0 auto;
         padding: 1rem 1.25rem 3rem; line-height: 1.6;
         font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  a { color: var(--link); text-decoration: underline; text-underline-offset: 0.15em; }
  a:focus-visible, :focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
  h1 { border-bottom: 2px solid var(--rule); padding-bottom: 0.3em; line-height: 1.25; }
  h2 { border-bottom: 1px solid var(--rule); padding-bottom: 0.2em; margin-top: 2em; }
  .table-wrap { overflow-x: auto; margin: 1em 0; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid var(--rule); padding: 0.45rem 0.7rem; text-align: left; vertical-align: top; }
  th { background: var(--th-bg); font-weight: 600; }
  code { background: var(--code-bg); padding: 0.1em 0.35em; border-radius: 4px; font-size: 0.9em;
         font-family: "Cascadia Code", Consolas, Menlo, monospace; }
  pre { background: var(--code-bg); padding: 1rem; border-radius: 6px; overflow-x: auto; }
  pre code { padding: 0; }
  hr { border: none; border-top: 1px solid var(--rule); margin: 2rem 0; }
  blockquote { border-left: 4px solid var(--rule); margin-left: 0; padding-left: 1rem; color: var(--muted); }
  .skip { position: absolute; left: -999rem; }
  .skip:focus { position: static; display: inline-block; margin-bottom: 0.5rem; }
  nav ul { list-style: none; padding: 0; margin: 0.5rem 0 1.5rem; display: flex; flex-wrap: wrap; gap: 0.25rem 1.25rem; }
  nav.bottom ul { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--rule); }
  .version { color: var(--muted); margin-top: -0.5em; }
</style>"""


def nav_html(links: list[tuple[str, str, str]], label: str, bottom: bool = False) -> str:
    items = "\n".join(
        f'    <li><a href="{html.escape(href)}"{f" rel={chr(34)}{rel}{chr(34)}" if rel else ""}>'
        f"{html.escape(text)}</a></li>"
        for text, href, rel in links)
    cls = ' class="bottom"' if bottom else ""
    return f'<nav aria-label="{html.escape(label)}"{cls}>\n  <ul>\n{items}\n  </ul>\n</nav>'


def page(title: str, body: str, nav: list[tuple[str, str, str]] | None = None,
         nav_label: str = "Guide") -> str:
    """A whole page: skip link, the nav top and bottom, the body in <main>."""
    top = nav_html(nav, nav_label) if nav else ""
    bottom = nav_html(nav, f"{nav_label}, end of page", bottom=True) if nav else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{CSS}
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
{top}
<main id="content">
{body}
</main>
{bottom}
</body>
</html>
"""


def add_header_scope(body: str) -> str:
    """scope="col" on the header cells of every table's header row.

    Each table also goes in a scrolling wrapper, so a wide one scrolls on a
    narrow screen. The wrapper scrolls, not the table: `display: block` on a
    table can strip its table semantics for some screen readers.
    """
    def fix(m: re.Match) -> str:
        return re.sub(r"<th(?=[\s>])(?![^>]*\bscope=)", '<th scope="col"', m.group(0))
    body = re.sub(r"<thead>.*?</thead>", fix, body, flags=re.DOTALL)
    return re.sub(r"(<table\b.*?</table>)", r'<div class="table-wrap">\1</div>',
                  body, flags=re.DOTALL)


def after_first_h1(body: str, extra: str) -> str:
    return re.sub(r"(</h1>)", lambda m: m.group(1) + "\n" + extra, body, count=1)


# ── Link check ──────────────────────────────────────────────────────────


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])


def check_links(out_dir: str) -> list[str]:
    """Every relative link between the pages in ``out_dir``, that does not resolve."""
    pages: dict[str, _LinkCollector] = {}
    for name in os.listdir(out_dir):
        if name.endswith(".html"):
            collector = _LinkCollector()
            with open(os.path.join(out_dir, name), encoding="utf-8") as f:
                collector.feed(f.read())
            pages[name] = collector
    broken = []
    for name, collector in sorted(pages.items()):
        for href in collector.hrefs:
            if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.IGNORECASE):
                continue  # https:, mailto: and the like
            target, _, frag = href.partition("#")
            target = target or name
            if target not in pages:
                broken.append(f"{name}: {href} (no page {target})")
            elif frag and frag not in pages[target].ids:
                broken.append(f"{name}: {href} (no #{frag} on {target})")
    return broken


# ── Pandoc and the build ────────────────────────────────────────────────


def render(markdown: str) -> str:
    """Markdown to an HTML fragment. Any pandoc warning fails the build."""
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise SystemExit("pandoc was not found on PATH.")
    result = subprocess.run(
        [pandoc, "--from", "markdown", "--to", "html5", "--fail-if-warnings"],
        input=markdown, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 or result.stderr.strip():
        raise SystemExit(f"pandoc failed:\n{result.stderr}")
    return add_header_scope(result.stdout)


def write(out_dir: str, name: str, content: str) -> None:
    with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def build_guide(guide_md: str, out_dir: str, version: str) -> list[str]:
    """Write full.html, index.html and the section pages. Returns the page names."""
    _, sections = split_guide(guide_md)
    pages = anchor_pages(guide_md, sections)
    # Fails on a link to no heading, before anything is written.
    for section in sections:
        section_markdown(section, pages)
    rewrite_anchors(guide_md, "full.html", {k: "full.html" for k in pages})

    version_line = f'<p class="version">Version {html.escape(version)}</p>'
    written = []

    full = after_first_h1(render(guide_md), version_line)
    write(out_dir, "full.html", page(
        GUIDE_TITLE, full,
        [("Contents", "index.html", ""), ("All release notes", "releases.html", "")]))
    written.append("full.html")

    for i, section in enumerate(sections):
        body = render(section_markdown(section, pages))
        write(out_dir, section.filename,
              page(f"{section.title} - {GUIDE_TITLE}", body, nav_links(sections, i)))
        written.append(section.filename)

    items = "\n".join(f'  <li><a href="{s.filename}">{html.escape(s.title)}</a></li>'
                      for s in sections)
    index_body = f"""<h1>{GUIDE_TITLE}</h1>
{version_line}
<p>{html.escape(DESCRIPTION)}</p>
<h2>Contents</h2>
<ol>
{items}
</ol>
<h2>More</h2>
<ul>
  <li><a href="full.html">The whole guide on a single page</a></li>
  <li><a href="releases.html">All release notes</a>: what changed in every version</li>
  <li><a href="{REPO_URL}/releases">Downloads on GitHub</a></li>
  <li><a href="{REPO_URL}/issues">Report a problem or suggest an idea</a></li>
</ul>"""
    write(out_dir, "index.html", page(GUIDE_TITLE, index_body))
    written.append("index.html")
    return written


def tagged_releases(repo_root: str) -> list[tuple[str, date]]:
    out = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)\t%(creatordate:short)", "refs/tags"],
        cwd=repo_root, capture_output=True, text=True, check=True).stdout
    releases = parse_tag_dates(out)
    if not releases:
        raise SystemExit("No v* tags found. The checkout needs fetch-depth: 0 to see tags.")
    return releases


def build_release_history(repo_root: str, out_dir: str) -> tuple[list[str], list[str]]:
    """Write the release pages. Returns (pages written, untagged notes versions)."""
    docs = os.path.join(repo_root, "docs")
    releases = tagged_releases(repo_root)
    have = set(notes_versions(os.listdir(docs)))
    missing = [v for v, _ in releases if v not in have]
    if missing:
        raise SystemExit(
            "Released versions with no docs/release-notes-vX.Y.Z.md: " + ", ".join(missing)
            + "\nEvery released version needs one, or it drops out of the history.")
    tagged = {v for v, _ in releases}
    untagged = [v for v in sorted(have, key=version_key) if v not in tagged]

    written = []
    for i, (version, released) in enumerate(releases):
        with open(os.path.join(docs, f"release-notes-v{version}.md"), encoding="utf-8") as f:
            body = render(strip_trailing_footers(f.read()))
        body = after_first_h1(body, (
            f'<p class="version">Released {long_date(released)}. '
            f'<a href="{RELEASE_TAG_URL}v{version}">Downloads for this release</a></p>'))
        links = [("User Guide", "index.html", ""), ("All release notes", "releases.html", "")]
        if i > 0:
            newer = releases[i - 1][0]
            links.append((f"Newer: {newer}", f"release-notes-v{newer}.html", "prev"))
        if i < len(releases) - 1:
            older = releases[i + 1][0]
            links.append((f"Older: {older}", f"release-notes-v{older}.html", "next"))
        name = f"release-notes-v{version}.html"
        write(out_dir, name, page(f"GHManage {version} Release Notes", body, links,
                                  nav_label="Release history"))
        written.append(name)

    first = releases[-1][1]
    items = "\n".join(
        f'  <li><a href="release-notes-v{v}.html">Version {v}</a>, {long_date(d)}'
        + (" (current release)" if i == 0 else "") + "</li>"
        for i, (v, d) in enumerate(releases))
    body = f"""<h1>GHManage Release History</h1>
<p>Every GHManage release, newest first, with the notes published for it.
There are {len(releases)} of them, starting in {MONTHS[first.month - 1]} {first.year}.</p>
<p>To find out which version you are running, open <strong>Help → About GHManage</strong>.
An installed copy of GHManage updates itself, so you are normally on the newest version already.</p>
<ul>
{items}
</ul>
<p>Each release's downloads are on <a href="{REPO_URL}/releases">its page on GitHub</a>.</p>"""
    write(out_dir, "releases.html", page(
        "GHManage Release History", body,
        [("User Guide", "index.html", ""), ("Single Page", "full.html", "")],
        nav_label="Release history"))
    written.append("releases.html")
    return written, untagged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default="build/docs", help="directory to write the site into")
    parser.add_argument("--version", required=True, help="the released version, e.g. 0.8.5")
    parser.add_argument("--repo-root", default=".", help="the repository's root")
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.repo_root, "docs", "USER-GUIDE.md"), encoding="utf-8") as f:
        guide = f.read()
    try:
        guide_pages = build_guide(guide, args.out, args.version)
    except ValueError as exc:
        raise SystemExit(f"docs/USER-GUIDE.md: {exc}")
    release_pages, untagged = build_release_history(args.repo_root, args.out)

    broken = check_links(args.out)
    if broken:
        raise SystemExit("Broken links between pages:\n  " + "\n  ".join(broken))

    print(f"Guide: {len(guide_pages)} pages ({', '.join(guide_pages)})")
    print(f"Release history: {len(release_pages)} pages")
    if untagged:
        print("Notes files with no tag, so not released and left out: " + ", ".join(untagged))
    return 0


if __name__ == "__main__":
    sys.exit(main())
