# GHManage v0.2.2 Release Notes

GHManage is an accessible, keyboard-first wxPython desktop app for browsing and
managing GitHub repositories — issues, pull requests, and the git/Actions side
of a repo — built to work well with screen readers.

## Download

| Download | When to use |
|----------|-------------|
| **`GHManage-win-Setup.exe`** — installer | **Start here.** Installs per-user (no administrator prompt) and keeps itself up to date automatically. |
| **`GHManage-win-Portable.zip`** — portable app folder | No installation. Unzip anywhere and run `ghmanage.exe`. Does not update itself. |

The other files on this page (`.nupkg`, `RELEASES`, `releases.win.json`,
`assets.win.json`) are the update feed. The app downloads them itself — you do
not need them.

Both downloads include the Python runtime and wxPython, so you do not need to
install Python separately. You do need the
[GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated
(`gh auth login`).

Windows will show a SmartScreen "unknown publisher" warning — these builds are
not code-signed yet. Choose **More info**, then **Run anyway**.

---

## New: GHManage updates itself

This is the headline change, and the reason for the new installer.

Install once with `GHManage-win-Setup.exe` and you should not have to think
about updating again. Shortly after startup GHManage quietly checks for a new
version. If it finds one it downloads it in the background and installs it the
**next time you start the app**, before any window appears.

Deliberately, the startup check **never interrupts you**:

- It does not open a dialog and does not steal focus.
- It announces itself in the status bar — "GHManage 0.2.3 downloaded — it will
  be installed next time you start GHManage" — and otherwise leaves you alone.
- It never restarts the app out from under you.

If you would rather check on demand, **Help → Check for Updates…** does so and
tells you either way. That one is user-initiated, so it does offer a dialog with
**Restart Now** if you want the update immediately, or **Later** to let it land
on the next launch.

**Help → About GHManage** reports the version you are running.

### Where it installs

The installer is per-user: GHManage goes into your local application data
folder, adds a Start Menu entry, and never asks for administrator rights. That
last part matters for updating — because nothing needs elevation, updates can
install silently instead of prompting you every time.

The portable zip is unchanged in spirit from the old `ghmanage.exe` download:
copy it where you like and run it. It simply cannot update itself, and the app
will tell you so if you use Help → Check for Updates.

### If an update ever goes wrong

Update activity is logged to `%APPDATA%\GHManage\ghmanage-update.log`. Starting
GHManage with `--debug` makes that log more detailed.

## Also in this release

- New command-line options: `--version` prints the version and exits, `--debug`
  turns on verbose update logging, and `--update-feed <folder>` points the update
  check at a local folder instead of GitHub (used for testing the update cycle
  offline).
- A **Help** menu has been added, with **Check for Updates…** and **About
  GHManage**.

## Note for existing users

If you are running the portable `ghmanage.exe` from v0.2.1 or earlier, it cannot
update itself to this release — that is exactly the limitation this release
fixes. Download `GHManage-win-Setup.exe` once, and updates are automatic from
here on. You can delete the old `ghmanage.exe` afterwards; your pinned repos and
favorites are stored separately and are not affected.
