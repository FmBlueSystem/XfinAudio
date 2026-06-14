# Tasks: XfinAudio Quality Tooling Baseline

## 1. Add pyright static type checker

- [x] Add `pyright` to dev dependencies.
- [x] Configure `[tool.pyright]` in `pyproject.toml` with permissive initial rules.
- [x] Run `uv run pyright src tests` and record baseline errors.
- [x] Fix real type errors:
  - [x] `traktor_nml.py` shadowed variable.
  - [x] `playlist_repository.py` `lastrowid` nullability.
  - [x] `playlist_service.py` `energy_tolerance` nullability.
  - [x] `build_view_model.py` strategy name casting.
  - [x] `scan_controller.py` / `recommendation_controller.py` workflow service typing.
  - [x] `library_screen.py` sort key typing.
  - [x] `review_screen.py` `QTableWidgetItem` construction.
  - [x] `menu_builder.py` / `settings_controller.py` host casting.
  - [x] `main_window.py` coordinator construction suppressions.
  - [x] Various test nullability fixes.
- [x] Verify `uv run pyright src tests` passes.

## 2. Add pytest-cov coverage measurement

- [x] Add `pytest-cov` to dev dependencies.
- [x] Configure `[tool.coverage.run]` and `[tool.coverage.report]` in `pyproject.toml`.
- [x] Set initial fail-under threshold to 70%.
- [x] Verify `uv run pytest --cov --cov-fail-under=70 -q` passes and reports baseline.

## 3. Add real-audio E2E smoke test

- [x] Create `tests/test_smoke_real_audio_scan_recommend_export.py`.
- [x] Copy `tests/fixtures/silence_1s.wav` into a temporary directory.
- [x] Write MIK-style ID3 tags (BPM, Camelot key, energy, title, artist, genre).
- [x] Exercise real `MetadataScanService`, `TrackRepository`, `PlaylistWorkflowService`.
- [x] Plan and write a Serato crate into a temporary `_Serato_/Subcrates` folder.
- [x] Assert the crate contains the expected relative track paths.
- [x] Verify the test passes and pyright is happy.

## 4. Update configuration and CI

- [x] Update `openspec/config.yaml` to mark type_checker, coverage, and e2e as available.
- [x] Update `scripts/release_gate_check.py` with type-check and coverage gates.
- [x] Update `tests/test_release_gate_check.py` expected gate lists.
- [x] Update `.github/workflows/non-audio-release-gates.yml` to run pyright and coverage.
- [x] Update `AGENTS.md` and `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` verification commands.

## 5. Final verification

- [x] `uv run pytest -q` passes.
- [x] `uv run pyright src tests` passes.
- [x] `uv run pytest --cov --cov-fail-under=70 -q` passes.
- [x] `uv run ruff check .` passes.
- [x] `uv run ruff format --check .` passes.
- [x] `uv run python scripts/release_gate_check.py --run` passes.
