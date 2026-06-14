# Open-source release readiness backlog

This backlog captures post-MVP work needed to turn XfinAudio release readiness into a safer full open-source GPL-3.0-only desktop project.

## Release candidate blockers

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P0 | Reproducible release smoke | `scripts/smoke_release_readiness.py` passes on a clean checkout and prints the documented checklist. |
| P0 | Automated non-audio release gates | `scripts/release_gate_check.py --run` executes pytest, lint, format, open-source/publication hygiene checks, source package hygiene, PyInstaller check-only, and root artifact hygiene without requiring audio; optional `--report-json PATH` writes CI/release evidence; `.github/workflows/non-audio-release-gates.yml` uploads that JSON in CI; optional `--include-packaging-build` runs temp build + launch/warning triage only under temporary directories and only through explicit manual dispatch in CI. |
| P0 | Manual desktop QA evidence | Completed 2026-06-14: recorded scan, recommendation, and temporary Serato crate export results from `/Volumes/dd/_Lossless/por_decada`. Evidence: `docs/qa-manual-mik-evidence.md`. |
| P0 | No unsafe live writes | Release notes and UI copy clearly state that live Serato writes are not part of the release candidate. |
| P0 | GPLv3 project posture | `LICENSE`, `pyproject.toml`, and docs state the full open-source GPL-3.0-only model without claiming legal clearance. |

## Product polish

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Empty-state guidance | Completed 2026-06-03: desktop `MainWindow` labels explain choosing a Mixed In Key processed folder, scanning before recommending, and reviewing before safe export. Evidence: `docs/ui-empty-states-warning-clarity.md`. |
| P1 | Warning clarity | Completed 2026-06-03: recommendation warning cells use human-readable review text via a pure UI helper while raw domain warnings remain in explanations. Evidence: `docs/ui-empty-states-warning-clarity.md`. |
| P2 | Export naming polish | Completed 2026-06-14: default export filenames include strategy and timestamp while remaining filesystem-safe. Evidence: `src/xfinaudio/exporting/export_naming.py`, `tests/test_export_naming.py`. |

## Serato compatibility

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Fixture-based crate validation | Completed 2026-06-03: deterministic crate fixtures are validated against documented Serato crate expectations; live Serato import remains unverified. |
| P1 | User-approved write flow | Any future crate write requires explicit confirmation, backup, validation, and rollback guidance. |
| P2 | Compatibility matrix | Completed 2026-06-14: supported Serato versions and known limitations are documented. Evidence: `docs/serato-compatibility-matrix.md`, `tests/test_serato_compatibility_matrix.py`. |

## Settings and persistence

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Remember safe export folder | Completed 2026-06-03: the app persists a user-selected safe export folder in app-owned JSON settings and never infers it from the audio scan folder. Caveat: desktop export UI/workflow remains future work. Evidence: `docs/safe-export-folder-settings.md`. |
| P1 | Scan settings review | Completed 2026-06-14: metadata field mappings and scan options are visible before long scans. Evidence: `src/xfinaudio/desktop/screens/library_screen.py`, `docs/help-4-desktop-metadata-walking-skeleton.md`. |
| P2 | Reset settings | Completed 2026-06-14: users can restore defaults from the Settings dialog without deleting the application database. Evidence: `src/xfinaudio/desktop/settings_dialog.py`, `tests/test_settings_dialog.py`. |

## Desktop UX

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Scan progress feedback | Completed 2026-06-03: scans expose supported-file progress updates and a cooperative cancel token; desktop shows progress/cancel state and canceled workflow results do not persist partial records. Caveat: still synchronous, so cancellation is checked between files rather than interrupting an active metadata read. Evidence: `docs/scan-progress-cancel.md`. |
| P1 | Recommendation review view | Completed 2026-06-04: desktop recommendation review shows quality summary counts, transition component scores, and human-readable warnings before export guidance. Evidence: `docs/recommendation-review-view.md`. |
| P2 | Keyboard and accessibility pass | Completed 2026-06-14: main workflow exposes global shortcuts, logical tab order, and accessible names. Evidence: `src/xfinaudio/desktop/main_window.py`, `src/xfinaudio/desktop/screens/*.py`, `tests/test_keyboard_accessibility.py`. |

