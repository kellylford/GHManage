# GHManage 0.4.0

GHManage is a Windows desktop app for reading and managing your GitHub
repositories from a fast, keyboard-driven list.

This release fills in the last gap in running workflows from the app: workflows
that ask for input now ask you for it too.

## Running a workflow with inputs

Many workflows take inputs — a target architecture, an environment to deploy to,
a flag to turn something on. GHManage could already start a workflow on the
branch of your choosing, but it always ran with whatever defaults the workflow
declared. There was no way to pick.

Now, when a workflow declares inputs, GHManage asks for them:

1. Choose the workflow and press `R`.
2. Pick the branch to run on.
3. If the workflow takes inputs, a form appears — one field per input, using the
   workflow's own descriptions as labels and its declared defaults as starting
   values.
4. Press Enter to run.

Each input gets the control that suits it. A list of allowed values becomes a
combo box, a true/false input becomes a checkbox, and everything else is a text
field. Required inputs will not let you continue while empty, and the message
names the field that needs filling in. Workflows with no inputs behave exactly as
before — you pick a branch and it runs, with nothing extra in the way.

The status bar reports what was started and with which values, so you can confirm
the run went out the way you intended without switching to the browser.

Every part of the form is keyboard-reachable and properly labelled: the fields
are generated on the fly from the workflow file, so each one is explicitly given
the name a screen reader reads, rather than being left to whatever the toolkit
would guess.

## Also in this release

- A workflow that only mentions `workflow_dispatch` in a comment is no longer
  treated as manually runnable. GHManage used to offer the run and GitHub would
  reject it.
- The inputs are read from the branch you chose, not from the default branch. A
  branch that adds or changes an input now shows the right form — previously it
  would have shown the default branch's fields and quietly discarded anything you
  entered.

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

Windows may show a SmartScreen "unknown publisher" warning until code signing is
switched on — choose **More info → Run anyway**.

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
