# Specification: Spectral Background Progress Indicator

## Glossary

- **Spectral completion**: the background process that computes missing `SpectralProfile` values after a scan or library load.
- **Spectral progress**: a `(processed_count, total_count)` pair indicating how many tracks have been completed so far.

## Requirements

### R1. Worker progress signal

**GIVEN** a `SpectralCompletionWorker` with missing spectral profiles  
**WHEN** the worker processes a track  
**THEN** it emits a `progress` signal containing the completed profile **and** a `progress_updated` signal containing `(processed_count, total_count)`.

**GIVEN** cached profiles exist for some tracks  
**WHEN** the worker starts  
**THEN** those tracks are counted as completed immediately in the first progress update.

### R2. AppState tracking

**GIVEN** spectral completion is running  
**THEN** `AppState.is_completing_spectral` is `True`, `spectral_progress_count` equals completed tracks, and `spectral_total_count` equals tracks needing completion.

**GIVEN** spectral completion finishes or is cancelled  
**THEN** `AppState.is_completing_spectral` is `False` and both counts are reset to `0`.

### R3. Library screen status text

**GIVEN** spectral completion is running with 3 of 10 tracks completed  
**WHEN** the Library screen renders  
**THEN** the status label shows `Analyzing spectral colors 3/10`.

**GIVEN** spectral completion is not running and tracks exist  
**WHEN** the Library screen renders  
**THEN** the status label shows the existing track-count summary.

### R4. MainWindow wiring

**GIVEN** a running spectral completion worker  
**WHEN** the worker emits a progress update  
**THEN** `MainWindow` updates `AppState` immutably and triggers a UI sync.

**GIVEN** the worker finishes  
**THEN** `MainWindow` clears the spectral completion state.

## Non-functional

- `AppState` remains immutable; use `model_copy(update=...)` for updates.
- The change must not break existing widget tests (spectral completion is already disabled by `conftest.py`).
- The change must stay within the 400-line review budget.
