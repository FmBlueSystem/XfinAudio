# PyInstaller packaging spike

XfinAudio now has a safe, pinned PyInstaller packaging spike for a macOS app-bundle candidate. The committed artifacts are limited to the spec file, smoke script, tests, lockfile, and documentation; generated `build/` and `dist/` outputs must stay out of the project root.

## Quick path

```bash
uv run python scripts/pyinstaller_build_smoke.py --check-only
uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch
uv run pytest -v tests/test_pyinstaller_packaging.py
```

Use the check-only command for routine verification. It prints the project-pinned PyInstaller version and the committed spec path without running a build.

## Temporary build smoke

```bash
uv run python scripts/pyinstaller_build_smoke.py --build-temp
uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch
```

The build smoke directs PyInstaller output to temporary paths by passing `--distpath` and `--workpath`. After a successful build it prints the PyInstaller warning report path plus expected/unexpected warning counts. With `--validate-launch`, it launches the built executable in package smoke mode and points app data to temp-only paths. It must not create project-root `dist/` or `build/` directories.

## Warning triage

The smoke script parses `warn-xfinaudio.txt` from the temp work directory and non-fatally triages PyInstaller analysis warnings. The allowlist is limited to observed optional, platform, development, typing, and PyInstaller/modulegraph false-positive groups. Unknown warning lines are still printed as unexpected; no hidden imports or excludes are added by triage alone.

## Package smoke mode

| Environment variable | Purpose |
|----------------------|---------|
| `XFINAUDIO_PACKAGE_SMOKE=1` | Initializes `QApplication` and `MainWindow.with_defaults(...)`, then exits `0` before `show()`/`exec()`. |
| `XFINAUDIO_DB_PATH` | Overrides the SQLite path for smoke validation. |
| `XFINAUDIO_SETTINGS_PATH` | Overrides the settings JSON path for smoke validation. |

The launch validator creates these paths under the temp PyInstaller root, not under `~/.xfinaudio`.

## Committed packaging configuration

| Area | Decision |
|------|----------|
| Spec path | `packaging/pyinstaller/xfinaudio.spec` |
| Entry point | `src/xfinaudio/desktop/app.py` |
| App name | `XfinAudio` |
| Bundle shape | PyInstaller onedir collection wrapped as `XfinAudio.app` on macOS |
| Icon/data files | None in this spike |
| Artifact hygiene | `.gitignore` excludes root `build/` and `dist/`; `*.spec` is not globally ignored |
| Dev dependency | `pyinstaller==6.20.0` is pinned exactly in the project dev dependency group and locked by `uv.lock` |
| Launch validation | `--validate-launch` requires `--build-temp` and uses temp DB/settings paths |
| Warning triage | `scripts/pyinstaller_build_smoke.py` reports the temp `warn-xfinaudio.txt` path plus expected/unexpected warning counts |

## Verification evidence

| Check | Result |
|-------|--------|
| RED focused tests | `uv run pytest -v tests/test_pyinstaller_packaging.py` failed with 6 expected failures for missing pin, smoke helpers, env docs, and launch validation. |
| GREEN focused tests | `uv run pytest -v tests/test_pyinstaller_packaging.py` passed: 16 tests. |
| Project PyInstaller | `uv run pyinstaller --version` printed `6.20.0`. |
| Check-only smoke | `uv run python scripts/pyinstaller_build_smoke.py --check-only` printed PyInstaller `6.20.0` and the committed spec path. |
| Temp launch smoke | `uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch` completed under `/var/folders/.../T/xfinaudio-pyinstaller-yxoc01yv/`, reported `PyInstaller expected warnings: 57` and `PyInstaller unexpected warnings: 0`, and launched `XfinAudio.app/Contents/MacOS/XfinAudio` in package smoke mode with temp DB/settings paths. |

## Important limits

- No DMG/pkg installer was created.
- No Developer ID signing or notarization was configured.
- No publishing or release upload was added.
- No product behavior changed outside explicit package smoke environment variables.
- No live Serato writes or audio mutation were introduced.
- The smoke build now uses the project environment (`uv run pyinstaller`, observed `6.20.0` on Python `3.11.13`), but GPL-3.0-only full open-source binary/app bundle redistribution reproducibility still needs CI or clean-machine evidence.
- PyInstaller still writes analysis warning files under the temp build path; the current smoke triages observed warnings as expected, but clean-account and CI runs should keep reviewing unexpected warnings before any public release or redistribution readiness claim.
- Binary/app bundle redistribution, PySide6/Qt, mutagen, signing/notarization/DMG, and third-party dependencies still require release-specific legal review. No legal clearance is implied.

## Next step

Run the same temp launch validation on a clean macOS test account before any signing, notarization, or installer work.
