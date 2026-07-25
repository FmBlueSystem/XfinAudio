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
# The DMG is unsigned and un-notarized. macOS will warn on first launch unless
# the user right-clicks > Open. Signing needs a Developer ID and is out of scope
# for a local build.

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

app_size="$(du -sh "${app_bundle}" | cut -f1)"
dmg_size="$(du -sh "${dmg_path}" | cut -f1)"
echo
echo "app: ${app_bundle} (${app_size})"
echo "dmg: ${dmg_path} (${dmg_size})"
echo
echo "Unsigned build: on first launch macOS will block it."
echo "Right-click the app > Open, or run: xattr -dr com.apple.quarantine <app>"
