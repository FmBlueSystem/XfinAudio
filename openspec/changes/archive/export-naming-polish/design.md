# Design: Export Naming Polish

## Overview

Introduce a centralized filename generator so non-Serato DJ software exports get descriptive, timestamped, filesystem-safe default names instead of the static `"XfinAudio Export"` fallback.

## Filename format

```text
{timestamp}_{strategy_name}_{suffix}_{track_count}_tracks
```

Example:

```text
20260614_005222_EnergyBoost_rekordbox_12_tracks
```

- `timestamp`: `%Y%m%d_%H%M%S` from `generated_at` or `datetime.now()`.
- `strategy_name`: `recommendation.strategy.name` sanitized.
- `suffix`: optional DJ software identifier (e.g. `rekordbox`, `traktor`, `virtualdj`).
- `track_count`: number of tracks in the recommendation.

## Sanitization rules

- Replace any character that is not alphanumeric, underscore, hyphen, or dot with `_`.
- Collapse consecutive underscores.
- Strip leading/trailing underscores and hyphens.
- Keep the result lowercase for filesystem safety.

## Integration

```text
ExportCoordinator.preview_non_serato_export
ExportCoordinator.export_recommendation_to_non_serato
        |
        v
default_export_filename(recommendation, generated_at, suffix=software.lower())
        |
        v
write_rekordbox_playlist_xml(..., playlist_name=name)
write_traktor_playlist_nml(..., playlist_name=name)
write_virtualdj_playlist_xml(..., playlist_name=name)
```

## Tests

- `tests/test_export_naming.py` tests the utility directly with fixed timestamps and mocked recommendations.
- `tests/test_export_coordinator.py` is updated only if existing assertions reference the old default name.

## Safety

- Pure function; no file system writes.
- No changes to Serato export naming.
- Backward-compatible for callers that provide an explicit `crate_name` or use a Prep Copilot variant.
