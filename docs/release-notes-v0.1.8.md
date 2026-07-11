# GHManage v0.1.8 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Drill into a workflow run's artifacts** — in the **Workflow Runs** view, press **Enter** on a run to list the artifacts that run produced, shown in the same list (name, size, whether it has expired, and date).
- **Download artifacts** — from a run's **Artifacts** list, press **Enter** (or **right-click → Download…**) on an artifact to download it into a folder you choose. The artifact is unpacked for you, so you get the actual file (for example `ghmanage.exe`) rather than a zip.
  - Expired artifacts are clearly marked and can't be downloaded — the app tells you instead of failing.
  - Press **Backspace** in the Artifacts list to return to the workflow runs.
  - The window title and status bar show which run you're viewing artifacts for.

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
| `Enter` (in Workflow Runs view) | List the selected run's artifacts |
| `Enter` (in Artifacts view) | Download the selected artifact into a folder you choose |
| `Backspace` (in Artifacts view) | Return to the workflow runs |
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
