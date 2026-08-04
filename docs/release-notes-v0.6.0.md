# GHManage 0.6.0

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

This release adds labels: a view of them, a way to read a repository through
them, and the two actions that were missing.

## Labels are a view now

`Ctrl+8` lists the repository's labels by name, with their descriptions and
colours, the same way `Ctrl+2` lists branches and `Ctrl+5` lists releases. The
details panel below spells out the label, its description, its colour, and
whether it is one of the defaults GitHub creates with a repository.

## Enter on a label reads the repository through it

Press `Enter` on a label and the Issues & PRs view comes back holding only the
issues and pull requests that carry it. Everything you already know still works
there — the state filter, the columns, the sort order, `C` to close, `M` to
comment — because it is the same view, not a new one.

The restriction is applied by GitHub, not by the quick filter, so it finds items
that were never on the page you were looking at. A repository with 800 open
issues will happily tell you the 6 tagged `accessibility`, and you never have to
press `Ctrl++` to go looking for them.

While a label is on, the window title and the status bar both name it, so it is
never a mystery why the list is short. `Backspace` returns to the labels.
`Ctrl+1` — asking for Issues & PRs by name — drops the label and shows
everything again.

## Creating and deleting labels

In the Labels view, `Insert` creates one and `Delete` removes the selected one.
Right-click offers both, and File ▸ New Label… / Delete Label… reach them from
the menu bar.

A new label needs a name. The description and the colour are optional; leave the
colour blank and GitHub picks one, or give it six hex digits and GHManage checks
them before it asks GitHub for anything. The form labels every field for a
screen reader and opens with focus in the name box.

Deleting is the one that deserves a warning: **a deleted label is stripped from
every issue and pull request that carries it, and GitHub offers no undo.**
GHManage names the label and says so before it does anything, and does nothing
unless you answer yes.

## Favorites moved to Ctrl+9

Labels took `Ctrl+8` and Favorites moved down to `Ctrl+9`. The numbers follow the
order of the View ▸ View Mode menu and are printed next to each item there, which
is the whole point of them — so the menu still tells you the answer.

| Key | View |
|-----|------|
| `Ctrl+1` | Issues & PRs |
| `Ctrl+2` | Branches |
| `Ctrl+3` | Commits |
| `Ctrl+4` | Tags |
| `Ctrl+5` | Releases |
| `Ctrl+6` | Workflows |
| `Ctrl+7` | Workflow Runs |
| `Ctrl+8` | Labels |
| `Ctrl+9` | ★ Favorites |

## A note on forks

On a fork, the labels come from the upstream repository — the same place the
fork's issues and pull requests come from, since forks have issues disabled.
That means the labels you see always match the issues you are reading.

## Install

1. Install the [GitHub CLI](https://cli.github.com/) and sign in — GHManage uses
   it for every GitHub request:

   ```
   gh auth login
   ```

2. Download **GHManage-win-Setup.exe** below and run it.

It installs for your account only, with no administrator prompt, and adds a Start
menu shortcut. **From here on it updates itself**: a new version downloads
quietly in the background and is applied the next time you start the app. Help ▸
Check for Updates checks on demand and offers to restart.

Windows may show a SmartScreen "unknown publisher" warning until code signing is
switched on — choose **More info → Run anyway**.

**GHManage-win-Portable.zip** is the same app as a folder you can run from
anywhere. It does not update itself.

If you already have GHManage installed, you do not need to download anything —
this version will arrive on its own.

## Requirements

- Windows 10 or 11, 64-bit
- The [GitHub CLI](https://cli.github.com/), installed and authenticated with
  `gh auth login`. GHManage never asks for or stores credentials of its own.
  Creating and deleting labels needs write access to the repository, which is
  the same permission the GitHub website would ask of you.

Your favorites and pinned repositories live in `%APPDATA%\ghmanage` and are kept
across updates.

## Downloads

| File | Use it if |
|------|-----------|
| `GHManage-win-Setup.exe` | You want GHManage installed and updating itself |
| `GHManage-win-Portable.zip` | You want a folder to run from anywhere, no install, no updates |

The remaining files (`*.nupkg`, `RELEASES`, `releases.win.json`,
`assets.win.json`) are the update feed the installed app reads. Leave them alone.
