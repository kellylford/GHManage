# ghmanage

A **wxPython GUI** for viewing and managing GitHub issues, pull requests, and git metadata.

Built with [wxPython](https://www.wxpython.org/) and the [GitHub CLI (`gh`)](https://cli.github.com/).

## Features

- **Repo chooser** — list shows your GitHub repositories; arrow through and press Enter to load
- **Issues & PRs view** — issues and PRs in one list, like an email inbox
- **Git views** — browse branches, commits, tags, releases, workflows (run them on a branch), and workflow runs (drill into a run's artifacts and download them)
- **Branch-specific commits** — press Enter on a branch to see its commits, or press Ctrl+B in Commits view to pick a branch
- **Details panel** — full body, metadata, comments, file changes, and release notes shown below the list
- **Comment navigation** — press Alt+N/Alt+P in the details box to jump between comments
- **View More** — press Ctrl++ to load more items (30 at a time)
- **View menu** with:
  - **Show** — switch between Issues & PRs, Branches, Commits, Tags, Releases, Workflows, and Workflow Runs
  - **Quick / Full list mode** — Quick shows compact rows; Full includes field names (e.g. "number: 208, type: PR, state: OPEN, title: …") for screen readers
  - **Sort order** — by number, title, created date, updated date, or comments
  - **Column selection** — toggle columns on/off (columns change per view mode)
  - **State filter** — open, closed, or all (issues/PRs view)
  - **Show filter** — issues only, PRs only, or both (issues/PRs view)
- **Actions** — close, reopen, add comment, open in browser

## Prerequisites

- Python 3.9+
- The `gh` CLI installed and authenticated (`gh auth login`)
- wxPython

## Install

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install .
```

## Run

```bash
python ghviewer.py
```

Or for a specific repository (skips the repo chooser):

```bash
python ghviewer.py --repo owner/repo-name
```

## Keybindings

### Global

| Key | Action |
|-----|--------|
| `R` or `Ctrl+R` | Refresh the list (resets to first page) |
| `Ctrl++` | View More — load the next page of items |
| `Ctrl+O` | Open the selected item on GitHub in your browser |
| `Ctrl+G` | Go to a specific issue/PR by number (issues view only) |
| `Ctrl+B` | Select a branch for the Commits view (commits view only) |
| `Alt+N` | Jump to the next comment in the details box |
| `Alt+P` | Jump to the previous comment in the details box |
| `Tab` | Move focus between the repo list, item list, and details panel |
| `Ctrl+Q` | Quit |

### In the issue/PR list only

| Key | Action |
|-----|--------|
| `Enter` (or double-click) | Open the selected item on GitHub in your browser |
| `C` | Close the selected issue/PR |
| `O` | Reopen the selected issue/PR |
| `M` or `Ctrl+M` | Add a comment to the selected item |

### In the branches view

| Key | Action |
|-----|--------|
| `Enter` | Switch to Commits view for the selected branch |

### In the workflows view

| Key | Action |
|-----|--------|
| `Enter` (or right-click → Run on branch…) | Run the selected workflow on a branch you pick |

Manual runs only work when the workflow declares an `on: workflow_dispatch`
trigger; if it doesn't, the app tells you so instead of triggering anything.
After a run starts, switch to **Workflow Runs** and refresh to watch it.

### In the workflow runs view

| Key | Action |
|-----|--------|
| `Enter` | Drill into the selected run's artifacts (shown in the same list) |

From a run's **Artifacts** list, press `Enter` (or right-click → Download…) on an
artifact to download it into a folder you choose, and `Backspace` to return to the
runs list. Expired artifacts can't be downloaded and are marked as such.

### View menu → Show

Switch between **Issues & PRs**, **Branches**, **Commits**, **Tags**, **Releases**,
**Workflows** (the workflow definitions, which you can run on a branch), and
**Workflow Runs** (recent run history).
Each view has its own set of columns and detail formatting.

## Building a standalone executable

```bash
build.bat
```

Or with a clean build:

```bash
build.bat clean
```

The executable will be in `dist/ghmanage.exe`. See `build.bat` for details.