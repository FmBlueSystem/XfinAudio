# Design

`packaging/macos/dmg.py` is a new downstream module that does not import or change
`packaging/macos/build.py`. It consumes build output only: `<output>/XfinAudio
Next.app` and the sibling `<output>/XfinAudio Next.app.native-manifest.json`
(`source_sha256`, `bundle`, `inventory_stage=post-final-signing`).

CLI: `--app`, `--expected-source-sha256`, `--output`. Flow: read and validate the
manifest; require the fixed image basename `XfinAudio Next QA.dmg` (volume name
`XfinAudio Next QA`) and reject any other name, an existing output, or an output
inside the source tree; build a fresh external staging directory containing the app
copy and the required staging-root `/Applications -> /Applications` symlink; reject
any app-bundle symlink that resolves outside the staged app and any other staging
symlink; run `/usr/bin/hdiutil create` then `hdiutil verify`; on success write the
fixed sibling `XfinAudio Next QA.sha256` and `XfinAudio Next QA.provenance.json`.

Source root: `dmg.py` takes no source-root input. It derives the source root from its
own resolved location (`Path(__file__).resolve().parents[2]`, the repository root
under `packaging/macos/`) and rejects an output that resolves inside that root, so
the output-inside-source check never relies on an undeclared working directory.

Symlink policy: the only staging symlink allowed to resolve outside staging is the
required `/Applications` link at the staging root. Every symlink inside the staged app
must resolve within the staged app, and any other staging symlink is rejected.

Safety: no credentials, signing, notarization, network or dependency install. The
hdiutil runner is injectable so tests use a synthetic runner and never build a real
app or image. Provenance records the app name, source seal, manifest hash, exact
produced image SHA-256 and a `qa_only: true` claim, and states that Gatekeeper,
notarization, signing and redistribution clearance were not evaluated.

Notices: the module re-checks presence of only the stable paths the built bundle
already declares under `Contents/Resources/LICENSES/`: `XfinAudio-NOTICE.md`,
`LICENSE`, `LICENSES.chromium.html`, a nonempty `FFmpeg-dependencies/` directory and
`ffmpeg-input-provenance.json`. It does not enumerate the dynamic Python notice set
(the module has no serialized inventory); `build.py` verifies those upstream, and
none of this adds, replaces or legally clears a notice. No real `.app` or DMG is
produced until the owner supplies the exact V11 seal and authorizes the build per
`packaging/macos/README.md`.
