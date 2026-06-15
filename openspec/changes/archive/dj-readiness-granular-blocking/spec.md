# Specification: Granular DJ Readiness Blocking

## Requirements

### R1. Soft quality warnings

**GIVEN** a playlist with max adjacent BPM jump above 3%  
**WHEN** `build_dj_readiness_report` runs  
**THEN** the BPM continuity check returns `needs_review` (not `blocked`).

**GIVEN** a playlist with average transition score below 0.65  
**WHEN** `build_dj_readiness_report` runs  
**THEN** the average score check returns `needs_review` (not `blocked`).

**GIVEN** a playlist with transition warnings  
**WHEN** `build_dj_readiness_report` runs  
**THEN** the transition warning check returns `needs_review`.

### R2. Hard data integrity blockers

**GIVEN** a playlist with < 2 tracks  
**WHEN** `build_dj_readiness_report` runs  
**THEN** the playlist size check returns `blocked`.

**GIVEN** a playlist with incomplete or missing-metadata tracks  
**WHEN** `build_dj_readiness_report` runs  
**THEN** the metadata check returns `blocked`.

**GIVEN** a Serato round-trip failure  
**WHEN** `validate_serato_round_trip` runs  
**THEN** it returns `blocked`.

### R3. Export gating

**GIVEN** the readiness report status is `needs_review`  
**WHEN** `ReviewViewModel.can_export` is called  
**THEN** it returns `True`.

**GIVEN** the readiness report status is `blocked`  
**WHEN** `ReviewViewModel.can_export` is called  
**THEN** it returns `False`.

## Non-functional

- The change must not break existing readiness tests.
- The change must stay within the 400-line review budget.
