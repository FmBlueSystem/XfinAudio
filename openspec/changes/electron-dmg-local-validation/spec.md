# Requirements

- R1: GIVEN an already-built `XfinAudio Next.app` and its sibling
  `XfinAudio Next.app.native-manifest.json`, WHEN DMG packaging is requested, THEN
  the manifest's `source_sha256` must equal the caller's expected source seal, its
  `bundle` must name the input app, and its `inventory_stage` must be
  `post-final-signing`; any mismatch stops before output creation.
- R2: GIVEN a packaging request, WHEN naming the artifact, THEN the identity is
  fixed: image basename `XfinAudio Next QA.dmg` and volume name `XfinAudio Next QA`,
  distinct from the legacy release identity; any other name is rejected and there is
  no caller-supplied QA name. The artifact is never presented as Gatekeeper-approved,
  notarized, signed or redistribution-cleared.
- R3: GIVEN a valid app, WHEN staging, THEN the app is copied into a fresh staging
  directory containing only the app and the required staging-root symlink
  `/Applications -> /Applications`; an existing output, an output inside the source
  tree, any app-bundle symlink that resolves outside the staged app, and any staging
  symlink other than the exempted `/Applications` link are rejected.
- R4: GIVEN a complete staging directory, WHEN the image is built, THEN one
  `hdiutil create` image is produced and `hdiutil verify` passes; a failed verify
  leaves no accepted artifact.
- R5: GIVEN produced image bytes, WHEN packaging succeeds, THEN the fixed sibling
  files `XfinAudio Next QA.sha256` and `XfinAudio Next QA.provenance.json` record the
  exact produced bytes and the source seal; no byte-reproducibility of the UDZO image
  is claimed.
- R6: GIVEN packaging of a sealed app, THEN the input app and manifest bytes are
  unchanged afterwards.
- R7: GIVEN notices already embedded in the built bundle, WHEN validating, THEN the
  module checks that the declared notice files are present and does not assert
  redistribution clearance; legal clearance stays a separate human/legal decision.

## Source root for the output-inside-source check

`dmg.py` has no source-root CLI input. It derives the source root from its own
resolved location (`Path(__file__).resolve().parents[2]`, the repository root that
contains `packaging/macos/`) and rejects an output that resolves inside that root, so
the check never depends on an undeclared working directory.

## Notices presence scope

The presence check reads only the stable paths the existing build already declares
under `Contents/Resources/LICENSES/`: `XfinAudio-NOTICE.md`, `LICENSE` and
`LICENSES.chromium.html` (asserted by `tests/test_macos_recipe.py`), plus a nonempty
`FFmpeg-dependencies/` directory and `ffmpeg-input-provenance.json` (produced by
`packaging/macos/build.py`). Python notices are verified upstream by `build.py` and
are not re-enumerated downstream, because the module has no serialized inventory of
the dynamic Python notice set. Presence is evidence the build embedded the declared
files, never evidence of legal redistribution clearance.
