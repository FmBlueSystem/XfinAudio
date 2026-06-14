# Release readiness smoke runbook

Use this runbook to verify that XfinAudio is ready for a post-MVP release candidate without adding product behavior or touching live Serato libraries.

## Quick path

Run the automated non-audio release gate runner from the project root:

```bash
uv sync
uv run python scripts/release_gate_check.py --check-only
uv run python scripts/release_gate_check.py --run
uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-release-gate-report.json
uv run python scripts/render_release_gate_evidence.py /tmp/xfinaudio-release-gate-report.json
```

Copy the rendered Markdown snippet manually into `docs/release-candidate-evidence.md` when release evidence needs to be recorded. The renderer writes to stdout by default, or to an explicit `--output PATH`; it never edits the evidence document automatically.

CI runs the same default non-audio gate through `.github/workflows/non-audio-release-gates.yml` on pull requests, pushes to `main`, and manual dispatch. It uses a macOS runner for packaging relevance, Python 3.11, `uv sync --locked`, writes `.release-evidence/release-gate-report.json`, renders `.release-evidence/release-gate-evidence.md` from that JSON, appends the Markdown to the GitHub Step Summary, and uploads both files as workflow artifact evidence for manual review/copy-paste.

If local packaging validation is feasible, run the optional temp-only PyInstaller build and launch gate:

```bash
uv run python scripts/release_gate_check.py --include-packaging-build
```

The CI workflow exposes that heavy temp packaging build only as the manual `include_packaging_build` dispatch input, with a default of `false`. Pull request and push runs stay on the non-heavy `--run --report-json` gate.

The runner covers every automated gate that does not require audio files. It runs or documents tests, lint, format, release readiness smoke, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only metadata, root artifact hygiene, and optional PyInstaller temp build + launch/warning triage without creating project-root `build/` or `dist/` artifacts.

XfinAudio source is full open source under GPL-3.0-only and is distributed as a Python package. The project is personal, non-commercial, and community-gifted. Source/wheel redistribution must comply with GPLv3 and third-party dependency obligations; this model is believed to present low legal risk but does not constitute legal clearance. Signed macOS `.app`/DMG redistribution is out of scope and remains pending legal review.

Use `--report-json PATH` to persist structured CI/release evidence for check-only listing, `--run`, or `--include-packaging-build`. The report parent directories may be created, but the runner refuses to create project-root `build/` or `dist/` as report directories. Prefer a temporary path or a project-ignored local path for evidence that should not be committed.

Use `scripts/render_release_gate_evidence.py REPORT_JSON [--output PATH]` to convert that JSON into a copy/paste Markdown snippet. The output still documents only non-audio gates and explicitly does not prove manual audio QA or release completion.

