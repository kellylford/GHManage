# GHManage v0.1.0 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

This is the first release of **GHManage**, a wxPython GUI for viewing and managing GitHub issues and pull requests.

### Features

- **Repo chooser** — a list box on the left shows your GitHub repositories; arrow through them and press Enter to load
- **Combined issues & PRs list** — issues and PRs in one list, like an email inbox, with sortable columns
- **Details panel** — full body, metadata, comments, and PR diff stats shown below the list
- **Comment navigation** — press Alt+N / Alt+P to jump between comments in the details box
- **Go To Issue** — press Ctrl+G to jump to a specific issue/PR by number
- **List modes** — Quick (compact) or Full (includes field names for screen readers)
- **View menu** — sort order, column selection, state filter (open/closed/all), show filter (issues/PRs/both)
- **Actions** — close, reopen, add comment, open in browser

### Keybindings

| Key | Action |
|-----|--------|
| `Enter` (or double-click) | Open the selected item on GitHub in your browser |
| `C` | Close the selected issue/PR |
| `O` | Reopen the selected issue/PR |
| `R` or `Ctrl+R` | Refresh the list |
| `M` or `Ctrl+M` | Add a comment to the selected item |
| `Ctrl+G` | Go to a specific issue/PR by number |
| `Alt+N` | Jump to the next comment in the details box |
| `Alt+P` | Jump to the previous comment in the details box |
| `Tab` | Move focus between the repo list, issue list, and details panel |
| `Ctrl+Q` | Quit |