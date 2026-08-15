#!/bin/bash
# ============================================================================
# Build the GHManage drag-to-Applications disk image
# ============================================================================
# Usage:
#   bash scripts/make_dmg.sh
#
# Input:  installer/Releases/GHManage-osx-Portable.zip  (written by `vpk pack`)
# Output: installer/Releases/GHManage-osx.dmg
#
# The DMG is built from the *packed* app, not straight from dist/GHManage.app.
# That is deliberate: `vpk pack` is what injects Contents/MacOS/UpdateMac and
# the sq.version manifest, and without those the app cannot self-update. A DMG
# built from the PyInstaller output would install a GHManage that silently
# never updates -- the same class of bug as the IsPortable guard in updater.py,
# and just as invisible. Velopack bundles are self-contained, so an app dragged
# out of this DMG updates exactly like one installed from the .pkg.
#
# By this point `vpk pack` has already signed, notarized and stapled the app
# inside the zip, so the app needs no further treatment here. The DMG itself
# still does: Gatekeeper assesses the disk image the user downloads, and an
# unnotarized DMG warns on open even when the app inside it is perfect.
#
# Environment:
#   GHM_SIGN_CODE=1        Sign the DMG with a Developer ID Application cert
#   GHM_NOTARIZE=1         Notarize and staple the DMG (implies GHM_SIGN_CODE=1)
#   GHM_SIGNING_IDENTITY   Identity string; discovered from the keychain if unset
#   GHM_KEYCHAIN           Optional keychain to search
#
# Notarization credentials are read by scripts/notarize_macos.sh; see that file.
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RELEASES="installer/Releases"
PORTABLE_ZIP="$RELEASES/GHManage-osx-Portable.zip"
FINAL_DMG="$RELEASES/GHManage-osx.dmg"

APP_VERSION=$(python3 -c "from version import __version__; print(__version__)")
VOLUME_NAME="GHManage $APP_VERSION"
MOUNT_POINT="/Volumes/$VOLUME_NAME"

SIGN_CODE="${GHM_SIGN_CODE:-0}"
NOTARIZE="${GHM_NOTARIZE:-0}"
# Notarization is meaningless without a Developer ID signature.
if [ "$NOTARIZE" = "1" ]; then
    SIGN_CODE=1
fi

echo "========================================================================"
echo "Building GHManage $APP_VERSION disk image"
echo "========================================================================"

if [ ! -f "$PORTABLE_ZIP" ]; then
    echo "ERROR: $PORTABLE_ZIP not found."
    echo "       Run './build.sh installer' first -- the DMG is built from the"
    echo "       packed app so it carries Velopack's updater."
    exit 1
fi

# ----------------------------------------------------------------------------
# Stage
# ----------------------------------------------------------------------------
STAGING="build/dmg_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING" "$RELEASES"

echo "Extracting the packed app..."
# ditto, not unzip: it preserves the extended attributes and symlinks that
# carry the code signature. unzip would produce an app that fails codesign
# --verify, and the reason would not be obvious.
ditto -x -k "$PORTABLE_ZIP" "$STAGING"

APP="$STAGING/GHManage.app"
if [ ! -d "$APP" ]; then
    echo "ERROR: no GHManage.app inside $PORTABLE_ZIP. Found:"
    ls -la "$STAGING"
    exit 1
fi

# The whole point of building from the portable zip. If this is ever missing,
# the DMG would ship a permanently frozen GHManage.
if [ ! -f "$APP/Contents/MacOS/UpdateMac" ]; then
    echo "ERROR: $APP has no Contents/MacOS/UpdateMac."
    echo "       Velopack did not process this bundle, so it cannot self-update."
    exit 1
fi

