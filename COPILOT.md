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
- `fetch_release_assets(repo, release_id, release_tag, limit)` — a release's files with their
  download counts. The releases endpoint already returns assets inline, so the Releases list
  costs no extra call; this exists so the drill-down view can refresh on its own (R key).
- `total_downloads(releases)` — sum across every asset of every release given.
- `ReleaseAsset` — dataclass for a release file. `Release.downloads` is a computed property
  summing its assets. **Download counts are lifetime running totals** — GitHub exposes no
  date breakdown, so any over-time view would require snapshotting and diffing ourselves.
- `fetch_labels(repo, limit)` / `create_label(repo, name, color, description)` /
  `delete_label(repo, name)` — the Labels view. All three go through
  `resolve_issue_repo`, like the issue calls do: on a fork you browse the upstream
  issues, so a label list from the fork itself would not match them. `gh label list`
  exits non-zero on a repo with no labels at all; `fetch_labels` translates that
  into an empty list rather than an error.
- `Label` — dataclass for a label: name, color, description, url, is_default.
- `fetch_issues` / `fetch_prs` take an optional `label` and pass it to `gh` as
  `--label`. Filtering server-side is the point — an unfiltered page of 100 may
  not contain a single issue with the label you picked.
- `fetch_compare(repo, base, head)` — compare two refs.
- `fetch_item_detail(item, repo)` — re-fetch a single issue/PR with full detail.
- `close_item` / `reopen_item` / `add_comment` — actions on issues/PRs.
- `list_repos(limit)` — list user's GitHub repos.
- `detect_repo()` — detect repo from current git directory.
- `sort_items(items, sort_order)` — sort by named order string.
- `fetch_dispatch_spec(repo, path, ref)` → `DispatchSpec` — whether a workflow can be run
  manually and which inputs it declares. **There is no API that returns a workflow's inputs.**
  GitHub's own "Run workflow" form is built by parsing the workflow file, and so is this.
  `ref` matters: a branch that adds an input has a different form from the default branch.
- `_parse_dispatch_spec(raw)` — the YAML parsing half, split out so it is testable without
  network access. Note the `on:` key: YAML 1.1 reads a bare `on` as boolean `True`, so the
  lookup checks both. Falls back to the old substring check if the file will not parse.
- `WorkflowInput` — one declared input: name, type, description, default, required, options.
- `fetch_environments(repo)` — environment names, used to fill the choices for an
  `environment`-typed input (the workflow file declares those without options).
- `dispatch_workflow(repo, workflow_id, ref, inputs)` — trigger a manual run. Inputs go over
  as `gh api -f "inputs[key]=value"`; `gh` turns the bracket syntax into nested JSON.
- `workflow_supports_dispatch(repo, path)` — thin wrapper kept for callers that only need the
  yes/no.

### ghviewer.py

- `GhViewerFrame` — main window. Owns all state: `repo`, `items`, `git_items`, `columns`,
  `sort_order`, `list_mode`, `state_filter`, `tab_filter`, `page_size`, `current_limit`,
  `view_mode`, `commit_branch`, `label_filter`.
- `_build_ui` / `_build_menu` / `_bind_events` — construction.
- `_load_items` — background fetch + populate list (dispatches by `view_mode`).
- `_switch_view(mode)` — switch between Issues/PRs, Branches, Commits, Tags, Releases,
  Workflow, Labels. Each drill-down view clears its context here when you leave it
  (`commit_branch`, `artifacts_run`, `assets_release`, `label_filter`) — add a reset for
  any new one.
- Drill-down views are registered in `PARENT_VIEW`, which is what makes Backspace step back up.
  A new drill-down needs an entry there, in `VIEW_COLUMNS`, and in `_VIEW_LABELS`.
- `_show_details(idx)` — dispatches to `_show_issue_details` or `_show_git_details`.
- `_navigate_comment(direction)` — Alt+N/Alt+P comment jumping.
- `_refresh_list_display` — re-populate list from `self.items` or `self.git_items` without re-fetching.
- `on_item_activated` — context-dependent: in Branches view, Enter switches to Commits for that branch; otherwise opens in browser.
- `on_select_branch` — Ctrl+B branch picker dialog for Commits view.
- **The Labels view is a view of the Issues view, not a drill-down.** Enter on a label
  sets `label_filter` and loads Issues & PRs restricted to it, which keeps the state
  filter, columns, sorting, and every issue action working. It is deliberately *not* in
  `PARENT_VIEW` — the parent map is keyed by view mode and the drilled-into view here is
  `VIEW_ISSUES`, which has no single parent. Backspace is handled as its own case in
  `on_list_key_down`, guarded on `label_filter` being set, and `on_view_issues` clears
  the filter when you ask for Issues & PRs by name (Ctrl+1) even though the mode does
  not change.
- `NewLabelDialog` — name/description/colour form. Colour is validated as 6 hex digits
  before `gh` is called, and may be left blank for GitHub to choose.
- `_on_label_action_done` — refresh after a label create/delete. Separate from
  `_on_action_done` because a label can be created from any view via the File menu, and
  refreshing the current view would hide the label just made.
