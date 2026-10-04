# Tasks

Documentation slice (this change):
1. [x] Inspect the existing builder, native-manifest contract, notices flow and
   packaging README.
2. [x] Record proposal/spec/design/tasks/state and the odd work-unit slice notes.
3. [ ] Behavior slice (strict TDD, <400 lines), not yet applied:
   - RED: synthetic hdiutil tests for source-digest/manifest/provenance mismatch, a
     name other than `XfinAudio Next QA.dmg`, existing output, output inside the
     derived source root, app-bundle symlink escape, the exempted `/Applications`
     link, an extra staging symlink, sealed-app immutability and presence of the
     declared notice paths.
   - GREEN: add `packaging/macos/dmg.py` — validate, require the fixed QA identity,
     stage the app plus required `/Applications` symlink, `hdiutil create`/`verify`,
     write the fixed sibling SHA-256 and QA provenance.
   - REFACTOR/VERIFY: focused tests plus ruff/pyright; no real `.app` or DMG build.

Deferred until owner authorization:
4. [ ] Build a real `.app` and QA DMG only after the exact V11 seal and
   `packaging/macos/README.md` authorization exist.
5. [ ] Developer ID signing/notarization (unit 3, externally blocked).
