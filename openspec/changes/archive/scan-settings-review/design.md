# Design: Scan Settings Review

## Overview

Add a concise, read-only scan settings review line to the Library screen so users can confirm scan expectations before starting a long scan.

## Data flow

```text
AppState.settings.scan.supported_extensions
        +
mixedinkey_contract field mappings
        |
        v
LibraryViewModel.scan_settings_review_text(state)
        |
        v
LibraryScreen.scan_settings_label
```

## ViewModel text

`scan_settings_review_text` returns a single-line string such as:

```text
Scan: .aif .aiff .flac .m4a .mp3 .wav · BPM (TBPM), key (TKEY), energy (COMM:Songs-DB_Custom1/comments)
```

The text is built from:

- `state.settings.scan.supported_extensions`
- Hard-coded field mappings that mirror `xfinaudio.metadata.mixedinkey_contract`.

## UI placement

A new `QLabel` is placed directly below the top controls row in `LibraryScreen`, above the existing `status_label`. It updates on every `render()` call.

## Rendering

`LibraryScreen.render()` already receives `LibraryViewModel` and `AppState`. The new label is updated with `vm.scan_settings_review_text(state)`.

`MainWindow` calls `library_screen.render(...)` whenever the selected folder changes, so the review will update accordingly.

## Tests

- ViewModel tests assert the presence of extension names and field/source names.
- Screen test (Qt offscreen) asserts the label text equals the ViewModel output.

## Safety

- Pure function; no side effects.
- No changes to scan behavior, settings schema, or persistence.
