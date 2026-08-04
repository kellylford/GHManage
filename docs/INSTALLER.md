# Installer & Automatic Updates

GHManage is packaged with [Velopack](https://velopack.io/). `build.bat installer`
runs PyInstaller then `vpk pack`, emitting `installer/Releases/` (gitignored):

- `GHManage-win-Setup.exe` — the installer users download
- `GHManage-win-Portable.zip` — the portable app folder, for users who do not
  want an install. It cannot self-update.
- `GHManage-<version>-full.nupkg` — the update package the in-app updater consumes
- `GHManage-<version>-delta.nupkg` — binary delta from the previous release
  (only generated when the previous release's packages are present; CI fetches
  them with `vpk download github` before packing, local builds usually produce
  full packages only)
- `RELEASES`, `releases.win.json`, `assets.win.json` — the release feed metadata
  the updater reads

`vpk` is a .NET global tool, **not** a Python package: `dotnet tool install -g vpk`.
The `velopack` PyPI package is only the in-app client library.

## Key facts

- **The build must be `--onedir`, not `--onefile`.** Velopack replaces an app
  *folder* in place. A onefile exe re-extracts the whole ~17 MB bundle on every
  launch — including the short-lived hook processes Velopack runs during an
  update, which overran Velopack's 15-second hook timeout and got killed in
  testing. Onefile also destroys delta efficiency: the app is one opaque blob,
  so a delta rewrites all of it. Measured on the same change, onedir produced a
  delta of 3 patched files out of 34; onefile patched the entire binary.
- **`--hidden-import velopack` is required.** `updater.py` imports velopack
  lazily inside functions so the app still runs from a source checkout without
  it. That hides the import from PyInstaller's static analysis, and without the
  flag the module is silently missing from the build — the updater then logs
  "velopack not installed; updates disabled" and never updates anything.
- **Per-user install.** `--instLocation PerUser` installs to
  `%LocalAppData%\GHManage\current\`, with no elevation prompt. Background
  updates into Program Files from a non-elevated process are not verified, so
  the machine-wide option stays off.
- **Automatic updates.** The startup check runs 2 seconds after the main window
  appears, in a background thread. A found update is downloaded silently and
  **applied on the next launch** by `updater.bootstrap()`
  (`set_auto_apply_on_startup(True)`), before any window is shown. The user
  never has to act. Help ▸ Check for Updates offers an immediate restart.
- **The startup check never shows a dialog.** It announces in the status bar
  ("… will be installed next time you start GHManage"). Only the user-initiated
  Help menu check prompts. This is deliberate: a modal raised at startup steals
  focus, and an app that restarts itself mid-session is hostile — especially
  with a screen reader.
  Note the ordering constraint in `ghviewer.py`: the check is scheduled *after*
  `self.Show()`. A `wx.MessageDialog.ShowModal()` raised against a frame that
  has not been shown returns immediately with the affirmative ID instead of
  waiting for input — during development that silently auto-confirmed "Restart
  Now" and restarted the app with no user involvement.
- **Version string must be SemVer.** `vpk pack --packVersion` rejects 4-part
  versions. `version.py` is the single source of truth; CI fails the release if
  the tag and `version.py` disagree.
- **Update logging** goes to `%APPDATA%\GHManage\ghmanage-update.log` (and
  Velopack's own log to `%LocalAppData%\velopack\velopack_GHManage.log`). Note
  this is `%APPDATA%`, not `%LocalAppData%` — the latter is the Velopack-managed
  install directory, and a log file held open in there blocks uninstall cleanup.
- **Code signing** is wired to Azure Trusted Signing and switches on with the
  `AZURE_CLIENT_ID` secret. See below.

## Release flow (CI)

On a `v*` tag, `.github/workflows/ghmanage.yml`:

1. Verifies the tag matches `version.py`.
2. Builds with PyInstaller (`--onedir --hidden-import velopack --hidden-import yaml`).
3. `vpk download github` — fetches the previous release's packages so a delta
   can be built. Allowed to fail (the first Velopack release has no prior).
4. `vpk pack` — builds the setup exe, full/delta packages, and feed metadata.
5. Uploads Setup.exe, the portable zip, the packages, and the three feed files.

The feed files are required assets, not extras. A release missing `RELEASES`,
`releases.win.json` or `assets.win.json` strands every installed client
*silently* — and a broken updater cannot fix itself in the field.

**The previous version's `.nupkg` is uploaded too, on purpose.** `vpk pack` writes
an entry for every package it saw into `RELEASES` / `releases.win.json`, so
deleting the older package leaves the published feed pointing at an asset the
release does not carry. The workflow used to delete it; v0.4.0 shipped that way
and its feed still references `GHManage-0.3.0-full.nupkg`. Harmless for the
normal delta path — Velopack takes the delta and never fetches the older full
package — but fixed from v0.4.1 on.

## Testing updates locally (no GitHub release needed)

`--update-feed <path>` points the update check at a local folder of `vpk pack`
output instead of GitHub Releases, so the whole cycle can be verified offline.
Everything except the GitHub fetch itself runs the production code path.

1. Set `version.py` to `0.2.1`, run `build.bat installer`.
2. **Copy `installer\Releases\GHManage-win-Setup.exe` aside** — `vpk pack`
   overwrites it on every pack, so the next step would otherwise leave you
   installing the *new* version and testing nothing.
3. Run the copied Setup.exe. It installs to `%LocalAppData%\GHManage`.
4. Bump `version.py` to `0.2.2` and run `build.bat installer` again **without
   deleting `installer\Releases`** — the previous full package being present is
   what lets the delta be generated.
5. Launch the installed copy against the local feed:
   `%LocalAppData%\GHManage\current\ghmanage.exe --update-feed <repo>\installer\Releases`
   The status bar announces the update; the log records "update 0.2.2
   downloaded". The app keeps running on 0.2.1 — this is correct.
6. Quit, then launch again from the Start Menu. The update is applied before the
   window appears; Help ▸ About reads 0.2.2.

Add `--debug` for verbose update logging.

## Testing the live GitHub path (one-time, two real releases)

The local cycle proves everything except Velopack's `GithubSource` resolving and
downloading real release assets. That link cannot be tested until **two**
published releases exist. Do it once, on your own machine, before relying on
updates to ship an urgent fix:

1. Tag and publish a baseline release.
2. **Check the release page by eye** for `RELEASES`, `releases.win.json`,
   `assets.win.json` and the `-full.nupkg`. A missing feed is the most likely
   failure and the one that strands clients silently.
3. Install from that release's Setup.exe — not a local build.
4. Bump `version.py`, add `docs/release-notes-vX.Y.Z.md`, tag, and publish. It
   must be a **normal published release, not a draft or prerelease** — the
   client uses `GithubSource(..., prerelease=False)` and will not see one.
5. Launch the installed baseline, wait for the status bar announcement, quit,
   relaunch, and confirm the new version.
6. If nothing happens, read `%APPDATA%\GHManage\ghmanage-update.log`, then
   recheck step 2.

Do not delete or reuse the test release — a machine that already updated to it
would point at missing assets, and reusing the number muddles the delta chain.

## Code signing

The workflow is wired for **Azure Trusted Signing**, reusing the same account
QuickMail signs with — signing account `kellylford` (resource group `IdeaPlace`,
eastus), certificate profile `kellyford-public`, endpoint
`https://eus.codesigning.azure.net/`. Nothing new needs to be purchased.
`azure/login@v3` exchanges the workflow's OIDC token for Azure credentials and
Velopack's bundled signtool authenticates through that session, so no
certificate or long-lived secret is ever stored in the repo.

**Signing is off until `AZURE_CLIENT_ID` is set.** Every signing step is gated on
it; with no secret the release still builds and publishes, unsigned, and the pack
step emits a workflow warning. Unsigned builds install and auto-update perfectly
well — signing only removes the SmartScreen "unknown publisher" warning on first
run. This gating is deliberate: a half-configured signing setup should not be
able to block a release.

### The signing identity

The app registration that signs is **`github-artifact-signing`**, app ID
`da30172c-ceb4-412c-b1fa-3c3a3808c631`. It is the principal holding *Artifact
Signing Certificate Profile Signer* on the `kellylford` account.

There is a separate app registration literally named `QuickMail`
(`bcdc84f1-…`) — it is **not** the signing identity and has no rights on the
signing account. Putting its ID in `AZURE_CLIENT_ID` authenticates fine and then
fails at pack time with an authorization error, which is a slow way to discover
the mistake.

### Current state

Done:

- The **`azure-signing` environment** exists on `kellylford/GHManage`, with no
  protection rules. It must stay unprotected; protection rules would make every
  build, including PRs, wait for approval.
- **`environment: azure-signing`** is declared on the `build` job. This is what
  pins the OIDC subject to a fixed string — the tenant does not support wildcard
  tag subjects, which is the whole reason an environment is involved.
- Repo secrets **`AZURE_TENANT_ID`** (`793722c2-ea04-49a3-8183-af139211b24f`)
  and **`AZURE_SUBSCRIPTION_ID`** (`566d6139-16a2-48b7-8aa5-fa5ebe17b28f`).
- **The role assignment**: `github-artifact-signing` holds *Artifact Signing
  Certificate Profile Signer* on
  `/subscriptions/566d6139-…/resourceGroups/IdeaPlace/providers/Microsoft.CodeSigning/codeSigningAccounts/kellylford`.
- **Both federated credentials** on `github-artifact-signing`, issuer
  `https://token.actions.githubusercontent.com`, audience
  `api://AzureADTokenExchange`:

  | Name | Subject |
  |------|---------|
  | `gh-ghmanage-signing` | `repo:kellylford/GHManage:environment:azure-signing` |
  | `gh-ghmanage-immutable` | `repo:kellylford@44002405/GHManage@1295265237:environment:azure-signing` |

  Two are needed because GitHub may issue either the plain subject or the
  immutable one built from the numeric owner and repo IDs. Every other signed
  repo in this tenant (QuickMail, WeatherFast, LiveCaptions, Image-Description-
  Toolkit) carries the same pair; matching only one leaves signing working until
  the day the other form is issued. The numeric IDs come from
  `gh api repos/kellylford/GHManage --jq '{id, owner_id: .owner.id}'`.

- Repo secret **`AZURE_CLIENT_ID`** = `da30172c-ceb4-412c-b1fa-3c3a3808c631`, the
  `github-artifact-signing` app ID. Set last, on purpose: it is the switch that
  turns the signing steps on, and switching them on before the federated
  credentials existed would have failed `azure/login` — which has no
  `continue-on-error` — taking the whole build job with it and publishing nothing
  at all for that tag. With the secret unset, every intermediate state shipped a
  working unsigned release.

Signing has been live since **v0.6.2**. Every `v*` tag signs automatically.

To confirm a release signed, check the pack step logged `Signing with Azure
Trusted Signing.` rather than the `AZURE_CLIENT_ID not set` warning, and:

```powershell
(Get-AuthenticodeSignature .\GHManage-win-Setup.exe) | Format-List Status, SignerCertificate
```

Signing applies to what a tag builds; it does not reach back. **v0.6.1 and
earlier remain unsigned**, so anyone downloading those still meets SmartScreen.

`.github/workflows/quickmail.yml` in the QuickMail repo is the reference
implementation for all of this.
