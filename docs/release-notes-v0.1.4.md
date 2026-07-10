# GHManage v0.1.4 Release Notes

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## What's new

### New features

- **Open any repo by URL** — browse any public GitHub repository (or one you have access to) without cloning it first.
  - **File → Open Repository… (Ctrl+Shift+O)** opens a dialog where you paste a GitHub URL or `OWNER/NAME`.
  - Accepts `https://github.com/owner/name`, `.git` URLs, SSH URLs, and paths like `/pull/123` (extra path is stripped).
  - All views work — issues, PRs, branches, commits, tags, releases, and workflow runs.
  - Write actions (close/reopen/comment) work on repos where your `gh`-authenticated account has permission.

- **Pinned repositories** — repos opened by URL are saved to `%APPDATA%\ghmanage\pinned_repos.json` and shown in the left repo list across sessions.
  - Pinned repos appear at the top of the list with a 📌 marker.
  - **File → Remove from List…** removes the selected pinned repo.
  - Your own repos (from `gh repo list`) are always fetched fresh and can't be removed from here.

- **Fork-aware issue fetching** — selecting a fork now pulls issues and PRs from its upstream parent.
  - Forks on GitHub have issues disabled by default; the issues live on the parent (upstream) repo.
  - The status bar notes when items come from upstream, e.g. `kellylford/quill (issues from upstream Community-Access/quill)`.
  - Close, reopen, comment, and detail-fetch all target the upstream repo for forks.

### Improvements

- **Informative window title** — the title bar now shows the current view, branch (where relevant), repo, and app name, e.g. `Commits — main — kellylford/quill — ghviewer`.
- **Default load count raised to 100** — the initial fetch now grabs up to 100 items instead of 30. "View More" (Ctrl++) still grows the list by 100 at a time.

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