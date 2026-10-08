# Packaging Strategy

XfinAudio is a full open-source GPL-3.0-only project. The current release channel is a local macOS QA DMG built by `packaging/macos/build.py` and `packaging/macos/dmg.py` around the Electron shell and the frozen headless core (the legacy Qt `build_dmg.sh`/PyInstaller app path was removed together with Qt). Developer/QA execution runs the Electron app via `npm start` in `desktop-electron/`, and Qt/PySide6 is no longer a dependency of XfinAudio. PyPI is no longer an automatic release channel: its workflow is retained as a manual-only, gated fallback using trusted publishing (OIDC). None of these mechanisms implies completed native macOS validation or legal clearance for third-party binary redistribution.

The Electron packaging recipe lives in `packaging/macos/`: `build.py` assembles `XfinAudio Next.app` from the compiled Electron app plus the frozen headless core (entry `packaging/macos/core_entry.py` → `xfinaudio.headless.__main__`) with a trusted FFmpeg closure and ad-hoc integrity signing; `dmg.py` produces the explicitly QA-only `XfinAudio Next QA.dmg` with sibling `.sha256`/`.provenance.json` evidence. The old PyInstaller spec (`packaging/pyinstaller/xfinaudio.spec`) and its smoke script were removed with Qt (historical: both went away in `4e31a3a`). The non-audio release gate runner at `scripts/release_gate_check.py` lists or executes all automated release-readiness gates that do not require audio files, including open-source publication docs, publication artifact hygiene, and source package hygiene, can write structured JSON evidence with `--report-json PATH`, and clearly leaves audio QA, clean-account validation, signing/notarization, DMG distribution, and legal review as pending manual gates. The GitHub Actions workflow at `.github/workflows/non-audio-release-gates.yml` runs the default non-heavy gate on macOS with Python 3.12, renders `.release-evidence/release-gate-evidence.md` from the JSON report, appends it to the GitHub Step Summary, and uploads both JSON and Markdown evidence files.

## Recommended path

| Stage | Decision | Purpose |
|-------|----------|---------|
| Developer/QA run | `npm start` in `desktop-electron/` | Fast Electron validation from source without installer artifacts. |
| Primary distribution | macOS DMG | Local packaging from a clean, gated commit; native macOS QA and redistribution review remain required. |
| Optional local build | `packaging/macos/build.py` (owner-gated) | Locally assembled `XfinAudio Next.app` for personal local use only; not a distributed artifact. |

## Target platforms

| Platform | Status |
|----------|--------|
| macOS | First target because current development and QA are macOS-based. |
| Windows | Future validation target after the macOS packaging path is stable. |
| Linux | Future validation target after the macOS packaging path is stable. |

## Distribution and licensing

- The current release channel is the macOS DMG; the Python source/package workflow remains available to developers. Signing is optional and does not establish redistribution clearance.
- Locally assembled `XfinAudio Next.app` bundles are ad-hoc signed by default and for personal local use only; optional Developer ID signing/notarization is credential-gated and documented under "Signing and notarization".
- XfinAudio source is GPL-3.0-only; redistribution must comply with GPLv3.
- Third-party dependency/license inventory tooling is documented in `docs/third-party-license-inventory.md`; it records package metadata evidence only.
- GPLv3 compliance and third-party dependency obligations (especially mutagen and FFmpeg; Qt/PySide6 is no longer a dependency of XfinAudio) for package distribution warrant legal review.
- This strategy does not add installer automation, legal clearance, or release publishing automation; signing/notarization stays a manual, credential-gated local step (the Electron QA image is ad-hoc signed only), not a release pipeline.
- No legal clearance is implied by this strategy.

## Signing and notarization

Local builds stay ad-hoc signed and un-notarized by default: `packaging/macos/build.py` signs with the empty identity (`-`) and `dmg.py` produces an explicitly QA-only image; Developer ID signing and notarization remain pending owner decisions.

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
- Third-party dependency/license inventory: `uv run python scripts/third_party_license_inventory.py`; optional JSON evidence can be written outside project-root `build/`/`dist/` with `--format json --output PATH`.
- Manual desktop QA with a real Mixed In Key processed folder.
- Confirmation that no live Serato writes are part of the candidate.
- Confirmation that GPL-3.0-only source license metadata and third-party binary redistribution review notes are current.

## Local QA image integrity enforcement

`packaging/macos/build.py` requires an explicit source root, external output
path, owner gate report, trusted FFmpeg closure manifest and verified dependency
licenses. It refuses outputs inside the source tree, re-checks the source seal
around assembly, and records post-final-signing native hashes in the sibling
`XfinAudio Next.app.native-manifest.json` without modifying the signed app.

`packaging/macos/dmg.py` then refuses an existing output or evidence, an output
inside the self-derived source root, a manifest that is not the exact
`post-final-signing` seal, and any staging symlink escaping the staged app except
the root `/Applications -> /Applications`. It runs `hdiutil create`/`verify` and
writes the sibling `.sha256`/`.provenance.json` for the exact bytes. The image is
explicitly QA-only: ad-hoc signed, not Developer ID-signed, not notarized, not
Gatekeeper-approved, and it claims no UDZO byte-determinism. A source bump, new
commit or bundle edit requires rebuilding; manually editing evidence is not a
supported recovery.
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

- PyInstaller is pinned in project dev dependencies and drives the Linux and macOS freezer lanes, but reproducible release confidence still needs clean-machine evidence before any DMG is handed out.
- Validate Windows and Linux behavior before claiming cross-platform support.
- Manual desktop QA with real Mixed In Key files remains required before release claims.
- Third-party package metadata can be incomplete; legal review remains required before binary redistribution claims, especially for mutagen and FFmpeg (Qt/PySide6 is no longer a dependency of XfinAudio).
- Serato fixture validation is not proof of live Serato compatibility.
