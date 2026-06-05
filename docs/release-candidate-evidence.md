# Release Candidate Evidence — Metadata Fixture Smoke

Date: 2026-06-03
Documentation update: 2026-06-04

## Scope

This evidence records the release-readiness checks that can run without a real Mixed In Key processed audio folder.

It uses metadata-only fixtures and temporary app-owned files. It does not read, create, render, mix, analyze, or mutate audio files. The non-audio release gate runner is `scripts/release_gate_check.py`; it can list or execute automated gates, including open-source publication docs, publication artifact hygiene, and source package hygiene, write structured JSON evidence with `--report-json PATH`, and clearly leaves audio QA, clean-account validation, signing/notarization, DMG distribution, binary redistribution review, and legal review as pending manual gates. Use `scripts/render_release_gate_evidence.py REPORT_JSON` to render that JSON as a Markdown snippet for manual copy/paste into this document; the renderer outputs to stdout by default or an explicit `--output PATH` and does not edit this evidence file automatically. The third-party dependency/license inventory is `scripts/third_party_license_inventory.py`; it renders package metadata evidence only and does not imply legal clearance. XfinAudio source is full open source under GPL-3.0-only; redistribution must comply with GPLv3 and third-party dependency obligations.

CI coverage is now prepared in `.github/workflows/non-audio-release-gates.yml`. The workflow runs the default non-heavy `--run --report-json .release-evidence/release-gate-report.json` gate on pull requests, pushes to `main`, and manual dispatch, then uploads the JSON report and rendered Markdown evidence as the `non-audio-release-gate-evidence` artifact. The optional temp PyInstaller packaging build is available only through the manual `include_packaging_build` dispatch input and defaults to `false`.

## Commands run

```bash
uv run python scripts/smoke_release_readiness.py
uv run pytest -q
uv run pytest -v tests/test_serato_crate.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run pytest -v tests/test_main_window.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run pytest -v tests/test_settings.py tests/test_settings_repository.py tests/test_main_window.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run pytest -v tests/test_scan_service.py tests/test_playlist_workflow.py tests/test_main_window.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run pytest -v tests/test_main_window.py
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run pytest -v tests/test_pyinstaller_packaging.py
uv run python scripts/pyinstaller_build_smoke.py --check-only
uv run python scripts/pyinstaller_build_smoke.py --build-temp
uv run pyinstaller --version
uv run python scripts/pyinstaller_build_smoke.py --check-only
uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch
uv run pytest -v tests/test_pyinstaller_packaging.py
uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch
uv run pytest -v tests/test_pyinstaller_packaging.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run pytest -q tests/test_release_gate_check.py
uv run python scripts/source_package_hygiene_check.py
uv run python scripts/release_gate_check.py --check-only
uv run python scripts/release_gate_check.py --run
uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-release-gate-report.json
uv run python scripts/render_release_gate_evidence.py /tmp/xfinaudio-release-gate-report.json
uv run python scripts/release_gate_check.py --include-packaging-build
uv run python scripts/third_party_license_inventory.py
uv run python scripts/third_party_license_inventory.py --format json --output /tmp/xfinaudio-third-party-inventory.json
# CI workflow prepared: .github/workflows/non-audio-release-gates.yml
```

## Results

