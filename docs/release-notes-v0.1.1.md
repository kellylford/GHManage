# GHManage v0.1.1 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### Bug fixes

- **Missing issues fixed** — `gh issue list` and `gh pr list` default to returning only 30 items. Repositories with more than 30 issues/PRs were truncated. The fetch functions now accept a `--limit` parameter so all items can be loaded.

### New features

- **View More** — a new **View More** menu item (`Ctrl++`) in the File menu loads the next page of items (30 at a time). The status bar shows how many items are currently loaded ("Showing up to N newest").
- **Incremental paging** — the app starts with the 30 newest items and grows the limit each time you press View More. Refresh (`Ctrl+R`) and any filter change (state, tab) resets back to the first page.

### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl++` | View More — load the next page of items |
| `Enter` (or double-click) | Open the selected item on GitHub in your browser |
| `C` | Close the selected issue/PR |
| `O` | Reopen the selected issue/PR |
| `R` or `Ctrl+R` | Refresh the list (resets to first page) |
| `M` or `Ctrl+M` | Add a comment to the selected item |
| `Ctrl+G` | Go to a specific issue/PR by number |
| `Alt+N` | Jump to the next comment in the details box |
| `Alt+P` | Jump to the previous comment in the details box |
| `Tab` | Move focus between the repo list, issue list, and details panel |
| `Ctrl+Q` | Quit |