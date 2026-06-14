# Design: No Unsafe Live Serato Writes

## Overview

This change is communication-only. It updates user-facing copy and release notes to state that live Serato library writes are not verified as part of the release candidate.

## UI copy changes

### `ExportViewModel`

- `empty_state_text()`: append a sentence that live Serato writes are not part of the verified release candidate and require manual backup/verification.
- `destination_text()`: clarify that exports land in the configured safe export folder and must be manually copied to a live `_Serato_/Subcrates` directory.

### `ExportScreen`

- Default `export_guidance_label` text includes the live-write warning.

## Release notes

`docs/release-notes-template.md` keeps existing warnings and adds an explicit sentence that live Serato writes are not part of the verified release candidate.

## Tests

- `tests/test_export_view_model.py`: instantiate `ExportViewModel` and assert warning phrases in returned strings.
- `tests/test_export_screen_copy.py`: instantiate `ExportScreen` offscreen and assert the guidance label contains the warning.

## Safety

- No functional changes.
- No export coordinator changes.
- No audio or file-system changes.
