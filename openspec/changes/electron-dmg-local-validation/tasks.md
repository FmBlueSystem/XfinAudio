# Tasks

Documentation slice (this change):
1. [x] Inspect the existing builder, native-manifest contract, notices flow and
   packaging README.
2. [x] Record proposal/spec/design/tasks/state and the odd work-unit slice notes.
3. [x] Behavior slice (strict TDD, <400 lines), applied:
   - RED: synthetic hdiutil tests for source-digest/manifest/provenance mismatch, a
     name other than `XfinAudio Next QA.dmg`, existing output, output inside the
     derived source root, app-bundle symlink escape, the exempted `/Applications`
     link, an extra staging symlink, sealed-app immutability and presence of the
     declared notice paths.
   - GREEN: add `packaging/macos/dmg.py` — validate, require the fixed QA identity,
     stage the app plus required `/Applications` symlink, `hdiutil create`/`verify`,
     write the fixed sibling SHA-256 and QA provenance.
   - REFACTOR/VERIFY: focused tests plus ruff/pyright; no real `.app` or DMG build.
   Evidence: planning `ed855c9` (209 lines), behavior `3fabf88` (392 added lines:
   `packaging/macos/dmg.py` 152, `tests/test_macos_dmg.py` 224, README 16).
   RED: 15 focused tests failed with `FileNotFoundError` for the missing module; a
   second RED covered two safety defects (streaming digest, partial-evidence cleanup).
   GREEN: focused `uv run pytest tests/test_macos_dmg.py tests/test_macos_recipe.py -q`
   28 passed; ruff/format/pyright clean; canonical
   `uv run python scripts/release_gate_check.py --run` exit 0 (4205 pytest passed,
   94.45% coverage; floor 89). QA-only slice verified against a synthetic runner; the
   broader work unit 2 stays `[ ]` until a real artifact exists.

Deferred until owner authorization:
4. [ ] Build a real `.app` and QA DMG only after the exact V11 seal and
   `packaging/macos/README.md` authorization exist.
5. [ ] Developer ID signing/notarization (unit 3, externally blocked).