cat > "$STAGING/README.txt" << EOF
GHManage $APP_VERSION
$(printf '=%.0s' $(seq 1 $((9 + ${#APP_VERSION}))))

INSTALL

  Drag GHManage.app onto the Applications folder in this window.

BEFORE FIRST RUN

  GHManage drives the GitHub CLI, so install and sign in to that first:

      brew install gh
      gh auth login

  GHManage finds gh in the usual Homebrew and MacPorts locations even though
  an app launched from Finder does not inherit your Terminal's PATH. If you
  keep gh somewhere unusual, set GHMANAGE_GH_PATH to its full path.

UPDATES

  GHManage updates itself. New versions download in the background and are
  installed the next time you start the app. Help > Check for Updates checks
  on demand. This works wherever you put the app.

REQUIREMENTS

  An Apple Silicon Mac (M1 or later), macOS 11 Big Sur or newer.

ACCESSIBILITY

  GHManage is built for screen reader users: full VoiceOver support and
  complete keyboard navigation.

https://github.com/kellylford/GHManage
EOF

# ----------------------------------------------------------------------------
# Build the image
# ----------------------------------------------------------------------------
# The /Applications symlink is created on the mounted read-write image, not in
# the staging folder: `hdiutil create -srcfolder` follows symlinks, so a
# symlink to /Applications sitting in staging makes it try to copy the whole
# protected /Applications directory, and the build fails.
hdiutil detach "$MOUNT_POINT" 2>/dev/null || true

TEMP_RO="build/GHManage-ro.dmg"
TEMP_RW="build/GHManage-rw.dmg"
rm -f "$TEMP_RO" "$TEMP_RW" "$FINAL_DMG"

echo "Creating disk image from staging..."
hdiutil create -srcfolder "$STAGING" -volname "$VOLUME_NAME" \
    -fs HFS+ -format UDZO -imagekey zlib-level=1 "$TEMP_RO"

echo "Converting to a writable image..."
hdiutil convert "$TEMP_RO" -format UDRW -o "$TEMP_RW"
rm -f "$TEMP_RO"

echo "Mounting..."
hdiutil attach -readwrite -noverify -noautoopen "$TEMP_RW"

if [ ! -d "$MOUNT_POINT" ]; then
    echo "ERROR: image did not mount at $MOUNT_POINT"
    rm -f "$TEMP_RW"
    exit 1
fi

echo "Adding the Applications symlink..."
ln -s /Applications "$MOUNT_POINT/Applications"

sync
hdiutil detach "$MOUNT_POINT" -force

echo "Compressing..."
hdiutil convert "$TEMP_RW" -format UDZO -imagekey zlib-level=9 -o "$FINAL_DMG"
rm -f "$TEMP_RW"
rm -rf "$STAGING"

# ----------------------------------------------------------------------------
# Sign and notarize the image
# ----------------------------------------------------------------------------
if [ "$SIGN_CODE" = "1" ]; then
    IDENTITY="${GHM_SIGNING_IDENTITY:-}"
    if [ -z "$IDENTITY" ]; then
        IDENTITY=$(security find-identity -v -p codesigning ${GHM_KEYCHAIN:+"$GHM_KEYCHAIN"} \
            | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)"/\1/') || true
    fi
    if [ -z "$IDENTITY" ]; then
        echo "ERROR: GHM_SIGN_CODE=1 but no Developer ID Application certificate found."
        exit 1
    fi

    echo "Signing the disk image..."
    codesign --force --timestamp \
        ${GHM_KEYCHAIN:+--keychain "$GHM_KEYCHAIN"} \
        --sign "$IDENTITY" "$FINAL_DMG"
    codesign --verify --verbose "$FINAL_DMG"
fi

if [ "$NOTARIZE" = "1" ]; then
    bash "$ROOT/scripts/notarize_macos.sh" "$FINAL_DMG"
fi

echo ""
echo "========================================================================"
echo "DMG: $FINAL_DMG ($(du -h "$FINAL_DMG" | cut -f1))"
echo "========================================================================"
if [ "$NOTARIZE" = "1" ]; then
    echo "Signed, notarized and stapled -- ready to publish."
elif [ "$SIGN_CODE" = "1" ]; then
    echo "Signed but NOT notarized. Gatekeeper will still warn on download."
else
    echo "UNSIGNED. macOS will refuse to open this after a download."
    echo "Fine for local testing; not for publishing."
fi
