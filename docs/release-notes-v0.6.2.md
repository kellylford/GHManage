# GHManage 0.6.2

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

**This is the first signed release.** The app itself is unchanged from 0.6.1.

## No more "unknown publisher"

Every release until now was unsigned, so Windows met you at the door with a
SmartScreen warning: a blue box saying "Windows protected your PC" and an
"unknown publisher" line, with the button that actually installs the app hidden
behind **More info**. That was never a sign anything was wrong — it is what
Windows says about any program whose author it cannot identify — but "unknown
publisher" is a poor first impression, and telling people to click through a
security warning is a bad habit to teach.

`GHManage-win-Setup.exe` and the app's own binaries are now signed through Azure
Trusted Signing. Windows can name the publisher, and the first-run warning goes
away.

Two honest caveats:

- **SmartScreen also weighs reputation, not just signature.** A brand-new signing
  identity can still draw a milder warning until Microsoft has seen the
  certificate on enough installs. This gets better on its own; nothing to do.
- **Signing does not reach backwards.** 0.6.1 and earlier are still unsigned on
  the releases page. If you have one of those, updating to 0.6.2 is the fix.

## Everything else

No functional changes. If you are coming from 0.6.0, the
[0.6.1 notes](https://github.com/kellylford/GHManage/releases/tag/v0.6.1) cover
the Actions menu, `Ctrl+I` / `Ctrl+D`, and the label-key fixes.

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
