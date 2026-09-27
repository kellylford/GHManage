#!/usr/bin/env bash
#
# setup_macos_secrets.sh — one-time: load the five GitHub Actions secrets that
# the build-macos job in .github/workflows/ghmanage.yml needs to sign and
# notarize the Mac release.
#
# YOU run this, not Claude, so the private key and its password never leave
# this machine. Everything it needs is already here — it discovers all of it:
#
#   Developer ID Application cert  the login keychain
#   Notary key / key id / issuer   ~/.fastweather-keys/asc.json
#
# GitHub never reveals a secret's value once set, which is why this cannot just
# copy the working secrets from Image-Description-Toolkit — that repo uses the
# same five names, set from these same local files.
#
# Usage:
#   scripts/setup_macos_secrets.sh                 # export the cert for you
#   scripts/setup_macos_secrets.sh path/to.p12     # use a .p12 you already have
#
# The keychain export puts up one macOS dialog asking you to allow it. That is
# the only interactive step; the export password is generated here, stored as
# MACOS_CERTIFICATE_PASSWORD, and never needs to be remembered.
#
set -euo pipefail

REPO="kellylford/GHManage"
ASC_JSON="$HOME/.fastweather-keys/asc.json"
IDENTITY="Developer ID Application: Kelly Ford (P887QF74N8)"

die() { echo "❌ $*" >&2; exit 1; }

WORK="$(mktemp -d)"
# macOS ships bash 3.2, which exits 0 when `set -u` trips while an EXIT trap is
# set, so an unset variable would pass for success. The trap fails the script
# unless it reached the end.
cleanup() {
    rm -rf "$WORK"
    [ -n "${VERIFY_KC:-}" ] && security delete-keychain "$VERIFY_KC" 2>/dev/null || true
    [ -n "${finished:-}" ] || exit 1
}
trap cleanup EXIT

# ── Preflight ─────────────────────────────────────────────────────────
command -v gh >/dev/null || die "gh CLI not found."
gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"
[ -f "$ASC_JSON" ] || die "missing $ASC_JSON — the notary key id and issuer id live there."

security find-identity -v -p codesigning | grep -q "$IDENTITY" \
    || die "'$IDENTITY' is not in the login keychain. Download it from developer.apple.com."

KEY_ID="$(python3 -c "import json;print(json.load(open('$ASC_JSON'))['key_id'])")"
ISSUER="$(python3 -c "import json;print(json.load(open('$ASC_JSON'))['issuer_id'])")"
P8="$(python3 -c "import json,os;print(os.path.expanduser(json.load(open('$ASC_JSON'))['p8_path']))")"
[ -f "$P8" ] || die "notary key not found at: $P8"

echo "Signing identity: $IDENTITY"
echo "Notary key:       $P8  (key id $KEY_ID)"
echo ""

# ── The notary key has to actually work, or the release fails at the very ──
# ── last step, after a full build. Check it first; it costs one API call. ──
echo "Checking the notary credentials against Apple…"
xcrun notarytool history --key "$P8" --key-id "$KEY_ID" --issuer "$ISSUER" \
    >/dev/null 2>&1 \
    || die "Apple rejected these notary credentials. The key may be revoked, or
       it may lack the role notarization needs. Create a new App Store Connect
       key (Users and Access → Integrations) and update $ASC_JSON."
echo "  ✅ Apple accepts them."
echo ""

# ── The .p12 ──────────────────────────────────────────────────────────
P12_PW="$(uuidgen)"
P12="${1:-}"

if [ -n "$P12" ]; then
    [ -f "$P12" ] || die ".p12 not found: $P12"
    printf "Enter the password for %s: " "$(basename "$P12")"
    read -rs P12_PW; echo ""
    [ -n "$P12_PW" ] || die "empty password"
else
    P12="$WORK/developer-id.p12"
    echo "Exporting the signing certificate from your keychain."
    echo "macOS will ask you to allow this — click Allow (or Always Allow)."
    echo ""
    # `security export` has no way to select one identity, so this exports every
    # identity in the keychain and narrows it to the Developer ID Application
    # one. That is a requirement, not a nicety: the App Store distribution and
    # development keys have no business in CI, so a narrowing that fails stops
    # here rather than uploading everything.
    security export -k "$HOME/Library/Keychains/login.keychain-db" \
        -t identities -f pkcs12 -P "$P12_PW" -o "$WORK/all.p12" \
        || die "Keychain export failed or was denied."

    command -v openssl >/dev/null || die "openssl is needed to narrow the export to one identity."
    openssl pkcs12 -in "$WORK/all.p12" -passin "pass:$P12_PW" -nodes -legacy \
        -out "$WORK/all.pem" 2>/dev/null \
        || die "Could not read the keychain export with openssl."

    # Keep the certificate and the one private key whose localKeyID matches it.
    # Keeping every key, as this once did, gives OpenSSL several to choose from;
    # it refuses the export, and the old fallback then uploaded all of them.
    python3 - "$WORK/all.pem" "$WORK/one.pem" "$IDENTITY" <<'PY' \
        || die "No '$IDENTITY' certificate with a matching key in the export."
