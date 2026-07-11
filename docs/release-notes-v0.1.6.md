# GHManage v0.1.6 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Compare Branches** — press **Ctrl+Shift+B** (or **File → Compare Branches…**) to compare any two branches in the current repository.
  - A two-step, screen-reader-friendly flow: first pick the **base** branch (compare *from*, e.g. `main`), then pick the **head** branch (compare *to*). Each prompt spells out the direction so it's always clear which way the comparison runs.
  - The result opens in a focusable, read-only text window you can navigate line by line. It leads with a plain-English summary — for example, *"'feature' is 5 commits AHEAD of 'main' and 2 BEHIND"* — followed by the commits that are on the head branch but not the base, and the list of changed files with per-file `+/-` line counts and a total.
  - Identical branches are reported clearly as "no differences."
  - Available whenever a repository is loaded; the Branches view shows a `Ctrl+Shift+B=compare branches` hint in the status bar.

### Bug fixes

- **Branch comparison now works** — the underlying compare request had a malformed API path that caused every comparison to fail. It has been corrected, and the feature is now wired into the app (see above).

### Improvements

- **Faster Branches view** — loading branches used to make one additional API call per branch, one at a time, which was slow on repositories with many branches. Those per-branch lookups now run concurrently, so the Branches view loads much faster. The information shown is unchanged.

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
