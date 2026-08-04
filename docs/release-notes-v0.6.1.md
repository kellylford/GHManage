# GHManage 0.6.1

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

0.6.0 added labels but hid the actions behind keys you had to find. This release
gives them a menu, better keys, and makes the ones that were already documented
actually work everywhere.

## An Actions menu

Everything that acts on what the list is showing now lives in one menu, whichever
view it belongs to: open in browser, close, reopen, comment, create and delete
labels, delete a workflow run, run a workflow on a branch, download an artifact,
select a branch, compare branches.

Several of these were previously reachable only by pressing Enter on the right
row or by finding the right-click menu, which meant discovering them by accident.
Now there is one place to look.

The menu answers "what can I do here?" rather than listing everything and letting
you find out by trying. Entries are labelled for the current view and greyed out
where they do not apply — **Delete** reads "Delete Label…" in the Labels view and
"Delete Workflow Run…" in Workflow Runs, so the menu never offers a bare "Delete"
whose object you have to guess.

## Ctrl+I and Ctrl+D

Insert is an awkward key — small, easy to miss, and missing outright on some
compact keyboards. It still works, but it is no longer the only way:

| Key | Action |
|-----|--------|
| `Ctrl+I` or `Insert` | Create a label |
| `Ctrl+D` or `Delete` | Delete the selected label, or the selected workflow run |

`Ctrl+D` follows the same rule as the menu: it deletes whatever the current view
can delete, and does nothing in views where nothing can be.

## Insert and Delete now work from the details panel

The details panel for a label described Insert and Delete, but those keys only
worked while the list itself had focus. Reading the text put focus in the one
place the keys it described did nothing. They now work from anywhere in the
window, and the text says so. Delete in the Workflow Runs view gained the same
reach.

The label details panel now reads as a key list rather than a run of "press X to
Y" sentences, and names the label that Delete would remove.

## Smaller fixes

- The status bar no longer advertises `Ctrl+B=select branch` in the Labels, Tags,
  Releases, and other lists. That key only works in Commits; everywhere else it
  answered "Select Branch is only available in Commits view."
- The Workflow Runs status bar and details panel now mention that Delete deletes
  a run — that has always worked, but nothing said so.

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
