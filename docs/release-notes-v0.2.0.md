# GHManage v0.2.0 Release Notes

GHManage is an accessible, keyboard-first wxPython desktop app for browsing and
managing GitHub repositories — issues, pull requests, and the git/Actions side
of a repo — built to work well with screen readers.

This release rolls up everything built so far into a single current build. Older
per-build releases have been removed to keep this page tidy; their version tags
remain in the repository history.

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## Highlights in this release

- **Backspace navigates back out of a drill-down.** When you've drilled into a
  sub-view — a branch's commits, or a workflow run's artifacts — **Backspace**
  returns you to where you came from (the branches list, or the workflow runs
  list). It steps back within the current flow rather than keeping a full
  app-wide history.

## What GHManage can do

### Issues & pull requests

- Browse issues and PRs for any repository, filter by **Open / Closed / All**,
  and switch between **Issues only / PRs only / both**.
- Rich details for the selected item, including labels, assignees, review status,
  branch/merge info, and the full comment thread — with **Alt+N / Alt+P** to jump
  between comments.
- **Close**, **reopen**, and **comment** on items without leaving the app.
- **Go To** a specific issue/PR by number, even if it isn't in the loaded page.

### Git views

- **Branches**, **Commits**, **Tags**, and **Releases** views, each with columns
  and detail formatting tuned to the item type.
- **Enter** on a branch drills into its **Commits**; **Backspace** returns to the
  branch list.
- **Compare Branches** (**Ctrl+Shift+B**): a two-step, screen-reader-friendly
  flow that reports how far one branch is ahead/behind another, the commits
  between them, and the changed files with per-file line counts.

### GitHub Actions

- **Workflows** view — the workflow definitions in the repo. **Enter** (or
  right-click → **Run on branch…**) runs a workflow on a branch you choose, when
  the workflow supports manual (`workflow_dispatch`) runs; if it doesn't, the app
  says so instead of failing.
- **Workflow Runs** view — recent run history. **Enter** drills into a run's
  **Artifacts** (name, size, expiry, date); **Enter** on an artifact downloads it
  into a folder you choose (unpacked, so you get the real file), and **Backspace**
  returns to the runs list.

### Getting around

- **Favorites** (**F** to toggle) collect items across repositories into one list.
- Open repos by **URL or OWNER/NAME** (**Ctrl+Shift+O**) without cloning.
- **Quick Filter** (**Ctrl+F**) narrows the current list as you type.
- **Quick / Full** list modes, configurable columns, and sortable lists.
- A **Full Mode** that speaks field names for screen readers.

## Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+Shift+O` | Open a repository by URL or OWNER/NAME |
| `Ctrl++` | View More — load the next page of items |
| `Ctrl+B` | Select a branch for the Commits view (commits view only) |
| `Ctrl+Shift+B` | Compare two branches (ahead/behind, commits, changed files) |
| `Ctrl+F` | Quick Filter — filter the current list by text |
| `Escape` | Clear the quick filter |
| `F` | Toggle favorite on the focused item |
| `Enter` (in Workflows view) | Run the selected workflow on a branch you pick |
| `Enter` (in Workflow Runs view) | List the selected run's artifacts |
| `Enter` (in Artifacts view) | Download the selected artifact into a folder you choose |
| `Enter` (in Branches view) | Switch to Commits view for the selected branch |
| `Backspace` (in Commits or Artifacts view) | Step back to the parent list |
| `Enter` (in other views) | Open the selected item on GitHub in your browser |
| `Enter` (in Favorites view) | Open the selected favorite in browser |
| `C` | Close the selected issue/PR (issues view only) |
| `O` | Reopen the selected issue/PR (issues view only) |
| `R` or `Ctrl+R` | Refresh the list (resets to first page) |
| `M` or `Ctrl+M` | Add a comment to the selected item (issues view only) |
| `Ctrl+G` | Go to a specific issue/PR by number (issues view only) |
| `Ctrl+O` | Open the selected item on GitHub in your browser |
| `Alt+N` | Jump to the next comment in the details box |
| `Alt+P` | Jump to the previous comment in the details box |
| `Tab` | Move focus between the repo list, item list, and details panel |
| `Ctrl+Q` | Quit |
