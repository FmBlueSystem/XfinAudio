#!/bin/bash
# Build XfinAudio.app with PyInstaller and package it as a distributable DMG.
#
# Builds outside the project root on purpose: the release gate requires
# project-root build/ and dist/ to be absent.
#
# Usage:
#   scripts/build_dmg.sh                  # build app + dmg into ./out (gitignored)
#   scripts/build_dmg.sh /path/to/output  # build into a specific directory
#   SKIP_APP_BUILD=1 scripts/build_dmg.sh # reuse an existing .app, only repackage
#
# Signing and notarization are optional and credential-gated. Every build
# reports one of three outcomes at the end:
#   unsigned (default): no Developer ID identity is available; macOS warns on
#     first launch unless the user right-clicks > Open.
#   signed: XFINAUDIO_SIGN_IDENTITY names a "Developer ID Application"
#     identity (or the keychain holds exactly one); the build fails if code
#     verification or the Gatekeeper assessment fails.
#   signed + notarized: XFINAUDIO_NOTARY_PROFILE names a keychain profile
#     stored with `xcrun notarytool store-credentials`; the DMG is submitted
#     to Apple's notary service, then stapled and validated. Submission
#     failures fail the build.

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-${project_root}/out}"
app_name="XfinAudio"
app_bundle="${output_dir}/dist/${app_name}.app"
volume_name="${app_name}"

version="$(
  sed -n 's/^version = "\(.*\)"/\1/p' "${project_root}/pyproject.toml" | head -1
)"
version="${version:-0.0.0}"
dmg_path="${output_dir}/${app_name}-${version}.dmg"

mkdir -p "${output_dir}"

# ---------------------------------------------------------------------------
# Resolve the code-signing identity up front. This is cheap and lets a
# misconfiguration (notarization requested without any signing identity) fail
# in seconds instead of after the multi-minute app build and DMG packaging.
# ---------------------------------------------------------------------------
sign_identity="${XFINAUDIO_SIGN_IDENTITY:-}"
if [[ -z "${sign_identity}" ]]; then
  # Auto-detect only when exactly one valid Developer ID Application identity
  # exists, so an ambiguous keychain never picks a certificate silently.
  # (while-read instead of mapfile: macOS ships bash 3.2, which lacks mapfile.)
  developer_id_entities=()
  while IFS= read -r identity_hash; do
    developer_id_entities+=("${identity_hash}")
  done < <(
    security find-identity -v -p codesigning 2>/dev/null \
      | awk '$0 ~ /Developer ID Application/ {print $2}'
  )
  if (( ${#developer_id_entities[@]} == 1 )); then
    sign_identity="${developer_id_entities[0]}"
  fi
fi

if [[ -n "${XFINAUDIO_NOTARY_PROFILE:-}" && -z "${sign_identity}" ]]; then
  echo "error: XFINAUDIO_NOTARY_PROFILE is set but no Developer ID Application signing identity is available; notarization requires a signed build" >&2
  exit 1
fi

if [[ "${SKIP_APP_BUILD:-0}" != "1" ]]; then
  echo "==> Building ${app_name}.app (this takes a few minutes)"
  cd "${project_root}"
  uv run pyinstaller packaging/pyinstaller/xfinaudio.spec \
    --distpath "${output_dir}/dist" \
    --workpath "${output_dir}/build" \
    --noconfirm
fi

if [[ ! -d "${app_bundle}" ]]; then
  echo "error: ${app_bundle} not found" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Optional code signing. Without a Developer ID Application identity the build
# stays unsigned and the rest of the pipeline is unchanged.
# ---------------------------------------------------------------------------
app_signed=0
if [[ -n "${sign_identity}" ]]; then
  echo "==> Signing ${app_bundle} (identity: ${sign_identity})"
  codesign --force --options runtime --timestamp --sign "${sign_identity}" "${app_bundle}"
  codesign --verify --strict "${app_bundle}"
  spctl -a -t exec -vv "${app_bundle}"
  app_signed=1
else
  echo "hint: unsigned build; set XFINAUDIO_SIGN_IDENTITY (Developer ID Application identity) to enable code signing."
fi

echo "==> Verifying the bundle launches"
# package_smoke_enabled() makes main() return before creating a window, so this
# exercises real startup (imports, Qt init, asset resolution) without a UI.
if ! XFINAUDIO_PACKAGE_SMOKE=1 "${app_bundle}/Contents/MacOS/${app_name}" >/dev/null 2>&1; then
  echo "error: the built app failed its startup smoke check" >&2
  exit 1
fi

echo "==> Staging DMG contents"
staging="$(mktemp -d)"
trap 'rm -rf "${staging}"' EXIT
cp -R "${app_bundle}" "${staging}/"
# Drag-to-install target.
ln -s /Applications "${staging}/Applications"

echo "==> Creating ${dmg_path}"
rm -f "${dmg_path}"
hdiutil create \
  -volname "${volume_name}" \
  -srcfolder "${staging}" \
  -ov \
  -format UDZO \
  "${dmg_path}" >/dev/null

echo "==> Verifying the image"
hdiutil verify "${dmg_path}" >/dev/null

# ---------------------------------------------------------------------------
# Optional notarization. Requires a signed build (fail-closed check above, at
# the top of the script); without a notary profile the DMG is left as produced
# above.
# ---------------------------------------------------------------------------
dmg_notarized=0
if [[ -n "${XFINAUDIO_NOTARY_PROFILE:-}" ]]; then
  echo "==> Notarizing ${dmg_path} (keychain profile: ${XFINAUDIO_NOTARY_PROFILE})"
  xcrun notarytool submit --wait --keychain-profile "${XFINAUDIO_NOTARY_PROFILE}" "${dmg_path}"
  echo "==> Stapling the notarization ticket"
  xcrun stapler staple "${dmg_path}"
  xcrun stapler validate "${dmg_path}"
  dmg_notarized=1
elif [[ "${app_signed}" == "1" ]]; then
  echo "hint: signed but not notarized; set XFINAUDIO_NOTARY_PROFILE (store it first with 'xcrun notarytool store-credentials') to enable notarization."
fi

app_size="$(du -sh "${app_bundle}" | cut -f1)"
dmg_size="$(du -sh "${dmg_path}" | cut -f1)"
echo
echo "app: ${app_bundle} (${app_size})"
echo "dmg: ${dmg_path} (${dmg_size})"
echo
if [[ "${dmg_notarized}" == "1" ]]; then
  echo "Signed and notarized build: Gatekeeper accepts it on first launch."
elif [[ "${app_signed}" == "1" ]]; then
  echo "Signed build (not notarized): Gatekeeper verifies it online on first launch."
  echo "Notarize with XFINAUDIO_NOTARY_PROFILE to remove that dependency."
else
  echo "Unsigned build: on first launch macOS will block it."
  echo "Right-click the app > Open, or run: xattr -dr com.apple.quarantine <app>"
fi
