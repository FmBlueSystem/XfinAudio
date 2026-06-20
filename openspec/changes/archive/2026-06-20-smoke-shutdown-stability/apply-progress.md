# Apply Progress: Smoke shutdown stability

## 2026-06-20

- Created SDD artifacts for smoke shutdown stability.
- RED: added `test_package_smoke_exits_without_creating_main_window`; it failed because `desktop_app.main()` still called `MainWindow.with_defaults(...)` before returning from package smoke mode.
- GREEN: moved the `package_smoke_enabled()` guard before `MainWindow.with_defaults(...)`, keeping smoke validation limited to QApplication/config/translator startup and preventing desktop controllers/workers from starting.
- Focused evidence: `uv run pytest tests/test_desktop_app.py -q` passed.
- Runtime evidence: `QT_QPA_PLATFORM=offscreen XFINAUDIO_PACKAGE_SMOKE=1 uv run xfinaudio` exited 0 with no spectral worker traceback output.
