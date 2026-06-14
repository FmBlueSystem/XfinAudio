# Proposal: Spectral Background Progress Indicator

## Intent

Make the background spectral profile completion visible to the DJ so they know the app is still working after a metadata scan or when a saved library is loaded.

## Scope

### In scope

- Emit per-file progress counts from `SpectralCompletionWorker`.
- Track spectral completion state in `AppState`.
- Display a concise progress message in the Library screen status line while profiles are being completed.
- Clear the progress message when the worker finishes or is cancelled.

### Out of scope

- Cancelling spectral completion independently (existing cancellation token is unchanged).
- Progress bars, modal dialogs, or tray notifications.
- Changing spectral analysis algorithm or cache behavior.

## Motivation

Manual QA showed that after scanning a folder the app appears idle while `SpectralCompletionWorker` analyzes audio in the background. On large libraries this can take minutes, and the DJ has no indication that work is happening or when it will finish.

## Success criteria

1. While spectral completion is running, the Library screen status label shows progress as `Analyzing spectral colors 3/10`.
2. When spectral completion finishes, the status label returns to the normal library summary.
3. Cached profiles are counted as completed immediately.
4. All verification commands pass.
5. No audio files are mutated.

## Rollback plan

- Remove the new `AppState` fields and the progress signal from `SpectralCompletionWorker`.
- Restore `LibraryViewModel.status_text()` to the previous behavior.
- Remove associated tests.

## Review budget

Estimated changed lines: ~80 production + ~60 test lines, well within the 400-line budget.
