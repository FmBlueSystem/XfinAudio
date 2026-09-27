# Packaging Strategy

XfinAudio is a full open-source GPL-3.0-only project. The primary distribution format is the Python package: end users install it with `pip`, `pipx`, or `uv tool`, and the dependency resolver fetches PySide6 and mutagen from PyPI under their own licenses. Developer/QA execution runs through `uv run xfinaudio`. The PyInstaller spike remains available only for producing an optional local `.app` (unsigned by default) for personal use; signed macOS `.app`/DMG redistribution is out of scope pending legal review.

A PyInstaller packaging spike now exists at `packaging/pyinstaller/xfinaudio.spec`; its optional local bundle includes only a validated, source-built FFmpeg CLI at bundle root for loudness measurement. The source pin, LGPL configuration, and rebuild command are recorded in `docs/third-party-license-inventory.md`; this does not change the pending legal-review posture for binary redistribution. It has a safe smoke script at `scripts/pyinstaller_build_smoke.py`. The non-audio release gate runner at `scripts/release_gate_check.py` lists or executes all automated release-readiness gates that do not require audio files, including open-source publication docs, publication artifact hygiene, and source package hygiene, can write structured JSON evidence with `--report-json PATH`, and clearly leaves audio QA, clean-account validation, signing/notarization, DMG distribution, and legal review as pending manual gates. The GitHub Actions workflow at `.github/workflows/non-audio-release-gates.yml` runs the default non-heavy gate on macOS with Python 3.12, renders Markdown evidence from the JSON report, appends it to the GitHub Step Summary, and uploads both CI evidence files; the temp packaging build is manual-only through the `include_packaging_build` dispatch input. PyInstaller is pinned in the project dev dependency group, and the smoke script can validate a temp-built app launch without touching user app data. The spike validates packaging configuration only; it does not produce a release artifact, installer, signed binary, notarized app, or published distribution.

## Recommended path

| Stage | Decision | Purpose |
|-------|----------|---------|
| Developer/QA run | `uv run xfinaudio` | Fast release-candidate validation from source without installer artifacts. |
| Primary distribution | Python package via `pip`/`pipx`/`uv tool` | End-user install; dependencies resolve from PyPI under their own licenses. |
| Optional local build | PyInstaller app bundle | Unsigned `.app` for personal local use only; not a distributed artifact. |

## Target platforms

| Platform | Status |
|----------|--------|
| macOS | First target because current development and QA are macOS-based. |
| Windows | Future validation target after the macOS packaging path is stable. |
| Linux | Future validation target after the macOS packaging path is stable. |

## Distribution and licensing

- XfinAudio is distributed as a Python package; no signed macOS `.app`/DMG is produced or redistributed.
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

## PyPI publication workflow

Publishing to PyPI is automated via GitHub Actions. To release a new version:

1. Update `version` in `pyproject.toml`.
2. Commit and push the version bump.
3. Create and push a tag:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
4. The `.github/workflows/publish-to-pypi.yml` workflow will run tests, build the package, and publish to PyPI.

### Required repository secret

The workflow expects a PyPI API token stored as `PYPI_API_TOKEN` in:
**Settings → Secrets and variables → Actions → New repository secret**.

Do not commit the token to the repository. `tokenpypi.txt` is already ignored in `.gitignore`.

## Open decisions and risks

- PyInstaller is pinned in project dev dependencies for optional local builds, but reproducible release confidence still needs clean-machine evidence when that path is used.
- Validate Windows and Linux behavior before claiming cross-platform support.
- Manual desktop QA with real Mixed In Key files remains required before release claims.
- Third-party package metadata can be incomplete; legal review remains required before binary redistribution claims, especially for PySide6/Qt and mutagen.
- Serato fixture validation is not proof of live Serato compatibility.
