# GHManage 0.6.3

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

One bug fix, and it is the kind worth explaining.

## A slow fetch can no longer land in the wrong view

Every list in GHManage is fetched on a background thread so the window stays
responsive. Nothing cancels a `gh` call once it has started, though, and until now
nothing checked whether the answer was still wanted when it arrived.

So if you selected a large repository and pressed `Ctrl+8` before its issues
finished loading, the issues would arrive a few seconds later and fill the Labels
list anyway — a hundred blank rows sitting under the Label, Description, and
Colour headings, with a status bar cheerfully reporting "100 issues, 0 PRs". The
data was fine; it was simply being poured into the wrong container. Refreshing
fixed it, once you worked out what had happened.

This affected every view, not just Labels. The bigger the repository and the
faster you move, the easier it was to hit — which is to say it hit exactly the
people the app is built for.

Every list load now carries a token, and results whose token is stale are
discarded. A failed fetch in a view you have left no longer replaces the status
of the view you are looking at, and `Go To Issue` no longer inserts into a list
that is no longer on screen.

## Everything else

No other changes. 0.6.2 turned on code signing; 0.6.1 added the Actions menu and
`Ctrl+I` / `Ctrl+D`.

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

This release is signed, so Windows can name the publisher rather than warning
about an unknown one. SmartScreen also weighs reputation, so a mild prompt may
persist for a while on a signing identity this new.

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
