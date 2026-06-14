# Design: XfinAudio Quality Tooling Baseline

## Goal

Add static type checking, test coverage measurement, and a real-audio E2E smoke test while keeping product behavior unchanged.

## Architecture impact

- **No new runtime modules**. All changes are dev dependencies, configuration, tests, and documentation.
- **Type checker integration**: `pyright` runs against `src/` and `tests/` with a permissive initial configuration.
- **Coverage integration**: `pytest-cov` measures line coverage against `src/xfinaudio` with a 70% fail-under threshold.
- **E2E smoke test**: A new pytest file writes MIK-style tags into a copied real WAV fixture and exercises scan → persist → recommend → Serato export.

## Affected files

| File | Change |
|------|--------|
| `pyproject.toml` | Add `pyright` and `pytest-cov` dev dependencies; add `[tool.pyright]` and `[tool.coverage.*]` sections. |
| `uv.lock` | Lock new dependencies. |
| `openspec/config.yaml` | Enable `type_checker`, `coverage`, and `e2e`; update validation commands. |
| `.github/workflows/non-audio-release-gates.yml` | Run pyright and coverage in CI. |
| `scripts/release_gate_check.py` | Add `type-check` and `coverage` command gates. |
| `tests/test_release_gate_check.py` | Update expected gate lists. |
| `tests/test_smoke_real_audio_scan_recommend_export.py` | New real-audio E2E smoke test. |
| `src/xfinaudio/recommendation/controls.py` | Accept `AbstractSet[str]` for `locked_paths`/`excluded_paths` so `AppState` frozensets are valid. |
| `src/xfinaudio/recommendation/playlist_service.py` | Guard `energy_tolerance` being `None`. |
| `src/xfinaudio/library/playlist_repository.py` | Assert `lastrowid` is not `None`. |
| `src/xfinaudio/exporting/traktor_nml.py` | Rename shadowed local `parent` variable. |
| `src/xfinaudio/desktop/build_view_model.py` | Cast strategy name to `StrategyName`. |
| `src/xfinaudio/desktop/scan_controller.py` | Type `workflow_service` as `PlaylistWorkflowService`. |
| `src/xfinaudio/desktop/recommendation_controller.py` | Type `workflow_service` as `PlaylistWorkflowService`. |
| `src/xfinaudio/desktop/screens/library_screen.py` | Narrow sort column before lambda; widen sort-key return type. |
| `src/xfinaudio/desktop/screens/review_screen.py` | Create empty `QTableWidgetItem` when header item is missing. |
| `src/xfinaudio/desktop/menu_builder.py` | Cast host to `QObject`. |
| `src/xfinaudio/desktop/settings_controller.py` | Cast host to `QWidget`. |
| `src/xfinaudio/desktop/main_window.py` | Suppress protocol/property type-check noise at coordinator construction sites. |
| Various tests | Add nullability assertions/casts to satisfy pyright. |
| `AGENTS.md` and `.atl/skills/gentle-ai-sdd-tdd/SKILL.md` | Update verification commands. |

## Safety considerations

- The smoke test only writes inside `tmp_path`; no real Serato library is touched.
- The committed fixture is never mutated; a copy is tagged for each test run.
- No audio DSP or signal processing is introduced.

## Rollback

- Revert `pyproject.toml` dependency and config changes.
- Delete `tests/test_smoke_real_audio_scan_recommend_export.py`.
- Revert `scripts/release_gate_check.py` and its tests.
- Revert `openspec/config.yaml`, CI, and documentation updates.