Individual automated gate commands used by the runner are:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/smoke_release_readiness.py
uv run pytest -q tests/test_open_source_license_docs.py tests/test_public_open_source_docs.py tests/test_github_community_templates.py tests/test_repository_publication_checklist.py tests/test_harmonic_mixing_doc.py
uv run pytest -q tests/test_publication_artifact_hygiene.py
uv run python scripts/source_package_hygiene_check.py
uv run python scripts/pyinstaller_build_smoke.py --check-only
```

Additional non-audio smoke command for deterministic in-memory workflow coverage:

```bash
uv run python scripts/smoke_release_readiness.py
```

Manual desktop launch command for interactive QA; this is not part of the automated non-audio release gate runner:

```bash
uv run xfinaudio
```

Expected smoke script checklist:

```text
PASS temp app database created
PASS track repository saved and listed fixtures
PASS playlist workflow recommendation built
PASS playlist exporters produced JSON/CSV/M3U strings
PASS quality report JSON built
PASS DJ readiness: Ready — 0 blocker(s), 0 review item(s); max BPM jump 0.80%
PASS Serato crate dry-run plan built without writing
PASS release readiness smoke completed
```

## Automated gate runner coverage

| Gate | What it verifies |
|------|------------------|
| `scripts/release_gate_check.py --check-only` | Lists automated and manual gates without running subprocess checks. |
| `scripts/release_gate_check.py --run` | Runs pytest, Ruff lint, Ruff format check, release readiness smoke, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only, and root artifact hygiene. |
| `scripts/release_gate_check.py --include-packaging-build` | Runs the non-audio gates plus temp-only PyInstaller build, package-smoke launch, and warning triage. |
| `scripts/release_gate_check.py --run --report-json PATH` | Writes JSON evidence with schema version, mode, project root, automated gate status/return codes, pending manual gates, overall status, and limitations. |
| `scripts/render_release_gate_evidence.py REPORT_JSON` | Renders the JSON evidence as Markdown for manual copy/paste into `docs/release-candidate-evidence.md`; stdout is the default and `--output PATH` is explicit. |
| `.github/workflows/non-audio-release-gates.yml` | Runs the default non-audio gate in CI, renders `.release-evidence/release-gate-evidence.md` from `.release-evidence/release-gate-report.json`, appends the Markdown to the GitHub Step Summary, and uploads both files as artifact evidence. |
| Source package hygiene | Builds `uv build --out-dir` under a temporary directory, inspects the sdist/wheel for private/local files, confirms key public docs are in the sdist, and checks package metadata. |
| Root artifact hygiene | Confirms project-root `build/` and `dist/` are absent. |

The JSON report can support CI/release evidence, including failed runs because it is written before the runner returns a non-zero gate result. It still cannot prove real Mixed In Key audio QA, which remains a manual pending gate. Signed macOS `.app`/DMG redistribution is out of scope for this distribution model.

## Automated smoke coverage

| Area | What the smoke verifies |
|------|--------------------------|
| App database | Creates a temporary SQLite application DB only. |
| Library repository | Saves and lists deterministic complete `TrackRecord` fixtures. |
| Recommendation workflow | Runs `PlaylistWorkflowService.recommend(...)` against persisted records. |
| Playlist export | Builds JSON, CSV, and M3U export strings in memory. |
| Quality report | Builds deterministic quality report JSON. |
| DJ readiness | Builds a DJ readiness report from recommendation and quality data. |
| Serato crate export | Builds a dry-run crate export plan and confirms no crate file is written. |

The automated smoke script does not create, read, render, mix, mutate, or analyze audio files.

## Out of scope / prohibited for RC

- No C++ work.
- No DSP, audio rendering, mixing, time-stretching, pitch-shifting, or waveform analysis.
- No key detection, BPM detection, beat tracking, downbeat tracking, or cue/phrase detection.
- No Serato database V2 mutation.
- No automatic writes to live Serato libraries.

## Manual desktop QA

1. Launch the app:
   ```bash
   uv run xfinaudio
   ```
2. Choose a folder that contains audio already processed by Mixed In Key.
3. Scan the folder.
4. Verify complete and incomplete metadata counts match the visible library expectations.
5. Recommend a playlist with at least one built-in strategy.
6. Verify explainability output includes scores and warnings that make sense for the selected tracks.
7. Export playlist artifacts to a safe folder outside audio library folders.
8. Do not use live Serato writes. Use only dry-run or fixture-based Serato verification for release readiness.

## Known limitations

- This is release readiness verification, not an installer or packaging workflow.
- GPL-3.0-only source licensing and wheel distribution do not clear PySide6/Qt, mutagen, or third-party dependency obligations for binary/app bundle distribution.
- The automated smoke uses deterministic metadata fixtures, not real audio files.
- The non-audio gate runner cannot prove real Mixed In Key audio QA.
- Signed macOS `.app`/DMG redistribution is out of scope for this distribution model.
- Desktop QA still requires a human-owned Mixed In Key processed sample folder.
- Live Serato database/library writes remain out of scope.

## Release candidate checklist

- [ ] Non-audio gate runner listed with `uv run python scripts/release_gate_check.py --check-only`.
- [ ] Non-audio gate runner executed with `uv run python scripts/release_gate_check.py --run`.
- [ ] JSON evidence recorded with `uv run python scripts/release_gate_check.py --run --report-json PATH` when CI/release evidence is needed.
- [ ] JSON evidence rendered with `uv run python scripts/render_release_gate_evidence.py PATH` and manually copied into `docs/release-candidate-evidence.md` when evidence publication is needed.
- [ ] CI Step Summary shows the rendered Markdown evidence, and `.github/workflows/non-audio-release-gates.yml` uploads both JSON report and Markdown snippet artifacts for pull request, push, or manual runs.
- [ ] Optional PyInstaller temp build gate executed with `uv run python scripts/release_gate_check.py --include-packaging-build` when feasible.
- [ ] Dependency sync completes.
- [x] Full pytest suite passes in metadata-fixture smoke evidence.
- [x] Ruff lint passes in metadata-fixture smoke evidence.
- [x] Ruff format check passes in metadata-fixture smoke evidence.
- [x] Automated release smoke prints all PASS lines in metadata-fixture smoke evidence.
- [ ] Desktop launch succeeds.
- [ ] Manual scan/recommend/export QA is completed safely.

Current metadata-only evidence is recorded in `docs/release-candidate-evidence.md`.
