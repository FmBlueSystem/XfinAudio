# Native arm64 Mac packaging adaptation

This recipe is a local integrity-signed development candidate, not a Developer ID
release, notarized installer, DMG, updater or installed-app replacement. Do not use
legacy `build_dmg.sh`, download a universal FFmpeg or change Gatekeeper/security.
The owner must integrate this patch, run complete gates, supply the exact new V11
seal and authorize its final build first. No final app was built for this handoff.

## Inputs and cache

Use Node24+, native Python3.12 and an external clean environment synchronized with
`uv pip sync --require-hashes packaging/macos/requirements-build.txt`. The lock
reuses unchanged official cross-platform Linux hashes plus pinned Darwin Macholib;
a full native resolution and reference-lock sync are retained in handoff evidence.
Do not install the legacy Qt-bearing root project. Electron comes from the npm
lock; compile TypeScript before final assembly. Outputs must be new and outside
source. Shared engines, Electron and Linux bootstrap remain unchanged.

Mac startup delegates canonical complete CLI validation to the shared bootstrap,
then selects `mac_numba_cache.AppDataCacheLocator` before scientific imports. The
locator calls Numba's standard frozen-aware initializer, replacing only its cache
path with validated appdata/cache/numba and the original source subpath. Source
stamp/executable content hash, line disambiguation and frozen-aware selection are
inherited unchanged. Hostile cache/locator variables are overridden; waveform
Joblib cache remains disabled. Symlink/relative/non-directory paths fail closed.

## Recipe

Provide the trusted existing FFmpeg and its recorded SHA256 closure manifest, and
explicit license material for FFmpeg and its dependency packages. Nothing is
resolved from unknown downloads. Native closure is copied, changed to contained
loader-relative install names and ad-hoc signed only in the new staging tree.
Audit every native object: architecture, install ID, rpaths, dependency resolution
and symlink containment. Absolute Homebrew/Cellar/venv references and unresolved
non-system dependencies fail. Parenthesized Electron helpers are read through an
open descriptor to avoid otool-classic archive-member parsing. Helper executables
use their own loader context. Preserve input hashes and the unchanged gate report.

```
MAC_FREEZER_PYTHON packaging/macos/build.py --root EXACT_V11_SOURCE \
  --output NEW_EXTERNAL_BUILD --gate-report OWNER_SEALED_GATES.json \
  --ffmpeg TRUSTED_EXISTING_FFMPEG --ffmpeg-manifest RECORDED_CLOSURE.json \
  --dependency-licenses VERIFIED_LICENSE_DIRECTORY
```

Owner gate reports may come from another host: every named gate, zero-skip
Electron result and identical source seal are required; their original root is
retained in provenance, never rewritten into purported local gate evidence.
Assembly renames the main executable to `XfinAudio Next` and sets the matching
`CFBundleExecutable` before signing, so Electron recognizes packaged mode and
uses the bundled core without a system Python fallback. It puts compiled app in
Contents/Resources/app, frozen core in Contents/Resources/core. Final native
inventories and local ad-hoc integrity signatures are checked. Embedded inventories
are explicitly pre-final-signing snapshots; the sibling
`XfinAudio Next.app.native-manifest.json` records audited post-signing native hashes
and the exact source seal without modifying the signed app. Retain that manifest
with final validation evidence. No credentials.

## Independent runtime verification

`cache_probe.py` is a dependency-only freezer entry. Test cold/warm six tagged
synthetic WAV/FLAC/MP3/AAC-M4A/ALAC-M4A/AIFF files with original analyzers, empty
PATH, hostile cache variables, read-only HOME/bundle and the original bundle
hidden during relocated runs. Verify executable stamp, actual cache loads, no
Qt/network, no fallback dependency and source SHA256/mtime conservation.
This passed for the handoff dependency probe; it does not prove the final app.
Final V11 core must independently repeat its runtime smoke and native preview,
pause/seek/resume/switch. Packaged Electron intentionally ignores development
XFIN_DATA_DIR: QA must first verify its actual userData/session/log/crash paths
under a new canonical profile using the approved native launch flow. Never infer
isolation from that development variable alone or select real legacy data.

## QA-only local DMG

```
MAC_FREEZER_PYTHON packaging/macos/dmg.py --app NEW_EXTERNAL_BUILD/"XfinAudio Next.app" \
  --expected-source-sha256 EXACT_V11_SEAL --output NEW_EXTERNAL_BUILD/"XfinAudio Next QA.dmg"
```

The basename is fixed to `XfinAudio Next QA.dmg`. From a self-derived source root, the
module rejects an existing output/evidence, an output inside that root, a manifest
that is not the exact `post-final-signing` seal, a missing declared notice or
executable, and any staging symlink escaping the staged app except root
`/Applications -> /Applications`; it then runs `hdiutil create`/`verify` and writes
the sibling `.sha256`/`.provenance.json` for the exact bytes. This ad-hoc local QA
image is not Developer ID-signed, notarized or Gatekeeper-approved, claims no UDZO
byte-determinism, and still requires the owner's V11 seal.
