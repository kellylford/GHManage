# GHManage 0.9.0

GHManage is a desktop app for reading and managing your GitHub repositories from
a fast, keyboard-driven list.

This release reaches beyond the repository you have open. Your notifications,
a list of everything that needs you, and search across all of GitHub are in
GHManage now, and any GitHub link you paste opens in its own view. Pull
requests can be reviewed and merged, a failed workflow run says what failed,
and there are new issues, copy commands, watch settings and switching between
GitHub accounts.

The repository list keeps its familiar start — Favorites, Activity, Starred
Repositories, Watched Repositories — with the new Notifications and My Work
after them, then your saved searches.

## Notifications

**Notifications** is your GitHub inbox: the issues, pull requests, releases,
discussions and workflow runs GitHub has told you about, across every
repository. It is in the repository list after Watched Repositories, with how
many are unread, for example "Notifications (12 unread)". You can also press `Ctrl+Shift+N`
(`Cmd+Shift+N` on a Mac).

Each row says why you were told (review requested, mention, assigned, CI
activity and so on), what kind of thing it is, its title, the repository, when
it last changed, and whether it is read.

| Key | Action |
|-----|--------|
| `Enter` | Open an issue or pull request here in GHManage; `Backspace` brings you back. Anything else opens on GitHub |
| `M` | Mark read |
| `Delete` or `Ctrl+D` | Mark done |
| `U` | Unsubscribe from the thread |
| `I` | Include read notifications, or not |
| `G` | Open its repository here |

**Actions ▸ Mark All as Read** asks first. To see only some notifications, use
the quick filter (`Ctrl+F`): it matches the reason and the repository as well as
the title.

## My Work

**My Work** (`Ctrl+Shift+M`, and in the repository list after Notifications)
answers "what on GitHub needs me?": the open issues and pull requests, in every
repository, where your review is requested, you are assigned, you opened them,
or you are mentioned, each listed once under the first reason that applies.
`Enter` opens one here; `Backspace` comes back.

## Search GitHub

**File ▸ Search GitHub** (`Ctrl+Shift+F`) searches issues and pull requests, or
repositories, across all of GitHub. Type GitHub's own search language, so every
qualifier works: `is:open label:bug repo:nvaccess/nvda`, `review-requested:@me`,
`updated:>2026-01-01`, `language:python stars:>50`. The results are a list like
any other: `Enter` opens one here and `Backspace` comes back, `Ctrl++` loads
more.

`Ctrl+S` saves a search. It goes in the repository list, marked 🔍, where
`Enter` runs it again.

## Pull requests

On a pull request in the issues list, `K` lists its checks, failures first; `V`
reviews it — approve, request changes or comment — and `D` marks a draft ready
for review, or back to a draft. **Actions ▸ Pull Request** adds **Merge**,
offering only the ways the repository allows, and Request Reviewers and Update
Branch.

## What failed, in a workflow run

In Workflow Runs, `L` on a failed run gathers what failed into one text to read
from the top: which jobs failed and at which step, the errors GitHub flagged,
and the last 40 lines of each failed step's log, with colour codes and
timestamps taken out. `J` lists a run's jobs and their steps, and `Enter` on a
job opens its whole log at the first error. `E` reruns a run — all of it, or
only what failed — and `X` cancels one that is running.

## Open any GitHub address

**File ▸ Open Repository or Address** (`Ctrl+Shift+O`) now takes the address of
an issue, pull request, commit, release, workflow run or branch, as well as a
repository. GHManage opens the repository on the matching view with that item
selected. When the clipboard already holds a GitHub address, the box starts
with it filled in, so a link copied from an email is `Ctrl+Shift+O` and `Enter`.
Links to single items don't add their repository to your list; only a
repository's own address does.

## New issue

**Actions ▸ New Issue** (`Ctrl+N`, or `N` in the issues list) asks for a title
and a description in Markdown. `Ctrl+Enter` creates the issue, and the list
reloads with it selected. If you cancel, or GitHub refuses it, what you typed is
kept for next time.

## Copy

**Actions ▸ Copy** puts something about the item you are on onto the clipboard:

| Key | Copies |
|-----|--------|
| `Ctrl+Shift+C` | Its link |
| `Ctrl+Shift+L` | A Markdown link, such as `[#42 Fix the cursor](https://github.com/…)` |
| `Ctrl+Shift+T` | Its title |
| `Ctrl+Shift+I` | Its number, SHA, tag or name; the menu says which |
| `Ctrl+Shift+D` | Everything in the details panel |

With focus in the repository list, they copy that repository.

## Watch settings

**Actions ▸ Watch Settings** (`Ctrl+Shift+U`) sets how GitHub notifies you about
a repository: Participating and @mentions, All Activity, or Ignore. The first
time, GHManage will probably tell you `gh` needs one more permission, and give
you the command that adds it:

```
gh auth refresh -h github.com -s notifications
```

## Switch GitHub account

If `gh` is signed in to more than one github.com account, **File ▸ Switch
GitHub Account** (`Ctrl+Shift+K`) switches between them without a terminal.

## Also fixed

On a Mac, every list load raised an error behind the scenes when it moved to
the first row. Nothing visible depended on it, but it is gone.

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
