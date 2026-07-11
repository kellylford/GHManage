# GHManage v0.1.7 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Workflows view** — a new **View → Show → Workflows** mode lists the workflow definitions configured in the current repository (their name, state, and file path), separate from the existing **Workflow Runs** history view.
  - The details panel shows meaningful information for the selected workflow — name, state, file path, ID, and URL — matching how the other git views present detail.
- **Run a workflow on a branch** — in the Workflows view, press **Enter** (or **right-click → Run on branch…**) on a workflow to trigger it manually.
  - You choose the branch to run against from a screen-reader-friendly picker; nothing is triggered until you confirm.
  - Manual runs only work when the workflow declares an `on: workflow_dispatch` trigger. If it doesn't, the app tells you so — and how to enable it — instead of failing silently.
  - After a run starts, switch to **Workflow Runs** and refresh to watch it.

### Keybindings

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
| `Enter` (in Branches view) | Switch to Commits view for the selected branch |
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
