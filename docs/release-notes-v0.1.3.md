# GHManage v0.1.3 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Branch-specific commits** — the Commits view now shows commits for a specific branch instead of always defaulting to `main`.
  - **From Branches view**: press `Enter` on any branch to switch to Commits view filtered to that branch.
  - **From Commits view**: press `Ctrl+B` (or File → Select Branch…) to pick a branch from a dialog.
  - The status bar and details panel show which branch you're viewing commits on.
  - Switching away from Commits view and back resets to the default branch.

### Improvements

- **build.bat** — added a build script for creating `dist\ghmanage.exe` from the repo root. Supports `build.bat` (incremental) and `build.bat clean` (full rebuild).
- **README** — updated with branch-specific commit keybindings and build instructions
- **COPILOT.md** — updated project knowledge file with new functions, state, and version history

### Keybindings

| Key | Action |
|-----|--------|
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