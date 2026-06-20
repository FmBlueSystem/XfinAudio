# Design: Exporting software boundary

## Approach

Create `xfinaudio.exporting.software` with a pure mapping for existing non-Serato playlist-file export extensions and a `playlist_file_extension()` lookup helper. Keep concrete writer functions in their existing modules. Update planning/application dispatch to consume the pure catalog rather than duplicating format knowledge.

For filename generation, sanitize the optional suffix first and append it only when the sanitized value is non-empty.

## Safety

The extension mapping preserves existing file extensions. No export format, audio, DSP, or Serato DB V2 behavior changes are introduced.
