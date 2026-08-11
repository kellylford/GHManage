# GHManage 0.7.0

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

This release adds the last part of a repository GHManage could not show you: the
website it publishes.

## GitHub Pages

Press `Ctrl+0` on a repository that publishes a site and you get its publish
history — one row per publish, with whether it succeeded, the commit it came
from, who pushed it, and how long it took. The status bar carries the address the
site lives at, its current state, and the branch and folder it is published from.
The details panel adds the rest: whether HTTPS is enforced, any custom domain,
whether the site is public, whether it has a custom 404 page.

If the repository has no site, GHManage says so instead of showing you an empty
list you have to interpret.

Pages is on `Ctrl+0` rather than in among the other repository views, because
slotting it into the middle would have shifted the number of every view below it.
The ones already in your fingers stay where they are.

## Browsing the pages

From the publish history, `Enter` opens **Published Pages** — every file the site
serves, each listed with the address it is served at. `Enter` on one opens it in
your default browser. `S` opens the site's home page from either view, and
`Backspace` returns to the publish history. The Actions menu has **Open Published
Site** as well, enabled once a site is found.

`F` favorites a page the same as anything else, so a page you check often is one
keystroke away from any repository you happen to be in.

## What the list can and cannot tell you

GitHub has no API that answers "what does this site serve", so GHManage works it
out from the branch the site publishes from. That is exact in the common cases
and an informed guess in two others, and the details panel tells you which one
you are looking at rather than leaving you to find out from a broken link.

**Jekyll sites serve Markdown as HTML.** A file stored as `guide/setup.md` is
served at `guide/setup.html`, and the address GHManage lists is the one that
works. A site with a `.nojekyll` file skips Jekyll and is served exactly as
committed, so the two match.

**A site built by Actions is listed from its source, not its output.** GitHub
publishes those through a workflow, and the workflow decides what actually ships
— possibly a subset of the files listed, possibly something it generated that is
not in the repository at all. For sites GitHub builds itself, the list is what is
served.

The publish history has the same split. Sites GitHub builds report a full build
log, with durations and the error message when one fails. Sites built by Actions
have no build log at all, so their history is read from their deployments
instead, which record a state but not a duration.

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
