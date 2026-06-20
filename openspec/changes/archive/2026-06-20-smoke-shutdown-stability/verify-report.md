# Verify Report: Smoke shutdown stability

Status: passed-local-and-ci

## Focused evidence

- PASS: `uv run pytest tests/test_desktop_app.py -q`
- PASS: `uv run pytest tests/test_desktop_app.py tests/test_pyinstaller_packaging.py::test_desktop_main_exits_before_event_loop_in_package_smoke_mode -q`
- PASS: `QT_QPA_PLATFORM=offscreen XFINAUDIO_PACKAGE_SMOKE=1 uv run xfinaudio` exited 0 with no stderr/stdout traceback output.
- PASS: `uv run pyright src/xfinaudio/desktop/app.py tests/test_desktop_app.py tests/test_pyinstaller_packaging.py`
- PASS: `uv run ruff check src/xfinaudio/desktop/app.py tests/test_desktop_app.py tests/test_pyinstaller_packaging.py`
- PASS: `uv run ruff format --check src/xfinaudio/desktop/app.py tests/test_desktop_app.py tests/test_pyinstaller_packaging.py`

## Full gate evidence

- PASS: `uv run pytest -q` — 938 passed.
- PASS: `uv run pyright src tests` — 0 errors, 0 warnings.
- PASS: `uv run pytest --cov --cov-fail-under=70 -q` — 938 passed, total coverage 89.95%.
- PASS: `uv run ruff check .`
- PASS: `uv run ruff format --check .`
- PASS: `uv run python scripts/release_gate_check.py --run`

## CI and merge evidence

- PASS: PR #210 Non-audio release gates — run `27868414085`.
- PASS: PR #210 merged at `2026-06-20T10:31:16Z` with merge commit `47b795295e406026fcd9a3329b33d0424227e081`.
- PASS: main Non-audio release gates — run `27868467432`.

## Local GUI launch note

- INCONCLUSIVE in Codex environment: direct `uv run xfinaudio` has no screen available, and later local process inspection via `ps`/`pgrep` was blocked by the host process APIs. This does not invalidate the package smoke fix; it only means display-backed GUI confirmation must be performed from the user's desktop session if needed.

## Safety evidence

- No DSP, audio mutation, Serato DB V2, export format, dependency, project-root `build/`, or project-root `dist/` changes were made.
