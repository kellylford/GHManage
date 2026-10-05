# GHManage 0.9.0

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

This release reaches past your own repositories. You can add the repositories
you have starred or are watching to the repository list, and a new Activity view
shows your GitHub feed.

## Activity

Activity is the feed github.com shows on your dashboard: what happens in the
repositories you star or watch, and what the people you follow do. That covers
pushes, pull requests, issues, comments, reviews, releases, stars and forks,
newest first and across every repository.

Open it from **Activity** near the top of the repository list, with
`Ctrl+Shift+A` (`Cmd+Shift+A` on a Mac), or from View ▸ View Mode ▸ Activity.
The repository you were in stays selected, so `Ctrl+1` takes you back to it.
Each row says who, what, which repository, what it was about, and when, in your
local time. The details panel gives the whole event as one sentence, followed by
the comment, review or description when there is one.

| Key | Action |
|-----|--------|
| `Enter` | Open the issue, pull request, comment, release or commits on GitHub |
| `G` | Open the event's repository here in GHManage. `Backspace` brings you back to the same event |
| `F` | Favorite the issue, pull request, release or discussion the event is about |
| `Ctrl++` | Load older events |

`G` also works from the details panel, and is on the Actions menu as Go to
Event's Repository (`Ctrl+Shift+G`).

GitHub keeps only the latest 300 events from the last 90 days. The first 100 are
loaded, `Ctrl++` loads 100 more at a time and puts you on the first of them, and
the status bar tells you when there are no more.

## Starred and watched repositories in the repository list

View ▸ Repository List has two new settings, Show Starred Repositories and Show
Watched Repositories. Each adds that list after your own repositories, and
GHManage remembers your choice. Both are off until you turn them on.

Every added repository says why it is there, after its name:

- `nvaccess/nvda (starred)`
- `owner/name (watching)`
- `(starred, watching)` for a repository on both lists

Typing a letter still jumps by owner name. GitHub watches your own repositories
automatically, so the watched list only adds repositories that belong to other
people. Your own repositories appear first, and the status bar tells you how many
starred and watched ones were added once they arrive.

## Also fixed

With a quick filter on (`Ctrl+F`), the details panel and keys like `Enter`, `F`,
`C` and `O` could act on a different item from the one you had selected,
because the filtered list and the full list were mixed up. They now always act
on the item you are on, in every view.

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