## QA and fixtures

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Mixed In Key fixture pack | Completed 2026-06-14: a small open fixture library covers complete and incomplete metadata cases. Evidence: `tests/fixtures/mik_processed/`, `tests/fixtures/mixedinkey_tag_variants.json`. |
| P1 | Regression checklist | Completed 2026-06-14: manual QA checklist covers scan, recommend, explainability, export, and dry-run Serato planning. Evidence: `docs/qa-manual-mik-evidence.md`, `scripts/manual_mik_qa_harness.py`. |
| P2 | Performance baseline | Completed 2026-06-14: scan and recommendation timings are recorded for a representative local library size. Evidence: `tests/test_performance_baseline.py`, `scripts/performance_baseline_report.py`. |

## Packaging and distribution

| Priority | Item | Acceptance criteria |
|----------|------|---------------------|
| P1 | Packaging strategy | Completed 2026-06-04: macOS-first RC packaging path, signing/notarization constraints, app-owned paths, build gates, GPL-3.0-only source posture, and distribution risks are documented. Evidence: `docs/packaging-strategy.md`. |
| P1 | Release notes template | Completed 2026-06-04: reusable release notes template includes scope, limitations, verification evidence, safe-use warnings, upgrade/data notes, license posture, and support prompts. Evidence: `docs/release-notes-template.md`. |
| P1 | PyInstaller packaging spike | Completed 2026-06-04: committed spec, check-only smoke, temp-only build smoke, artifact hygiene, and evidence are documented without producing a release artifact. Evidence: `docs/pyinstaller-packaging-spike.md`. |
| P1 | Pinned packaging environment | Completed 2026-06-04: PyInstaller is pinned in project dev dependencies and locked by `uv.lock`; `uv run pyinstaller --version` reported `6.20.0`. Evidence: `docs/pyinstaller-packaging-spike.md`. |
| P1 | Temp app-bundle launch validation | Completed 2026-06-04: `--build-temp --validate-launch` runs the generated app with `XFINAUDIO_PACKAGE_SMOKE=1` and temp DB/settings paths. Evidence: `docs/pyinstaller-packaging-spike.md`. |
| P1 | PyInstaller warning triage | Completed 2026-06-04: temp builds report `warn-xfinaudio.txt`, expected/unexpected counts, and unexpected lines; observed local validation reported 57 expected and 0 unexpected warnings. Evidence: `docs/pyinstaller-packaging-spike.md`. |
| P1 | Non-audio release gate CI | Completed 2026-06-04: GitHub Actions workflow runs default non-heavy release gates on macOS with Python 3.11, locked uv sync, JSON evidence upload, and a manual-only optional packaging build input defaulting to false. Evidence: `.github/workflows/non-audio-release-gates.yml` and `tests/test_non_audio_release_gates_workflow.py`. |
| P1 | Third-party dependency/license inventory | Completed 2026-06-04: stdlib inventory script renders direct runtime/dev/build dependency metadata as Markdown or JSON and refuses project-root `build/`/`dist/` output. Legal review remains pending for binary redistribution, especially for PySide6/Qt and mutagen. Evidence: `docs/third-party-license-inventory.md`. |
| P1 | Python package distribution model | XfinAudio is distributed as a Python package installed via `pip`, `pipx`, or `uv tool`; the dependency resolver fetches PySide6 and mutagen from PyPI under their own licenses. Signed macOS `.app`/DMG redistribution is out of scope and not pursued. Evidence: `README.md`. |
| P1 | PyPI publication | Completed 2026-06-14: published `xfinaudio==1.0.0` to PyPI and added a tag-triggered GitHub Actions workflow for future releases. Evidence: https://pypi.org/project/xfinaudio/1.0.0/, `.github/workflows/publish-to-pypi.yml`. |
| P1 | Distribution license review | Pending: GPLv3 compliance and third-party dependency obligations (especially PySide6/Qt and mutagen) for package distribution still warrant legal review. No legal clearance is implied. |
| P2 | Update path | Completed 2026-06-14: documented update approach preserves the app database and user settings. Evidence: `docs/update-path.md`, `tests/test_update_path.py`. |