```text
PASS temp app database created
PASS track repository saved and listed fixtures
PASS playlist workflow recommendation built
PASS playlist exporters produced JSON/CSV/M3U strings
PASS quality report JSON built
PASS Serato crate dry-run plan built without writing
PASS release readiness smoke completed
........................................................................ [ 62%]
...........................................                              [100%]
115 passed in 0.60s
19 focused Serato crate tests passed in 0.07s
122 full-suite tests passed in 0.46s
All checks passed!
47 files already formatted
9 focused MainWindow UI polish tests passed in 0.29s
127 full-suite tests passed in 0.45s
All checks passed!
47 files already formatted
21 focused settings/MainWindow tests passed in 0.28s
136 full-suite tests passed in 0.46s
All checks passed!
49 files already formatted
27 focused scan/workflow/MainWindow tests passed in 0.31s
144 full-suite tests passed in 0.48s
All checks passed!
49 files already formatted
21 focused MainWindow recommendation review tests passed in 0.30s
149 full-suite tests passed in 0.48s
All checks passed!
49 files already formatted
149 full-suite tests passed in 0.67s
All checks passed!
49 files already formatted
4 focused PyInstaller packaging tests passed in 0.29s
4 focused PyInstaller packaging tests passed in 0.17s after script formatting cleanup
153 full-suite tests passed in 0.66s
All checks passed!
51 files already formatted
PyInstaller check-only printed version 6.14.2 and the committed spec path without creating root build/dist artifacts
PyInstaller temp build completed under /var/folders/.../T/xfinaudio-pyinstaller-ewzz2zpw/ without creating root build/dist artifacts
PyInstaller project dev dependency printed version 6.20.0
PyInstaller check-only printed version 6.20.0 from the project environment
PyInstaller temp build and launch validation completed under /var/folders/.../T/xfinaudio-pyinstaller-ndz4otr4/ with temp DB/settings paths
11 focused PyInstaller packaging tests passed in 0.49s after adding pinned dependency and launch validation
160 full-suite tests passed in 0.68s before final formatting and 160 passed in 0.74s after final formatting
Ruff check passed
Ruff format check reported 51 files already formatted
PyInstaller warning triage RED focused tests failed with 5 missing-helper/output failures, then the expanded observed warning group test failed until the allowlist covered observed optional/platform/dev false positives
PyInstaller temp build and launch validation completed under /var/folders/.../T/xfinaudio-pyinstaller-yxoc01yv/ with warning report /var/folders/.../T/xfinaudio-pyinstaller-yxoc01yv/build/xfinaudio/warn-xfinaudio.txt, 57 expected warnings, 0 unexpected warnings, and temp DB/settings paths
16 focused PyInstaller packaging tests passed in 0.42s after warning triage implementation
165 full-suite tests passed in 0.62s
Ruff check passed after warning triage implementation
Ruff format check reported 51 files already formatted after warning triage implementation
Non-audio release gate runner focused tests passed after RED coverage for dry-run listing, optional packaging command, manual gate reminders, failure propagation, root artifact hygiene, and doc references
Non-audio release gate runner check-only mode listed tests, lint, format, open-source publication docs, publication artifact hygiene, PyInstaller check-only, root artifact hygiene, optional temp packaging, and pending manual gates
Non-audio release gate runner --run completed: 178 tests passed, Ruff check passed, Ruff format check reported 54 files already formatted, PyInstaller check-only passed, and root build/dist artifacts were absent
Non-audio release gate runner --include-packaging-build completed: PyInstaller temp build and package-smoke launch passed under /var/folders/.../T/xfinaudio-pyinstaller-9yn_dd_d, warning triage reported 57 expected warnings and 0 unexpected warnings, and artifacts remained under the temporary directory
Structured JSON evidence is available from `scripts/release_gate_check.py --report-json PATH`; it records schema version 1, mode, project root, automated gate statuses/return codes, pending manual gates, overall status, and limitations. The report supports CI/release evidence but does not prove audio QA, clean account validation, signing/notarization, DMG distribution, or release completion.
GitHub Actions workflow safety tests now cover `.github/workflows/non-audio-release-gates.yml`, including Python 3.11 setup, locked uv sync, JSON report upload, prohibited release-publishing material, and manual-only optional packaging build behavior.
Third-party dependency/license inventory tooling renders direct runtime/dev/build dependency metadata with name, version, license metadata, summary, homepage/project URL, and legal review notes; PySide6/Qt, mutagen, and binary redistribution remain flagged for legal review and no legal clearance is implied.
Manual audio QA remains pending because no real Mixed In Key processed audio folder was provided
```

## Source publication readiness refresh

Latest local source-publication verification after the GPLv3/open-source cleanup:

```text
Expanded non-audio release gate includes tests, lint, format, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only, and root artifact hygiene.
Open-source publication docs gate includes license/docs, public docs, GitHub community templates, repository publication checklist tests, the harmonic mixing guide publication contract, and stale commercial-posture wording regression coverage.
Publication artifact hygiene covers `.DS_Store`, `*.bak`, private root handoff/credential files, and ignored local release evidence.
Source package hygiene builds into a temporary directory outside the project root, inspects the sdist/wheel for private/local files, confirms key public docs are in the sdist, and checks wheel license/readme metadata without creating root `build/` or `dist/` artifacts.
Full local pytest suite: 230 passed.
Ruff check passed.
Ruff format check passed.
No root build/dist artifacts, `.DS_Store`, or `*.bak` files were present.
Manual audio QA remains pending.
Clean macOS account validation remains pending.
Signing, notarization, DMG creation, binary redistribution review, and legal review remain pending.
```

## Verified

