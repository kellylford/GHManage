# GHManage 0.5.0

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

This release makes moving between the views of a repository a single keystroke.

## Ctrl and a number switches views

A repository has a lot of faces — issues and PRs, branches, commits, tags,
releases, workflows, the runs of those workflows. Getting from one to another
meant walking the View menu into the View Mode submenu every time. Now each view
has a number:

| Key | View |
|-----|------|
| `Ctrl+1` | Issues & PRs |
| `Ctrl+2` | Branches |
| `Ctrl+3` | Commits |
| `Ctrl+4` | Tags |
| `Ctrl+5` | Releases |
| `Ctrl+6` | Workflows |
| `Ctrl+7` | Workflow Runs |
| `Ctrl+8` | ★ Favorites |

The numbers follow the order of the View ▸ View Mode menu and are shown next to
each item there, so there is nothing extra to memorize — the menu tells you. The
shortcuts work from anywhere in the window: the repository list, the item list,
or the details panel. You do not have to move focus first.

The status bar names the view as it loads, so the switch is confirmed out loud
rather than only appearing in the list. Every view except Favorites belongs to a
repository; press one of these with no repository selected and GHManage says
"Select a repository first" and stays where it is, instead of dropping you into
an empty list.

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

Your favorites and pinned repositories live in `%APPDATA%\ghmanage` and are kept
across updates.

## Downloads

| File | Use it if |
|------|-----------|
| `GHManage-win-Setup.exe` | You want GHManage installed and updating itself |
| `GHManage-win-Portable.zip` | You want a folder to run from anywhere, no install, no updates |

The remaining files (`*.nupkg`, `RELEASES`, `releases.win.json`,
`assets.win.json`) are the update feed the installed app reads. Leave them alone.
