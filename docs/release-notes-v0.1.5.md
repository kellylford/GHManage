# GHManage v0.1.5 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### Bug fixes

- **No more console window flashing** — on Windows, every background `gh` CLI call used to briefly pop up a console window. This is now suppressed with `CREATE_NO_WINDOW`, so the app runs quietly without terminal windows flashing on screen during loads.

- **Go To works for any issue/PR number** — previously, Go To (Ctrl+G) only worked if the item was already in the loaded list. If you searched for a closed issue, a PR beyond the fetch limit, or anything not matching the current filter, it just said "not found." Now it fetches the item on-demand from GitHub and inserts it into the list so you can view it regardless of state or page position.

- **Go To shows a dialog when item doesn't exist** — if you enter a number that doesn't exist as an issue or PR in the repo, you now get a clear "Not Found" dialog instead of a silent status bar message that's easy to miss. Errors during the fetch also show a dialog.

### Improvements

- **View menu cleanup** — the View menu had two submenus both named "Show," which was confusing. They are now clearly labeled:
  - **View Mode** — switch between Issues & PRs, Branches, Commits, Tags, Releases, Workflow Runs
  - **Filter** — filter Issues Only / PRs Only / Issues & PRs within the Issues & PRs view

### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+Shift+O` | Open a repository by URL or OWNER/NAME |
| `Ctrl++` | View More — load the next page of items |
| `Ctrl+B` | Select a branch for the Commits view (commits view only) |
| `Enter` (in Branches view) | Switch to Commits view for the selected branch |
| `Enter` (in other views) | Open the selected item on GitHub in your browser |
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