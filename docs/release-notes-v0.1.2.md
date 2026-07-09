# GHManage v0.1.2 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Git views** — browse branches, commits, tags, releases, and CI workflow runs directly in the app. Switch views via the View → Show submenu.
  - **Branches** — branch name, last commit message, author, date, protected status
  - **Commits** — SHA, message, author, date; details panel shows file-level changes with additions/deletions
  - **Tags** — tag name and commit SHA
  - **Releases** — tag, name, date, draft/prerelease flags; details panel shows full release notes
  - **Workflow Runs** — CI status, result, branch, event, date — see if builds passed without leaving the app
- **Dynamic columns** — the Columns submenu rebuilds automatically when switching between Issues/PRs and Git views, showing only the columns relevant to the current view
- **Open in browser** works across all views — press Enter or Ctrl+O to open any item on GitHub

### Improvements

- **COPILOT.md** — added a project knowledge file documenting architecture, conventions, and API usage for anyone working on the codebase
- **README** — updated with new features, views, and keybindings

### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl++` | View More — load the next page of items |
| `Enter` (or double-click) | Open the selected item on GitHub in your browser |
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