# GHManage 0.8.0

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

The status bar has always been where GHManage tells you things. This release
makes it somewhere you can go.

## F6 moves between panes

`F6` moves focus to the next part of the window — the repository list, the item
list, the details panel, the status bar, and round to the repository list again.
`Shift+F6` goes the other way.

`Tab` is unchanged. It still moves between the repository list, the item list
and the details panel, and never stops on the status bar.

On a Mac keyboard, press `fn+F6` unless you have set the function keys to behave
as standard keys.

## Arrow through the status bar

The status bar used to be one long line. It is now split into items, and once
`F6` has put you on it, `Left` and `Right` move from one item to the next,
wrapping round at either end:

- **The message** — what the view is showing, or the last thing GHManage told you.
- **Keys** — the keys that work in the current view.
- **Filter** — the quick filter and how many rows it matches, while one is set.
- **Mode** — Quick mode or Full mode.
- **Update** — when an update has been found. See below.

An item with nothing to say is not on the bar, so every stop has something on
it. Your screen reader's own command for reading the status bar still reads the
whole thing.

## The filter and mode stay put

Because they were part of that one line, the filter and the list mode vanished
the moment anything else was announced — open an item in the browser and the
filter count was gone until the list next loaded. They are separate items now and
stay on the bar for as long as they are true.

## An update you can act on

When GHManage finds an update at startup it downloads it quietly and installs it
the next time you start the app. It used to say so once, in a message the next
announcement overwrote. The update now stays on the status bar as **GHManage
X.Y.Z ready to install**. Press `Enter` or `Space` on it to restart into the new
version now, or choose Later to keep working.

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
