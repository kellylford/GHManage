# GHManage — Project Knowledge

> This file is the authoritative reference for anyone (human or AI) working on this project.
> Keep it updated whenever the architecture, conventions, or features change.

## What This Project Is

**GHManage** (package name `ghviewer`) is a **wxPython desktop GUI** for viewing and managing
GitHub issues, pull requests, and git metadata — branches, commits, tags, releases,
and CI workflow runs. It is designed specifically to be **screen-reader-friendly** without being
patronizing: keyboard-first navigation, a "Full mode" that includes field names in list rows,
status-bar announcements, and comment navigation via Alt+N/Alt+P.

The app shells out to the **`gh` CLI** for all GitHub operations (issues, PRs, repos) and uses
the **GitHub REST API** (via `gh api`) for git metadata that `gh` doesn't have first-class commands
for (branches, commits, tags, compare, workflow runs).

## Architecture

```
ghviewer.py   — UI layer (wxPython). All event handlers, menus, dialogs, list population.
gh_data.py    — Data layer. All `gh` CLI and `gh api` calls, data classes, parsing.
```

**Rule:** `ghviewer.py` never calls `gh` or the API directly. `gh_data.py` never imports wx.
This separation is critical — keep it.

### Data flow

1. User selects a repo → `ghviewer` calls `gh_data.fetch_*` in a background thread
2. `gh_data` shells out to `gh` (or `gh api`), parses JSON, returns `Item` / `Branch` / `Commit` objects
3. `ghviewer` receives results via `wx.CallAfter` and populates the ListCtrl + details panel

### Threading model

All network calls happen in `threading.Thread(daemon=True)`. Results are marshaled back to the
UI thread via `wx.CallAfter`. Never touch wx widgets from a worker thread.

## Key Classes & Functions

### gh_data.py

- `Item` — dataclass for issues/PRs. Has `to_row(columns)` and `to_accessible_string(columns)`.
- `_run_gh(args)` — runs `gh` subprocess, returns stdout, raises `GhError` on failure.
- `fetch_issues(repo, state, limit)` / `fetch_prs(repo, state, limit)` — list issues/PRs.
- `fetch_branches(repo, limit)` — list branches via REST API.
- `fetch_commits(repo, branch, limit)` — list commits, optionally for a specific branch.
- `fetch_commit_detail(repo, sha)` — full commit with file changes.
- `fetch_tags(repo, limit)` / `fetch_releases(repo, limit)` / `fetch_workflow_runs(repo, limit)`.
- `fetch_compare(repo, base, head)` — compare two refs.
- `fetch_item_detail(item, repo)` — re-fetch a single issue/PR with full detail.
- `close_item` / `reopen_item` / `add_comment` — actions on issues/PRs.
- `list_repos(limit)` — list user's GitHub repos.
- `detect_repo()` — detect repo from current git directory.
- `sort_items(items, sort_order)` — sort by named order string.

### ghviewer.py

- `GhViewerFrame` — main window. Owns all state: `repo`, `items`, `git_items`, `columns`,
  `sort_order`, `list_mode`, `state_filter`, `tab_filter`, `page_size`, `current_limit`,
  `view_mode`, `commit_branch`.
- `_build_ui` / `_build_menu` / `_bind_events` — construction.
- `_load_items` — background fetch + populate list (dispatches by `view_mode`).
- `_switch_view(mode)` — switch between Issues/PRs, Branches, Commits, Tags, Releases, Workflow.
- `_show_details(idx)` — dispatches to `_show_issue_details` or `_show_git_details`.
- `_navigate_comment(direction)` — Alt+N/Alt+P comment jumping.
- `_refresh_list_display` — re-populate list from `self.items` or `self.git_items` without re-fetching.
- `on_item_activated` — context-dependent: in Branches view, Enter switches to Commits for that branch; otherwise opens in browser.
- `on_select_branch` — Ctrl+B branch picker dialog for Commits view.

## Conventions

### Screen-reader friendliness

- **Status bar is the announcement channel.** Use `self._announce(msg)` (which calls `SetStatusText`).
- **Full mode** prefixes field names in list rows: `"number: 208, type: PR, state: OPEN"`.
- **Keyboard first.** Every action has a keybinding. Never add a feature that requires mouse-only access.
- **No patronizing hand-holding.** Don't add "Welcome!" dialogs or verbose tooltips. Power users want speed.
- **Comment navigation** uses Alt+N/Alt+P with position tracking via `_comment_positions`.

### Code style

- Type hints everywhere (`from __future__ import annotations`).
- Dataclasses for data models.
- `Optional[str]` for `repo` (None = detect from current directory).
- Section dividers with `# ── Name ──` in both files.
- `GhError` is the only exception type for data-layer failures.

### `gh` CLI usage

- Issues/PRs: use `gh issue list` / `gh pr list` / `gh issue view` / `gh pr view` with `--json`.
- Actions: `gh issue close` / `gh issue reopen` / `gh issue comment` (same for `pr`).
- Repos: `gh repo list` / `gh repo view`.
- Git metadata: use `gh api` (REST API) — branches, commits, tags, compare, releases, workflow runs.
- Always pass `--repo OWNER/NAME` when `repo` is not None.
- `gh` returns newest-first by default for issue/pr lists.

### GitHub REST API endpoints used

| Purpose | Endpoint |
|---------|----------|
| Branches | `repos/{owner}/{repo}/branches` |
| Branch detail | `repos/{owner}/{repo}/branches/{branch}` |
| Commits | `repos/{owner}/{repo}/commits` |
| Commit detail | `repos/{owner}/{repo}/commits/{sha}` |
| Tags | `repos/{owner}/{repo}/tags` |
| Compare | `repos/{owner}/{repo}/compare/{base}...{head}` |
| Releases | `repos/{owner}/{repo}/releases` |
| Workflow runs | `repos/{owner}/{repo}/actions/runs` |
| Contributors | `repos/{owner}/{repo}/contributors` |

## CI/CD

- `.github/workflows/ghmanage.yml` — builds `ghmanage.exe` via PyInstaller on Windows.
- Triggers on push to `main`, `v*` tags, and PRs to `main`.
- On tag push: creates a GitHub Release with `ghmanage.exe` attached.
- Release notes read from `docs/release-notes-<tag>.md`.
- Uses `softprops/action-gh-release@v3`.

## Release process

1. Update version in `pyproject.toml`.
2. Create `docs/release-notes-vX.Y.Z.md`.
3. Commit: `git commit -m "Description (vX.Y.Z)"`.
4. Tag: `git tag vX.Y.Z`.
5. Push: `git push origin main && git push origin vX.Y.Z`.
6. CI auto-builds and creates the release.

## Current versions

- v0.1.0 — initial release
- v0.1.1 — fixed missing issues (paging), added View More
- v0.1.2 — git views: branches, commits, tags, releases, workflow runs
- v0.1.3 — branch-specific commits: Enter on a branch switches to its commits, Ctrl+B branch picker

## Roadmap

- **PR diff view** — show file-level changes for a PR in the details panel.
- **Branch comparison** — compare two branches or tags, show commits and file changes.
- **Multi-repo dashboard** — watch multiple repos at once.
- **Workflow run filtering** — filter workflow runs by branch.