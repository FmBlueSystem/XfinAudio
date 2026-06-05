# Scan Progress and Cooperative Cancel

Date: 2026-06-03

## Scope

XfinAudio now exposes a scan progress/cancel seam for long metadata scans without changing audio files, recommendation algorithms, or export workflows.

## Behavior

- `scan_folder(...)` keeps the existing successful return shape: `list[TrackRecord]`.
- Callers may pass `on_progress` to receive `ScanProgress(processed_count, total_count, current_path)` after each supported audio file is processed.
- Unsupported files are excluded from `total_count`.
- Callers may pass a `ScanCancellationToken` and request cancellation with `cancel()`.
- Cancellation is cooperative and checked between supported files. The current metadata read is allowed to finish.
- A canceled scan raises `ScanCancelledError` from the library seam with records scanned so far for display-only use.
- `PlaylistWorkflowService.scan_folder(...)` catches cancellation, returns `cancelled=True`, and does not call `save_scan_results`.

## Desktop UI

The desktop window adds:

- a disabled-by-default `Cancel Scan` button;
- a scan progress label;
- synchronous scan state that enables cancel while a scan is running;
- cancellation status text that states no partial scan results were saved.

The current implementation is intentionally synchronous. The cancel request is non-destructive, but it is not a background-worker interrupt and does not stop an in-progress Mutagen read mid-file.

## Future worker path

A future background worker/thread can reuse the same domain seam:

1. create a `ScanCancellationToken` at scan start;
2. pass `on_progress` updates through a UI-safe signal/queue;
3. call `cancel()` from the UI;
4. preserve the workflow rule that canceled scans never persist partial records.

## Verification

Focused verification:

```bash
uv run pytest -v tests/test_scan_service.py tests/test_playlist_workflow.py tests/test_main_window.py
```

Full verification should include:

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```
