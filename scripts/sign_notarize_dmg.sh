#!/usr/bin/env bash
#
# Sign, notarize, staple, and package the XfinAudio macOS app bundle into a DMG.
#
# This script performs IRREVERSIBLE, externally visible release actions
# (Apple notarization submission). Run it only after every gate in
# docs/macos-signing-notarization-dmg-plan.md is satisfied and recorded,
# including release-specific legal review for GPL-3.0-only binary
# redistribution (PySide6/Qt, mutagen, and other dependencies).
#
# Secrets are read from the environment and the macOS keychain only.
# Never commit certificates, private keys, keychain profiles, Apple IDs,
# or app-specific passwords.
#
# Required environment variables:
#   XFIN_SIGN_IDENTITY    Developer ID Application identity, e.g.
#                         "Developer ID Application: Acme Inc (TEAMID1234)"
#   XFIN_TEAM_ID          Apple Developer Team ID, e.g. "TEAMID1234"
#   XFIN_NOTARY_PROFILE   notarytool keychain profile name created via
#                         `xcrun notarytool store-credentials`
#
# Optional environment variables:
#   XFIN_DIST_DIR         Output directory (default: ./release-dist)
#   XFIN_VERSION          Version label for the DMG name (default: 0.1.0)

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly PROJECT_ROOT
readonly SPEC_PATH="${PROJECT_ROOT}/packaging/pyinstaller/xfinaudio.spec"

DIST_DIR="${XFIN_DIST_DIR:-${PROJECT_ROOT}/release-dist}"
VERSION="${XFIN_VERSION:-0.1.0}"
readonly APP_PATH="${DIST_DIR}/XfinAudio.app"
readonly ZIP_PATH="${DIST_DIR}/XfinAudio-${VERSION}.zip"
readonly DMG_PATH="${DIST_DIR}/XfinAudio-${VERSION}.dmg"

log() { printf '>> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_env() {
  local name="$1"
  [[ -n "${!name:-}" ]] || die "Missing required environment variable: ${name}"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

preflight() {
  require_env XFIN_SIGN_IDENTITY
  require_env XFIN_TEAM_ID
  require_env XFIN_NOTARY_PROFILE
  require_cmd pyinstaller
  require_cmd codesign
  require_cmd xcrun
  require_cmd hdiutil
  require_cmd ditto

  security find-identity -v -p codesigning 2>/dev/null \
    | grep -Fq "${XFIN_SIGN_IDENTITY}" \
    || die "Signing identity not found in keychain: ${XFIN_SIGN_IDENTITY}"
}

build_app() {
  log "Building app bundle with PyInstaller"
  rm -rf "${DIST_DIR}"
  mkdir -p "${DIST_DIR}"
  pyinstaller --noconfirm --clean \
    --distpath "${DIST_DIR}" \
    --workpath "${DIST_DIR}/build" \
    "${SPEC_PATH}"
  [[ -d "${APP_PATH}" ]] || die "Expected app bundle not produced: ${APP_PATH}"
}

sign_app() {
  log "Signing app bundle"
  codesign --force --options runtime --timestamp \
    --sign "${XFIN_SIGN_IDENTITY}" \
    "${APP_PATH}"
  log "Verifying signature"
  codesign --verify --deep --strict --verbose=2 "${APP_PATH}"
  spctl --assess --type execute --verbose "${APP_PATH}"
}

notarize_app() {
  log "Zipping signed app for notarization"
  /usr/bin/ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"
  log "Submitting to Apple notarization (this blocks until Apple responds)"
  xcrun notarytool submit "${ZIP_PATH}" \
    --keychain-profile "${XFIN_NOTARY_PROFILE}" \
    --team-id "${XFIN_TEAM_ID}" \
    --wait
  log "Stapling notarization ticket"
  xcrun stapler staple "${APP_PATH}"
  xcrun stapler validate "${APP_PATH}"
  spctl --assess --type execute --verbose "${APP_PATH}"
}

build_dmg() {
  log "Building DMG"
  rm -f "${DMG_PATH}"
  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "${staging}"' RETURN
  /usr/bin/ditto "${APP_PATH}" "${staging}/XfinAudio.app"
  ln -s /Applications "${staging}/Applications"
  hdiutil create -volname "XfinAudio ${VERSION}" \
    -srcfolder "${staging}" \
    -ov -format UDZO \
    "${DMG_PATH}"
  log "Verifying DMG Gatekeeper assessment"
  spctl --assess --type open --context context:primary-signature \
    --verbose "${DMG_PATH}" || true
  shasum -a 256 "${DMG_PATH}"
}

main() {
  preflight
  build_app
  sign_app
  notarize_app
  build_dmg
  log "Done. Signed, notarized, stapled app and DMG are in: ${DIST_DIR}"
  log "Record all evidence in docs/macos-signing-notarization-dmg-plan.md before any release claim."
}

main "$@"
