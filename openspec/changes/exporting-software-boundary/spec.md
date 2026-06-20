# Spec: Exporting software boundary

## Requirement: Playlist file export software catalog is explicit

XfinAudio SHALL expose a pure export software catalog for non-Serato playlist file export extensions.

### Scenario: Supported software resolves its extension

Given a supported playlist-file export software name,
When its extension is requested,
Then the extension SHALL match the existing export format without writing files.

### Scenario: Unsupported software is rejected

Given an unsupported playlist-file export software name,
When its extension is requested,
Then a `ValueError` SHALL identify the unknown software.

## Requirement: Export filename generation skips empty sanitized suffixes

XfinAudio SHALL avoid empty filename parts when optional filename suffix input sanitizes to an empty string.

### Scenario: Unsafe-only suffix is ignored

Given a suffix containing only unsafe characters,
When the default export filename is generated,
Then the filename SHALL not contain a double separator caused by an empty suffix part.
