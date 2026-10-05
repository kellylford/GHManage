# GHManage 0.8.1

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

A small release that makes web addresses easier to copy, and fixes moving
between comments.

## Addresses on a line of their own

The details panel used to show an address as `URL: https://…` on one line, so
copying it meant selecting the line and then trimming off the label. The label
is now on one line and the address on the next. Arrow down to the address,
press `Home`, then `Shift+End`, and copy — you get just the address.

This applies everywhere the details panel shows an address: issues, pull
requests, branches, commits, tags, labels, releases, release assets, workflows,
workflow runs, published pages, and favorites. The Pages publish history shows
its site address the same way, under **Site:**.

An item with no address now says **(none)** rather than leaving the line blank,
and a favorited Pages file no longer shows its address twice.

## Moving between comments

`Alt+N` and `Alt+P` move between the comments on an issue or pull request. When
the description ran to more than one line — which is most of the time — they
selected the wrong text, landing short of the comment you asked for. They now
select exactly the comment, starting at its "Comment N of M" heading. On a Mac
the keys are `Option+N` and `Option+P`.

## Before you start

GHManage drives the [GitHub CLI](https://cli.github.com/), so install it and sign
in first:

```
gh auth login
```

GHManage never asks for or stores credentials of its own — every request goes
through `gh`.

## Updating

If you already have GHManage installed you do not need to download anything; this
version will arrive on its own.

## Downloads

| File | Use it if |
|------|-----------|
| `GHManage-win-Setup.exe` | Windows, installed and updating itself |
| `GHManage-win-Portable.zip` | Windows, a folder to run from anywhere, no install, no updates |
| `GHManage-osx.dmg` | macOS, drag to Applications |
| `GHManage-osx-Portable.zip` | macOS, unzip it yourself |

The remaining files (`*.nupkg`, `RELEASES`, `releases.win.json`,
`assets.win.json`, `releases.osx.json`, `assets.osx.json`) are the update feed
the installed app reads. Leave them alone.

## Requirements

- Windows 10 or 11, 64-bit — or an Apple Silicon Mac on macOS 11 or newer
- The [GitHub CLI](https://cli.github.com/), installed and authenticated with
  `gh auth login`