- **The Actions menu is the home for anything that acts on the listed item**, whichever
  view it belongs to. `_update_actions_menu` re-labels and enables its entries for the
  current view and is called from `_update_menu_checks` (so every `_switch_view` covers
  it) plus `_select_repo` / `_select_favorites`, where the repo changes without the view
  doing so. A new action belongs there, with an entry in that method.
- `_delete_focused_item` is the single dispatcher behind Delete, Ctrl+D, and the Actions
  menu entry, so the key and the menu cannot disagree about what Delete means in a view.
  Add new deletable views there and in `_update_actions_menu`.
- **Bare Insert/Delete are handled in `on_char_hook`** — a frame-level `EVT_CHAR_HOOK` —
  **not** in `on_list_key_down` and **not** as accelerators. `EVT_LIST_KEY_DOWN` only
  fires while the list has focus, which made the keys unusable from the details panel,
  and that panel is where the text describing them is read. A bare Delete *accelerator*
  is not an option either: it would swallow the Delete key everywhere in the window.
  Their Ctrl+I / Ctrl+D twins are ordinary accelerators on the Actions menu items, which
  is why those need nothing in the hook. The hook skips everything else, so focused
  controls keep first claim on their own keys, and it ignores the repo list, where
  Delete reads as "remove this repo".
- Status-bar hints are per-view for a reason: a key named in the status bar has to work
  in that view. `Ctrl+B=select branch` is Commits-only — `on_select_branch` refuses
  everywhere else.
- `WorkflowInputsDialog` — the "Run workflow" form, generated at runtime from a
  `DispatchSpec`. choice/environment → `wx.Choice`, boolean → `wx.CheckBox`, everything else
  → `wx.TextCtrl`. Because it is generated rather than hand-written, **labelling is manual**:
  each control gets a preceding `wx.StaticText` *and* a matching `SetName`, so the accessible
  name is right whichever the screen reader picks up. A checkbox carries its own label and so
  gets the name only — a StaticText too would read it twice.
- The manual-run flow is **branch first, then inputs** (`_run_workflow_flow` →
  `_on_workflow_branches_ready` → `_on_workflow_dispatch_ready`). Inputs are declared in the
  workflow file, so they must be read from the branch being run. Reading them first would
  show the default branch's form and silently drop values on any branch that differs.

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
| Releases (assets inline) | `repos/{owner}/{repo}/releases` |
| Release assets | `repos/{owner}/{repo}/releases/{id}/assets` |
| Workflow runs | `repos/{owner}/{repo}/actions/runs` |
| Contributors | `repos/{owner}/{repo}/contributors` |
| Workflow file (for inputs) | `repos/{owner}/{repo}/contents/{path}?ref={ref}` |
| Environments | `repos/{owner}/{repo}/environments` |
| Manual run | `POST repos/{owner}/{repo}/actions/workflows/{id}/dispatches` |

## CI/CD

- `.github/workflows/ghmanage.yml` — builds `ghmanage.exe` via PyInstaller on Windows.
- Triggers on push to `main`, `v*` tags, and PRs to `main`.
- On tag push: creates a GitHub Release with `ghmanage.exe` attached.
- Release notes read from `docs/release-notes-<tag>.md`.
- Uses `softprops/action-gh-release@v3`.

## Release process

1. Update `__version__` in `version.py`. (`pyproject.toml` reads it from there; CI fails the
   build if the tag and `version.py` disagree.)
2. Create `docs/release-notes-vX.Y.Z.md`. **Required** — the workflow passes it to both
   `vpk pack --releaseNotes` and the release body, so a missing file fails the release.
3. Commit: `git commit -m "Description (vX.Y.Z)"`.
4. Tag: `git tag vX.Y.Z`.
5. Push: `git push origin main && git push origin vX.Y.Z`.
6. CI auto-builds and creates the release.

## Current versions

- v0.1.0 — initial release
- v0.1.1 — fixed missing issues (paging), added View More
- v0.1.2 — git views: branches, commits, tags, releases, workflow runs
- v0.1.3 — branch-specific commits: Enter on a branch switches to its commits, Ctrl+B branch picker
- v0.1.4 — open repos by URL, pinned repos, fork-aware issue fetching, informative window title, default load 100
- *(v0.1.5–v0.3.0 not recorded here — see `docs/release-notes-v*.md` for each)*
- v0.4.0 — Run Workflow collects `workflow_dispatch` inputs
- v0.5.0 — Ctrl+1..Ctrl+8 switch views
- v0.6.0 — Labels view (Ctrl+8): browse by label, create and delete labels.
  Favorites moved to Ctrl+9 to keep the numbers matching the menu order.
- v0.6.1 — Actions menu gathers every item action; Ctrl+I / Ctrl+D alongside
  Insert/Delete; bare Insert/Delete work from the details panel too.

## Roadmap

- **PR diff view** — show file-level changes for a PR in the details panel.
- **Branch comparison** — compare two branches or tags, show commits and file changes.
- **Multi-repo dashboard** — watch multiple repos at once.
- **Workflow run filtering** — filter workflow runs by branch.