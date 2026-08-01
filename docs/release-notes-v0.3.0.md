# GHManage 0.3.0

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

Issues, pull requests, branches, commits, tags, releases, workflows, and workflow
runs all appear in a single list-and-details layout, the way an email client lays
out a mailbox. Every view is reachable from the keyboard and reads cleanly with a
screen reader — there are no custom-drawn controls to get lost in.

This is the first release worth pointing anyone at: GHManage now installs itself
properly and keeps itself up to date, so getting the next version no longer means
going and fetching one.

## Install

1. Install the [GitHub CLI](https://cli.github.com/) and sign in — GHManage uses
   it for every GitHub request:

   ```
   gh auth login
   ```

2. Download **GHManage-win-Setup.exe** below and run it.

It installs for your account only, with no administrator prompt, and adds a Start
menu shortcut. **From here on it updates itself**: a new version downloads
quietly in the background and is applied the next time you start the app. Nothing
to click, nothing to download again. Help ▸ Check for Updates checks on demand
and offers to restart.

Windows may show a SmartScreen "unknown publisher" warning until code signing is
switched on — choose **More info → Run anyway**.

**GHManage-win-Portable.zip** is the same app as a folder you can run from
anywhere. It does not update itself.

## What it does

**Pick a repository.** The app opens on a list of your GitHub repositories —
arrow to one and press Enter. Repositories you add by URL stay pinned near the
top. Press `F` on any item, in any view, to star it; everything you star collects
in a single **★ Favorites** view that spans repositories. Or skip the chooser and
launch with `--repo owner/name`.

**Issues and pull requests together.** One inbox-style list, filtered by state
(open, closed, all) and type (issues, PRs, or both), sorted by number, title,
created date, updated date, or comment count. The details panel below shows the
full body, metadata, comments, and — for PRs — the file changes. `Alt+N` and
`Alt+P` jump between comments without scrolling.

**Git views.** Switch the list to branches, commits, tags, releases, workflows,
or workflow runs from the View menu. Press Enter on a branch to see its commits,
or `Ctrl+B` to pick a branch from within the commits view. `Ctrl+Shift+B` compares
two branches to see what's ahead and behind.

**Releases with download counts.** The Releases view shows how many times each
release was downloaded, with a repo-wide total in the status bar. Press Enter for
a per-file breakdown, most-downloaded first.

**Drill down and download.** Enter on a workflow run lists its artifacts and
downloads the one you pick; `Backspace` steps back out to where you were.

**Act without leaving the app.** Close and reopen issues and PRs, add comments,
run a workflow on a branch you choose, delete workflow runs, and open anything on
GitHub in your browser.

**Built for screen readers.** Quick list mode shows compact rows; Full list mode
includes field names in each row ("number: 208, type: PR, state: OPEN, title: …")
so a screen reader announces what each value means. Columns are configurable per
view, and every action has a keybinding — the
[README](https://github.com/kellylford/GHManage#keybindings) has the full table.

## Also in this release

- The app has a real icon, in the Start menu, the taskbar, and Alt+Tab.
- `ghmanage.exe` now carries version information, so Properties ▸ Details tells
  you which build you are running.

## Requirements

- Windows 10 or 11, 64-bit
- The [GitHub CLI](https://cli.github.com/), installed and authenticated with
  `gh auth login`. GHManage never asks for or stores credentials of its own.

Your favorites and pinned repositories live in `%APPDATA%\ghmanage` and are kept
across updates.

## Downloads

| File | Use it if |
|------|-----------|
| `GHManage-win-Setup.exe` | You want GHManage installed and updating itself |
| `GHManage-win-Portable.zip` | You want a folder to run from anywhere, no install, no updates |

The remaining files (`*.nupkg`, `RELEASES`, `releases.win.json`,
`assets.win.json`) are the update feed the installed app reads. Leave them alone.
