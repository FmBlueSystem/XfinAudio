# Apply progress

Documentation-only slice for the first independently testable sub-slice of
installable-Electron work unit 2. No production code or test changed; no `.app` or
DMG was built.

Recorded contract for the future `packaging/macos/dmg.py`: consume the already-built
`XfinAudio Next.app` and sibling `.native-manifest.json`; validate source digest,
manifest provenance and the fixed `XfinAudio Next QA.dmg` name; stage the app
plus the sole allowed staging-root `/Applications` symlink; run `hdiutil create`/
`verify`; write sibling SHA-256 and QA provenance for the exact produced bytes;
reject existing output, output inside the module-derived source root and escaping
app-bundle symlinks; never modify the sealed app. The downstream presence check
covers the stable `LICENSES/` paths in the spec; upstream Python notices remain
`build.py`'s responsibility. Presence is not legal clearance, and no UDZO
byte-determinism is claimed.

Deferred: the behavior slice (synthetic-hdiutil RED then GREEN, <400 lines) and any
real build, which stays blocked on the owner's exact V11 seal and authorization per
`packaging/macos/README.md`. Developer ID remains absent; no electron-builder
dependency and no legacy Qt DMG script; `packaging/macos/build.py` is untouched.
