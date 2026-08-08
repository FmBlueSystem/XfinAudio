# Tasks: Spectral Color Features

## Task 1 — Add spectral analyzer module

Implement `src/xfinaudio/audio/spectral_profile.py` with `SpectralProfile`, `analyze_spectral_profile`, and `score_spectral_similarity`.

- [ ] RED: Write failing tests in `tests/audio/test_spectral_profile.py` asserting synthetic fixture classification.
- [ ] GREEN: Implement `SpectralProfile` model and `analyze_spectral_profile`.
- [ ] GREEN: Implement `score_spectral_similarity`.
- [ ] REFACTOR: Clean naming and add docstrings.
- [ ] VERIFY: `uv run pytest tests/audio/test_spectral_profile.py -q` passes.

## Task 2 — Add librosa/numpy dependency

- [ ] Update `pyproject.toml` with pinned `librosa` and `numpy`.
- [ ] Run `uv lock` and commit `uv.lock`.
- [ ] VERIFY: `uv run python -c "import librosa, numpy; print(librosa.__version__)"` succeeds.

## Task 3 — Persist spectral profile in SQLite

- [ ] RED: Write failing test in `tests/library/test_track_repository.py` asserting profile round-trip.
- [ ] GREEN: Bump `SCHEMA_VERSION` to 2, add `spectral_profile_json` column, implement migration.
- [ ] GREEN: Update `TrackRecord` serialization/deserialization in `TrackRepository`.
- [ ] REFACTOR: Extract migration helpers if duplication appears.
- [ ] VERIFY: Repository tests pass.

## Task 4 — Integrate analysis into scan service

- [ ] RED: Write failing test in `tests/library/test_scan_service.py` asserting spectral profile is attached when analyzer is available.
- [ ] GREEN: Call `analyze_spectral_profile` in `scan_folder` after metadata parsing.
- [ ] GREEN: Make analysis optional/fallback-safe (missing librosa → profile is None).
- [ ] REFACTOR: Keep scan loop readable.
- [ ] VERIFY: Scan service tests pass.

## Task 5 — Add spectral component to transition scoring

- [ ] RED: Write failing test in `tests/recommendation/test_scoring.py` asserting spectral similarity scoring.
- [ ] GREEN: Add `spectral` weight to `ScoringWeights` and spectral component to `score_transition`.
- [ ] GREEN: Handle missing profiles by ignoring the spectral component.
- [ ] REFACTOR: Ensure component score stays within [0, 1].
- [ ] VERIFY: Scoring tests pass.

## Task 6 — Add spectral jump warnings

- [ ] RED: Write failing test asserting a warning on RED→GREEN transition.
- [ ] GREEN: Add spectral jump detection in quality/review layer.
- [ ] REFACTOR: Reuse existing warning formatting.
- [ ] VERIFY: Quality tests pass.

## Task 7 — UI color badges

- [ ] RED: Write failing test for color badge helper.
- [ ] GREEN: Add helper that maps `SpectralProfile.dominant_color` to display text/badge.
- [ ] GREEN: Show badge in library table and review table.
- [ ] VERIFY: UI tests pass (or manual QA if UI tests are limited).

## Task 8 — Multiprocessing optimization (optional follow-up)

- [ ] Benchmark sequential vs `ProcessPoolExecutor` on a small folder.
- [ ] If speedup is significant, integrate batch analysis in scan worker.
- [ ] VERIFY: Cancellation still works; no orphan processes.

## Task 9 — Update rules and documentation

- [ ] Update `openspec/config.yaml` and `gentle-ai-sdd-tdd` skill to allow read-only offline spectral analysis.
- [ ] Update `NOTICE.md` if dependency redistribution implications change.
- [ ] Update `docs/open-source-license.md` if binary redistribution caveats change.
- [ ] VERIFY: `tests/test_open_source_license_docs.py` and related pass.

## Task 10 — Final verification

- [ ] Run `uv run pytest -q`.
- [ ] Run `uv run pyright src tests`.
- [ ] Run `uv run pytest --cov --cov-fail-under=70 -q`.
- [ ] Run `uv run ruff check .` and `uv run ruff format --check .`.
- [ ] Run `uv run python scripts/release_gate_check.py --run`.
- [ ] Manual QA: scan a small folder, verify color badges and warnings.
- [ ] Write `verify-report.md`.
