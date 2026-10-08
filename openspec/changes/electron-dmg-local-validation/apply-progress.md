# Apply progress

Slice 1 (documentation only) of the first independently testable sub-slice of
installable-Electron work unit 2. No production code or test changed in slice 1; no
`.app` or DMG was built in any slice.

Recorded contract for the applied `packaging/macos/dmg.py`: consume the already-built
`XfinAudio Next.app` and sibling `.native-manifest.json`; validate source digest,
manifest provenance and the fixed `XfinAudio Next QA.dmg` name; stage the app
plus the sole allowed staging-root `/Applications` symlink; run `hdiutil create`/
`verify`; write sibling SHA-256 and QA provenance for the exact produced bytes;
reject existing output, output inside the module-derived source root and escaping
app-bundle symlinks; never modify the sealed app. The downstream presence check
covers the stable `LICENSES/` paths in the spec; upstream Python notices remain
`build.py`'s responsibility. Presence is not legal clearance, and no UDZO
byte-determinism is claimed.

## Behavior slice (applied)

Committed as `3fabf88` (392 added lines: `packaging/macos/dmg.py` 152,
`tests/test_macos_dmg.py` 224, README 16) on top of planning commit `ed855c9`
(209 lines), within the 400-line budget. RED: 15 failures on the missing module,
then a second RED for two safety defects (streaming digest, partial-evidence
cleanup) before GREEN. Final focused `uv run pytest tests/test_macos_dmg.py
tests/test_macos_recipe.py -q`: 28 passed; ruff/format/pyright clean; canonical
`uv run python scripts/release_gate_check.py --run` exit 0 (4205 pytest passed,
94.45% coverage vs 89 floor). Synthetic fake runner only: no real app, DMG or
`hdiutil` call. The real build and clean-account QA stay blocked on the owner's exact
V11 seal and authorization; this QA-only slice is verified but the work unit stays
open until a real artifact exists.
