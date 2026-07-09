# ghmanage

A **wxPython GUI** for viewing and managing GitHub issues and pull requests.

Built with [wxPython](https://www.wxpython.org/) and the [GitHub CLI (`gh`)](https://cli.github.com/).

## Features

- **Repo chooser** — dropdown lists your GitHub repositories, or type `owner/name`
- **Combined list** — issues and PRs in one list, like an email inbox
- **Details panel** — full body, metadata, comments, and PR diff stats shown below the list
- **Comment navigation** — press N/P in the details box to jump between comments
- **View menu** with:
  - **Quick / Full list mode** — Quick shows compact rows; Full includes field names (e.g. "number: 208, type: PR, state: OPEN, title: …") for screen readers
  - **Sort order** — by number, title, created date, updated date, or comments
  - **Column selection** — toggle any of 16 columns on/off
  - **State filter** — open, closed, or all
  - **Show filter** — issues only, PRs only, or both
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

### In the issue/PR list

| Key | Action |
|-----|--------|
| `Enter` (or double-click) | Open the selected item on GitHub in your browser |
| `C` | Close the selected issue/PR |
| `O` | Reopen the selected issue/PR |
| `R` or `Ctrl+R` | Refresh the list |
| `M` or `Ctrl+M` | Add a comment to the selected item |
| `Tab` | Move focus to the next control |
| `Ctrl+Q` | Quit |

### In the details box

| Key | Action |
|-----|--------|
| `N` | Jump to the next comment |
| `P` | Jump to the previous comment |
| `Tab` | Move focus back to the list |

## Building a standalone executable

```bash
pip install pyinstaller
pyinstaller --noconsole --name ghmanage ghviewer.py
```

The executable will be in `dist/ghmanage/`.