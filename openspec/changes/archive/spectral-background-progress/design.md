# Design: Spectral Background Progress Indicator

## Decision question

Where and how should the app communicate that spectral profiles are being completed in the background?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Dedicated progress bar in LibraryScreen | Very visible; shows percentage. | Adds new widget and layout; overkill for a background completion task. | Rejected. |
| B. Status line in LibraryScreen.status_label | Reuses existing widget; minimal intrusion; consistent with scan progress. | Less visually prominent. | **Selected.** |
| C. MainWindow.status_label | Central location. | Breaks the screen-level ViewModel pattern; MainWindow.status_label is used for app-wide messages. | Rejected. |
| D. Update Color column cell text temporarily | Direct association with the data being computed. | Noisy; requires per-row state; hard to read overall progress. | Rejected. |

## Architecture impact

```text
SpectralCompletionWorker
    │ progress_updated(processed, total)
    ▼
MainWindow._on_spectral_progress_updated
    │ model_copy(update={is_completing_spectral, spectral_progress_count, spectral_total_count})
    ▼
AppState
    ▼
LibraryViewModel.status_text(state)
    ▼
LibraryScreen.status_label
```

## Affected files

- `src/xfinaudio/desktop/app_state.py` — add `is_completing_spectral`, `spectral_progress_count`, `spectral_total_count`.
- `src/xfinaudio/desktop/spectral_completion_worker.py` — emit `progress_updated(processed, total)` from `_SpectralCompletionRunner`.
- `src/xfinaudio/desktop/main_window.py` — connect `progress_updated` and `finished` to update `AppState`.
- `src/xfinaudio/desktop/library_view_model.py` — return spectral progress text when completion is active.
- `tests/test_spectral_completion_worker.py` — assert `progress_updated` signal and counts.
- `tests/test_library_view_model.py` — assert spectral progress status text.
- `tests/test_main_window.py` — assert AppState updates on progress/finished.

## Safety

- No audio mutation.
- No DSP scope expansion.
- AppState updates use `model_copy(update=...)`.
- Existing widget tests are protected by the global `_disable_spectral_completion_worker` fixture; new tests will use isolated workers or mocks.