import re, sys
src, dst, want = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(src).read()
# Each bag is its attribute lines followed by one PEM block.
blocks = re.findall(r'(?:^.*?\n)*?-----BEGIN [^-]+-----.*?-----END [^-]+-----\n',
                    text, re.S | re.M)

def key_id(block):
    found = re.search(r'localKeyID:\s*([0-9A-Fa-f ]+)', block)
    return found.group(1).strip() if found else None

cert = next((b for b in blocks if 'CERTIFICATE' in b and want in b), None)
if cert is None or key_id(cert) is None:
    sys.exit(1)
key = next((b for b in blocks if 'PRIVATE KEY' in b and key_id(b) == key_id(cert)), None)
if key is None:
    sys.exit(1)
open(dst, 'w').write(cert + key)
PY

    # -legacy because `security import`, which the runner uses, cannot read the
    # AES/PBKDF2 encryption OpenSSL 3 gives a .p12 by default.
    openssl pkcs12 -export -legacy -in "$WORK/one.pem" -name "$IDENTITY" \
        -passout "pass:$P12_PW" -out "$P12" 2>/dev/null \
        || die "Could not build a .p12 from the Developer ID identity."
    rm -f "$WORK/all.p12" "$WORK/all.pem" "$WORK/one.pem"
    echo "  Narrowed the export to the Developer ID certificate alone."
fi

# ── Verify the .p12 the way the CI runner will import it ──────────────
# `security import` into a throwaway keychain is exactly what the workflow
# does, and unlike OpenSSL it reads Keychain's legacy-encrypted .p12 happily.
VERIFY_KC="$WORK/verify.keychain-db"
security create-keychain -p "$(uuidgen)" "$VERIFY_KC" >/dev/null
security import "$P12" -k "$VERIFY_KC" -P "$P12_PW" -T /usr/bin/codesign >/dev/null 2>&1 \
    || die "The .p12 could not be imported. If you supplied it, check the password."
FOUND="$(security find-identity -v -p codesigning "$VERIFY_KC" 2>/dev/null)"
echo "$FOUND" | grep -q "Developer ID Application" \
    || die "That .p12 holds no Developer ID Application certificate:
$FOUND"
[ "$(echo "$FOUND" | grep -c '^ *[0-9])')" = 1 ] \
    || die "That .p12 holds more than one signing identity; CI needs only Developer ID Application:
$FOUND"
echo ""
echo "Certificates in the .p12:"
printf '%s\n' "$FOUND" | grep -oE '"[^"]+"' | sed 's/^/  /'
echo ""

# ── Upload ────────────────────────────────────────────────────────────
# The braces are load-bearing: macOS ships bash 3.2, which is not multibyte
# aware when parsing a variable name, so `$REPO…` reads the bytes of the
# ellipsis as part of the name, looks up a variable that does not exist, and
# `set -u` kills the script one line before it does any work.
echo "Setting secrets on ${REPO}…"
base64 < "$P12" | gh secret set MACOS_CERTIFICATE_P12   --repo "$REPO"
printf '%s' "$P12_PW" | gh secret set MACOS_CERTIFICATE_PASSWORD --repo "$REPO"
base64 < "$P8"  | gh secret set NOTARY_KEY_P8           --repo "$REPO"
gh secret set NOTARY_KEY_ID    --repo "$REPO" --body "$KEY_ID"
gh secret set NOTARY_ISSUER_ID --repo "$REPO" --body "$ISSUER"
unset P12_PW

echo ""
gh secret list --repo "$REPO"
echo ""

# ── The .pkg ──────────────────────────────────────────────────────────
if ! security find-identity -v | grep -q "Developer ID Installer"; then
    cat <<'EOF'
⚠️  No "Developer ID Installer" certificate on this machine, so
    GHManage-osx-Setup.pkg will be published UNSIGNED and macOS will refuse to
    open it. The DMG and the portable zip are signed and notarized normally.

    Either create that certificate at developer.apple.com (Certificates → +
    → Developer ID Installer), download it, and re-run this script — or drop
    the .pkg row from the download table in docs/release-notes-v0.7.1.md.
EOF
    echo ""
fi

echo "✅ Done. The Mac release is now signed and notarized on the next tag:"
echo "     git tag v0.7.1 && git push origin v0.7.1"
finished=1
