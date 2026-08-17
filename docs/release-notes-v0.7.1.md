# GHManage 0.7.1

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

**GHManage runs on the Mac.** That is the whole of this release. Nothing about
the Windows app changes — same features, same keys, same update path.

## macOS

Download **GHManage-osx.dmg** below, open it, and drag GHManage to Applications.
It is the same app you know: the repository list, issues and pull requests,
branches, commits, tags, releases, workflows, labels, Pages, favorites, and every
keystroke that drives them.

Like the Windows build, **it updates itself**. A new version downloads quietly in
the background and is applied the next time you start the app; Help ▸ Check for
Updates checks on demand. On the Mac that works wherever you keep the app —
`/Applications`, your own `~/Applications`, or anywhere else — because a Mac app
bundle carries its own updater with it.

**GHManage-osx-Portable.zip** is the same app if you prefer to unzip it
yourself. Both update themselves.

Apple Silicon only — an M1 or later, on macOS 11 Big Sur or newer. There is no
Intel build: the GUI toolkit GHManage is built on ships separate builds per
processor rather than one that covers both.

## VoiceOver

The list of issues, branches, commits and everything else is a real macOS table,
so VoiceOver reads it properly — the list itself, its rows, and the columns you
have turned on.

This is worth calling out because it very nearly was not the case. The list
control the Windows build uses has no native Mac equivalent in the toolkit;
asking for one there quietly gives you a plain view that draws rows on itself and
tells the accessibility system nothing. It looks correct and reads as an empty
space. Tabbing to it announced nothing at all. The Mac build uses a genuine table
instead, which is what VoiceOver needs to see.

Full and Quick list modes both work as they do on Windows. Quick reads compact
rows; Full includes the field names.

## Before you start

GHManage drives the GitHub CLI, so install and sign in to that first:

```
brew install gh
gh auth login
```

An app opened from Finder does not inherit the `PATH` from your Terminal, so
GHManage looks for `gh` in the usual Homebrew and MacPorts locations itself. If
you keep it somewhere unusual, set `GHMANAGE_GH_PATH` to its full path.

GHManage never asks for or stores credentials of its own — every request goes
through `gh`.

Your favorites and pinned repositories live in `~/.config/ghmanage`.

## Windows

Unchanged. If you already have GHManage installed you do not need to download
anything; this version will arrive on its own.

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
