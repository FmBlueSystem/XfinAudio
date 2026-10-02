# Packaging Strategy

XfinAudio is a full open-source GPL-3.0-only project. The current release channel is the macOS DMG, built locally with `scripts/build_dmg.sh`. Developer/QA execution remains `uv run xfinaudio`. PyPI is no longer an automatic release channel: its workflow is retained as a manual-only, gated fallback using trusted publishing (OIDC). None of these mechanisms implies completed native macOS validation or legal clearance for third-party binary redistribution.

A PyInstaller packaging spike now exists at `packaging/pyinstaller/xfinaudio.spec`; its optional local bundle includes only a validated, source-built FFmpeg CLI at bundle root for loudness measurement. The source pin, LGPL configuration, and rebuild command are recorded in `docs/third-party-license-inventory.md`; this does not change the pending legal-review posture for binary redistribution. It has a safe smoke script at `scripts/pyinstaller_build_smoke.py`. The non-audio release gate runner at `scripts/release_gate_check.py` lists or executes all automated release-readiness gates that do not require audio files, including open-source publication docs, publication artifact hygiene, and source package hygiene, can write structured JSON evidence with `--report-json PATH`, and clearly leaves audio QA, clean-account validation, signing/notarization, DMG distribution, and legal review as pending manual gates. The GitHub Actions workflow at `.github/workflows/non-audio-release-gates.yml` runs the default non-heavy gate on macOS with Python 3.12, renders Markdown evidence from the JSON report, appends it to the GitHub Step Summary, and uploads both CI evidence files; the temp packaging build is manual-only through the `include_packaging_build` dispatch input. PyInstaller is pinned in the project dev dependency group, and the smoke script can validate a temp-built app launch without touching user app data. The spike validates packaging configuration only; it does not produce a release artifact, installer, signed binary, notarized app, or published distribution.

## Recommended path

| Stage | Decision | Purpose |
|-------|----------|---------|
| Developer/QA run | `uv run xfinaudio` | Fast release-candidate validation from source without installer artifacts. |
| Primary distribution | macOS DMG | Local packaging from a clean, gated commit; native macOS QA and redistribution review remain required. |
| Optional local build | PyInstaller app bundle | Unsigned `.app` for personal local use only; not a distributed artifact. |

## Target platforms

| Platform | Status |
|----------|--------|
| macOS | First target because current development and QA are macOS-based. |
| Windows | Future validation target after the macOS packaging path is stable. |
| Linux | Future validation target after the macOS packaging path is stable. |

## Distribution and licensing

- The current release channel is the macOS DMG; the Python source/package workflow remains available to developers. Signing is optional and does not establish redistribution clearance.
- PyInstaller-built `.app` bundles are unsigned by default and for personal local use only; optional Developer ID signing/notarization is credential-gated and documented under "Signing and notarization".
- XfinAudio source is GPL-3.0-only; redistribution must comply with GPLv3.
- Third-party dependency/license inventory tooling is documented in `docs/third-party-license-inventory.md`; it records package metadata evidence only.
- GPLv3 compliance and third-party dependency obligations (especially PySide6/Qt and mutagen) for package distribution warrant legal review.
- This strategy does not add installer automation, legal clearance, or release publishing automation; signing/notarization in `scripts/build_dmg.sh` stays a manual, credential-gated local step, not a release pipeline.
- No legal clearance is implied by this strategy.

## Signing and notarization

Local builds stay unsigned and un-notarized by default: `scripts/build_dmg.sh` only signs when credentials are available, so a machine without a Developer ID identity produces exactly the unsigned DMG it always has, with a hint on how to enable signing.

| Environment variable | Effect when set |
|----------------------|-----------------|
| `XFINAUDIO_SIGN_IDENTITY` | Sign the `.app` with this identity (hardened runtime, trusted timestamp), then enforce `codesign --verify --strict` and a Gatekeeper assessment (`spctl -a -t exec -vv`); a verification failure fails the build. When unset, the script signs only if the keychain holds exactly one valid "Developer ID Application" identity, and never guesses between several. |
| `XFINAUDIO_NOTARY_PROFILE` | After the DMG is created and verified, submit it to Apple's notary service with `xcrun notarytool submit --wait --keychain-profile`, then staple and validate the ticket with `xcrun stapler`. A submission failure fails the build. Requires the app to have been signed. |

Prerequisites:

- A "Developer ID Application" certificate in the keychain for signing.
- A notarytool keychain profile stored once with `xcrun notarytool store-credentials PROFILE ...`, backed by an App Store Connect API key or an app-specific password, for notarization.

The final build summary names the outcome: unsigned (with the right-click > Open workaround), signed, or signed and notarized. Enabling signing or notarization does not change the redistribution posture: binary redistribution still requires the legal review noted under "Distribution and licensing".

## App-owned paths

| Data | Path |
|------|------|
| SQLite database | `~/.xfinaudio/xfinaudio.sqlite3` |
| Settings JSON | `~/.xfinaudio/settings.json` |

