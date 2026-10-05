# GHManage 0.8.2

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

This release fixes Go To Issue for issues and pull requests that are not in the
list you are looking at.

## Go To Issue finds items that are not in the list

Go To Issue (`Ctrl+G`, or `Cmd+G` on a Mac) jumps to an issue or pull request by
number. When that number was already in the list it worked. When it was not —
a closed issue while you were viewing open ones, or something older than the
list goes back — GHManage said it was fetching it and then never finished. It
now fetches the item, adds it to the list, selects it, and moves you to its
details.

## Pull requests arrive as pull requests

When Go To Issue did fetch a pull request, it showed it as an issue, without its
branches or the size of its changes. It now shows the full pull request
details.

## The real reason when Go To Issue cannot fetch

If GitHub could not be reached — you were offline, your `gh` sign-in had
expired, or the repository had gone — GHManage said the number did not exist.
It now says what actually went wrong, and keeps "not found" for numbers that
really are neither an issue nor a pull request.

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
