# GHManage 0.9.1

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

GHManage now lives at [TheIdeaPlace/GHManage](https://github.com/TheIdeaPlace/GHManage),
and this release brings back repositories that had dropped out of the list
after moving into an organization.

## Your organizations' repositories are in the list

The repository list used to show only repositories your own account owns, so
any you moved into an organization, or that a team you belong to works on,
weren't there. It now lists those too, mixed in with your own, most recently
pushed first. Each one reads with its organization's name in front, for
example "TheIdeaPlace/GHManage — …".

You get up to 100 of your own repositories and up to 100 from organizations, so
a busy organization can't push your own off the list. An organization
repository is listed when you have more than read access to it, for example
through a team that can write to it. One you can only read through the
organization's base permission isn't; open it by address
(`Ctrl+Shift+O`) to add it.

If your organization's repositories still don't appear, check that `gh` can
read your organizations:

```
gh auth refresh -h github.com -s read:org
```

When `gh`'s sign-in has expired, the status bar now says so, "Bad credentials.
Run gh auth login to sign in again.", rather than showing an empty list.

## GHManage has moved

The project is now at `github.com/TheIdeaPlace/GHManage`, and the user guide
(Help ▸ User Guide, `F1`) at
[theideaplace.github.io/GHManage](https://theideaplace.github.io/GHManage/).
Old addresses forward to the new ones, and installed copies keep updating
without you doing anything.

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
