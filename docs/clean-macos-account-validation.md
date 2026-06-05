# Clean macOS account validation runbook

Use this checklist to validate the PyInstaller temporary app launch from a clean macOS user account. This is a manual gate for packaging confidence; it is not signing, notarization, installer creation, or release publishing.

## Purpose and non-goals

| Topic | Decision |
|-------|----------|
| Purpose | Run the existing temp PyInstaller launch smoke from a clean macOS account and record enough evidence to compare it with local developer-account smoke output. |
| Non-goal | Do not create committed build artifacts, root `build/` or `dist/`, installers, signed binaries, notarized apps, or published release files. |
| Status | Passing local temp-launch smoke is not clean-account validation. Clean-account validation remains pending until this command is manually run from the clean account. |

## Preflight checklist

1. Create or choose a macOS user account that has not previously run XfinAudio.
2. Log in to that account directly, not by reusing the developer account shell.
3. Confirm the account has access to a project checkout outside root-owned or quarantined paths.
4. Install or make available `uv` and the project Python version without copying build outputs from another account.
5. From the project root, confirm no root packaging artifacts exist:
   ```bash
   test ! -d build && test ! -d dist
   ```
6. Synchronize dependencies if needed:
   ```bash
   uv sync
   ```

## Command to run

Run exactly this command from the project checkout:

```bash
uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch
```

The command must use temporary PyInstaller paths and must not create project-root `build/` or `dist/` directories.

## Expected output markers

Record the full command output. The successful clean-account run should include these markers:

```text
PyInstaller version: 6.20.0
PyInstaller warning report: <temp-root>/build/xfinaudio/warn-xfinaudio.txt
PyInstaller expected warnings: 57
PyInstaller unexpected warnings: 0
Launch validation completed in package smoke mode.
```

The app path should be inside the temporary PyInstaller root, typically ending with:

```text
/dist/XfinAudio.app/Contents/MacOS/XfinAudio
```

The DB path and settings path should be temp-only package smoke paths, not `~/.xfinaudio`:

```text
<temp-root>/smoke/xfinaudio.sqlite3
<temp-root>/smoke/settings.json
```

## Evidence fields to record

| Field | Value |
|-------|-------|
| Date/time | |
| Tester | |
| macOS version | |
| CPU architecture | |
| account type | Clean standard user / clean admin user / other: |
| Project checkout path | |
| Command | `uv run python scripts/pyinstaller_build_smoke.py --build-temp --validate-launch` |
| Full command output | Attach or paste. |
| PyInstaller version | Expected: `6.20.0`. |
| Warning report path | |
| Expected warning count | Expected: `57`. |
| Unexpected warning count | Expected: `0`. |
| App path | Temp `XfinAudio.app/Contents/MacOS/XfinAudio` path. |
| DB path | Temp `smoke/xfinaudio.sqlite3` path. |
| settings path | Temp `smoke/settings.json` path. |
| Root artifact check | Confirm project-root `build/` and `dist/` are absent after the run. |
| Result | Pending / pass / fail. |

## Failure triage

| Symptom | First checks |
|---------|--------------|
| Unexpected warnings | Save the warning report, compare unknown lines with the existing allowlist, and do not claim validation until each warning is resolved or explicitly triaged. |
| Launch failure | Save stdout/stderr, app path, return code, and temp DB/settings paths. Re-run only after preserving the first failure evidence. |
| Permissions or quarantine | Confirm the checkout and temp directories are readable/executable by the clean account. Check whether macOS quarantine attributes are blocking execution. |
| Missing `uv` or Python | Install the expected toolchain for the clean account, then re-run from a clean checkout state. Do not reuse another account's `.venv` as evidence. |
| PySide6/Qt errors | Capture stderr and macOS version/CPU architecture. Verify the dependency environment was created by `uv` in the clean account. |

## Status statement

Passing local temp-launch smoke is not clean-account validation. Clean-account validation remains pending until this command is manually run from the clean account and the evidence above is recorded.
