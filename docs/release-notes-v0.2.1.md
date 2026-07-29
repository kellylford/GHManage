# GHManage v0.2.1 Release Notes

GHManage is an accessible, keyboard-first wxPython desktop app for browsing and
managing GitHub repositories — issues, pull requests, and the git/Actions side
of a repo — built to work well with screen readers.

## Download

| Download | When to use |
|----------|-------------|
| **`ghmanage.exe`** — standalone portable executable | No installation required. Copy it anywhere and run. |

The executable includes the Python runtime and wxPython — you do not need to install Python separately.

You do need the [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`).

---

## New: release download counts

GitHub records how many times every file attached to a release has been
downloaded, and shows that number nowhere in its web interface. GHManage now
surfaces it.

**In the Releases view**, a **downloads** column gives the total across all files
attached to each release, and the status bar totals every release currently
loaded — press **Ctrl++** to load more and the total grows with the list. An
**assets** column is available too, if you turn it on under **View → Columns**.

**Press Enter on a release** to drill into its individual files, ordered
most-downloaded first, because the count is the reason you opened the view. The
status bar reports that release's total. **Backspace** returns to the releases
list, the same way it steps back out of a workflow run's artifacts. **Enter** on
a file downloads it in your browser.

**The details panel** breaks a release down file by file without leaving the
list, so arrowing through releases reads out each one's totals in turn.

### Reading the numbers

The counts are worth a little care. A download is an HTTP request, not a person —
nothing deduplicates by user. The count is a **lifetime running total** with no
date breakdown, and no GitHub API offers one, so a trend has to be built by
recording the numbers over time and comparing them.

Most usefully: if your release contains several files, they describe **different
groups of people** and should not be averaged. An installer counts people
acquiring the software; an updater package counts installs that were still
running when you shipped the next version. The second is a far better measure of
whether anyone stayed.

There is a full write-up of the method and the interpretation traps at
[How to Get GitHub Release Download Numbers](https://kellylford.github.io/QuickMail/github-release-download-numbers.html).

## Also in this release

- Source archives ("Source code (zip/tar.gz)") are not counted anywhere by
  GitHub — they are not release assets — so they correctly do not appear in the
  new view.
- Byte-size formatting is now shared between artifacts and release assets rather
  than duplicated.

## Keybindings added

| Key | Action |
|-----|--------|
| `Enter` (in Releases view) | Drill into the selected release's files and download counts |
| `Enter` (in Release Assets view) | Download the selected file in your browser |
| `Backspace` (in Release Assets view) | Step back to the releases list |