Release packaging must preserve these app-owned paths and must not infer write destinations from the scanned audio library. Packaging smoke validation may override them only through `XFINAUDIO_DB_PATH` and `XFINAUDIO_SETTINGS_PATH`, with `XFINAUDIO_PACKAGE_SMOKE=1` to exit before the desktop event loop.

## Release build gates

A release candidate is not ready until all gates are recorded in evidence:

- Non-audio gate checklist: `uv run python scripts/release_gate_check.py --check-only`.
- Automated non-audio gates: `uv run python scripts/release_gate_check.py --run`.
- Structured JSON evidence when needed: `uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-release-gate-report.json`.
- CI non-audio evidence: `.github/workflows/non-audio-release-gates.yml` runs `uv sync --locked`, `uv run python scripts/release_gate_check.py --run --report-json .release-evidence/release-gate-report.json`, renders `.release-evidence/release-gate-evidence.md`, appends it to the GitHub Step Summary, and uploads both JSON and Markdown evidence files.
- Full test suite: `uv run pytest -q`.
- Lint: `uv run ruff check .`.
- Format check: `uv run ruff format --check .`.
- Open-source publication docs: `uv run pytest -q tests/test_open_source_license_docs.py tests/test_public_open_source_docs.py tests/test_github_community_templates.py tests/test_repository_publication_checklist.py tests/test_harmonic_mixing_doc.py`.
- Publication artifact hygiene: `uv run pytest -q tests/test_publication_artifact_hygiene.py`.
- Source package hygiene: `uv run python scripts/source_package_hygiene_check.py`.
- Release smoke script: `uv run python scripts/smoke_release_readiness.py`.
- PyInstaller packaging check-only smoke: `uv run python scripts/pyinstaller_build_smoke.py --check-only`.
- Third-party dependency/license inventory: `uv run python scripts/third_party_license_inventory.py`; optional JSON evidence can be written outside project-root `build/`/`dist/` with `--format json --output PATH`.
- PyInstaller temp build and launch smoke when feasible: `uv run python scripts/release_gate_check.py --include-packaging-build`, which delegates to `uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch` with temp DB/settings paths only.
- Manual desktop QA with a real Mixed In Key processed folder.
- Confirmation that no live Serato writes are part of the candidate.
- Confirmation that GPL-3.0-only source license metadata and third-party binary redistribution review notes are current.

## Local DMG integrity enforcement

`bash scripts/build_dmg.sh` requires a clean Git checkout (including staged and
non-ignored untracked changes) and runs the complete non-audio release gate
before building or reusing an app. Source SHA is checked again after the gate,
app build, staging, and image verification; gate failure or changed source stops
the process. Output defaults to ignored `out/`; project-root `build/`, `dist/`,
and the repository root itself are refused as output destinations.

After successful build, optional signing, and startup smoke, the script writes
`out/dist/XfinAudio.app.provenance.json`. It binds the source SHA, project TOML
version, gate command, and SHA-256 bundle-tree digest (contents, names, file types,
permissions, and internal symlink targets). The app's Info.plist version must
match the project. External/broken symlinks and special files are refused.
The staged copy is checked against this evidence before DMG creation.

`SKIP_APP_BUILD=1 bash scripts/build_dmg.sh` still runs the gate and requires the
same clean SHA, version, and unchanged bundle evidence before signing or running
the app. Old bundles without evidence must be rebuilt. Moving a matching bundle
and its sidecar together is supported. A version bump, new commit, or bundle edit
requires rebuilding; manually editing evidence is not a supported recovery.

This is local process/integrity evidence, not a signed publisher attestation or
a hermetic/reproducible-build guarantee. A local actor able to rewrite the bundle
and evidence can forge both. Installed dependencies, toolchains, and the ignored
source-built FFmpeg input are not independently attested. The pinned FFmpeg
source checksum and existing validation remain separate controls.

Optional Developer ID signing and notarization are accepted intentional choices,
not defects corrected by this enforcement. Synthetic Linux shell tests verify
ordering and failure handling; they do not replace a real macOS app/DMG build,
Gatekeeper validation, notarization, clean-account QA, or legal review.

## PyPI publication workflow

`.github/workflows/publish-to-pypi.yml` has only `workflow_dispatch`; pushing a
tag does not publish anything. If the maintainer explicitly chooses the fallback,
the selected tag must match `[project].version` and the workflow reruns all
non-audio release gates before building and publishing.

Authentication uses PyPI trusted publishing (OIDC), the workflow's `id-token:
write` permission, and its named `pypi` environment. The matching trusted publisher
must already be configured on PyPI; a stored `PYPI_API_TOKEN` is not required.
Do not add or store credentials as part of ordinary builds. This documentation
does not authorize publishing, account configuration, or permission changes.

## Open decisions and risks

- PyInstaller is pinned in project dev dependencies for optional local builds, but reproducible release confidence still needs clean-machine evidence when that path is used.
- Validate Windows and Linux behavior before claiming cross-platform support.
- Manual desktop QA with real Mixed In Key files remains required before release claims.
- Third-party package metadata can be incomplete; legal review remains required before binary redistribution claims, especially for PySide6/Qt and mutagen.
- Serato fixture validation is not proof of live Serato compatibility.