- Temporary SQLite app database creation.
- Track repository save/list round-trip.
- Playlist workflow recommendation.
- Explainability/quality path through `PlaylistWorkflowService`.
- JSON/CSV/M3U export generation in memory.
- Quality report JSON generation.
- Serato crate dry-run planning without writing a crate file.
- Fixture-based Serato crate parser and validator for supported `vrsn`/`otrk`/`ptrk` TLV subset.
- Ordered path validation, version mismatch reporting, unknown tag diagnostics, and malformed byte failure reporting.
- Full automated test suite.
- Ruff lint and format compliance.
- MainWindow empty-state guidance labels for selecting a Mixed In Key processed folder, scanning before recommending, and safe export review reminders.
- MainWindow safe export folder selection/display, persistence, and rejection when the export folder equals the selected audio scan folder.
- App-owned JSON settings persistence for `AppSettings.export.safe_export_folder`, including missing file defaults, malformed JSON errors, and future-version rejection.
- Desktop recommendation warning formatting for incomplete metadata, invalid Camelot keys, empty warnings, and unknown review notes while preserving raw explanation warnings.
- Scan progress callbacks report supported-file totals and deterministic current paths while excluding unsupported files.
- Cooperative scan cancellation stops before later files, returns partial records only as canceled display state, and prevents workflow persistence of partial results.
- Desktop scan progress/cancel controls expose progress state, disable cancel after completion, and show canceled status without saving partial records.
- Desktop recommendation review view shows a quality summary with track, transition, average score, and warning counts.
- Desktop transition review table shows order, from/to tracks, component scores, final score, and human-readable warnings while preserving raw explanation data.
- Desktop export guidance tells users to inspect the review table before exporting; no export action or live Serato write flow was added.
- Packaging strategy documentation covers macOS-first RC packaging, future PyInstaller distribution, signing/notarization constraints, app-owned paths, build gates, GPL-3.0-only source posture, PySide6/Qt and mutagen binary redistribution review, and open risks.
- Non-audio release gate runner at `scripts/release_gate_check.py` lists and runs automated gates for pytest, Ruff lint, Ruff format check, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only metadata, root artifact hygiene, and optional temp PyInstaller build + launch/warning triage, with optional structured JSON evidence via `--report-json PATH`.
- PyInstaller packaging spike includes a committed spec, pinned project dev dependency, check-only smoke, temp-only build smoke, temp launch validation, warning triage with zero unexpected observed warnings, and artifact hygiene for root `build/` and `dist/` directories.
- Release notes template documentation covers scope, limitations, verification evidence, safe-use warnings, GPL-3.0-only license posture, upgrade/data notes, and support prompts.
- Third-party dependency/license inventory tooling and documentation cover direct project dependency metadata, Markdown/JSON output, project-root `build/`/`dist/` output refusal, and PySide6/Qt, mutagen, and binary redistribution legal review notes without claiming legal clearance.

## Not verified yet

Manual desktop QA with real audio is still pending because no real Mixed In Key processed folder was provided.

No installer, Developer ID signed binary, notarized artifact, DMG, legal clearance, binary redistribution approval, or published release was produced by the packaging strategy, release notes, dependency/license inventory, or macOS distribution planning update.

The PyInstaller temp build smoke produced an unsigned app-bundle candidate only under a temporary directory. It is not a release artifact and is for optional personal local use only. PyInstaller is pinned in the project dev dependency group, temp launch validation passed locally in package smoke mode with temp DB/settings paths, and local warning triage reported 57 expected warnings with 0 unexpected warnings. XfinAudio is distributed as a Python package (`pip`/`pipx`/`uv tool`); signed macOS `.app`/DMG redistribution is out of scope. GPLv3 compliance and dependency obligations (PySide6/Qt, mutagen) for package distribution still warrant legal review. No legal clearance is implied.

Pending manual checks:

1. Launch desktop app with `uv run xfinaudio`.
2. Select a real Mixed In Key processed audio folder.
3. Scan and verify complete/incomplete metadata counts.
4. Recommend a playlist using at least one built-in strategy.
5. Inspect transition explanations and warnings.
6. Export artifacts to a safe folder outside the audio library.
7. Validate Serato crate only through dry-run or fixture flow; do not use live Serato writes.
8. Import fixture-generated crates into Serato manually in a disposable environment before claiming live compatibility.

## Release risk

The automated metadata fixture smoke supports a technical release-candidate decision, but it is not a substitute for human desktop QA with real Mixed In Key files.
