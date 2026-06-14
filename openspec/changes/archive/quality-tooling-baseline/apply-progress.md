# Apply Progress: XfinAudio Quality Tooling Baseline

## Summary

All planned tasks were applied. The project now has pyright, pytest-cov, and a real-audio E2E smoke test integrated into the local verification flow, CI, and release gate runner.

## Key decisions

- Kept pyright in `basic` mode with several noisy rules disabled to avoid a massive protocol/Qt refactor. The value is establishing the gate; strictness can be raised later.
- Changed `DJControls.locked_paths`/`excluded_paths` from `set[str]` to `AbstractSet[str]` so `AppState` frozensets are accepted without a larger refactor.
- Used targeted `cast` and `# type: ignore[reportArgumentType]` for known Qt/Protocol mismatches rather than redesigning the host protocols.
- Set coverage fail-under to 70%; actual baseline is ~88%.

## Files changed

- `pyproject.toml`
- `uv.lock`
- `openspec/config.yaml`
- `.github/workflows/non-audio-release-gates.yml`
- `scripts/release_gate_check.py`
- `tests/test_release_gate_check.py`
- `tests/test_smoke_real_audio_scan_recommend_export.py`
- `src/xfinaudio/recommendation/controls.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `src/xfinaudio/library/playlist_repository.py`
- `src/xfinaudio/exporting/traktor_nml.py`
- `src/xfinaudio/desktop/build_view_model.py`
- `src/xfinaudio/desktop/scan_controller.py`
- `src/xfinaudio/desktop/recommendation_controller.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/review_screen.py`
- `src/xfinaudio/desktop/menu_builder.py`
- `src/xfinaudio/desktop/settings_controller.py`
- `src/xfinaudio/desktop/main_window.py`
- `tests/test_build_view_model.py`
- `tests/test_export_view_model.py`
- `tests/test_review_view_model.py`
- `tests/test_playlist_repository.py`
- `tests/test_table_populators.py`
- `AGENTS.md`
- `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`
