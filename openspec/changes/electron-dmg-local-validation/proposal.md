# Downstream macOS DMG packaging for the QA Electron app

Deliver the first independently testable sub-slice of work unit 2: a separate,
credential-free `packaging/macos/dmg.py` that turns an already-built QA app into a
local QA image. The module consumes `XfinAudio Next.app` plus its sibling
`XfinAudio Next.app.native-manifest.json`, validates the source digest, manifest
provenance and the fixed QA-only identity (`XfinAudio Next QA.dmg`, volume `XfinAudio
Next QA`), stages the app with the required `/Applications` symlink, runs
`hdiutil create`/`hdiutil verify`, and writes the fixed sibling SHA-256 and QA
provenance record for the exact produced bytes. It refuses an existing output, an
output inside the source root derived from the module location, app-bundle symlink
escapes and any other staging symlink, and never modifies the sealed app. This is not
a full installer and never claims Gatekeeper approval, notarization, signing or
redistribution clearance.

Out of scope: no real `.app` or DMG build until the owner supplies the exact V11
seal and explicitly authorizes it per `packaging/macos/README.md`; no Developer ID,
notarization or signing (unit 3 stays externally blocked); no `electron-builder`
dependency; no legacy Qt DMG script reuse; `packaging/macos/build.py` is untouched;
no hdiutil UDZO byte-determinism claim.

Risks: silently accepting a stale or wrong-tree app, a symlink escaping staging,
mutation of a sealed bundle, or implying legal/Gatekeeper clearance from notice
presence alone; Python notices stay verified upstream in `build.py` rather than
re-enumerated downstream. Rollback: discard the external output directory; source,
sealed app and app data stay intact.

Success criteria: `dmg.py` rejects every invalid input before output creation; a
synthetic-hdiutil test proves each rejection and the produced-bytes checksum path;
no real artifact is required to verify behavior.

Review chain: (1) this documentation slice (<350 lines); (2) the behavior slice
(`dmg.py` + tests, strict TDD, <400 lines). The full installer remains deferred
until owner authorization.
