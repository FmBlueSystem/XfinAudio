# Spec Delta: loudness-analysis (NEW)

## ADDED Requirements

### Requirement: EBU R128 measurement

The system SHALL measure per track: integrated loudness (LUFS), loudness range (LRA, LU),
and true peak (dBTP) using a pinned FFmpeg executable with the `ebur128=peak=true` filter,
invoked with an explicit audio-stream mapping and no stdin.

#### Scenario: cover art does not break measurement
- **WHEN** a track with embedded cover art is analyzed
- **THEN** measurement reads only audio streams (`-map 0:a:0`) and produces metrics

#### Scenario: corrupt file produces typed failure
- **WHEN** FFmpeg fails or times out on a file
- **THEN** the profile records a typed failure status persisted across scans, and the
  scan continues with remaining files

#### Scenario: short material
- **WHEN** a track is below the minimum duration floor
- **THEN** integrated LUFS is measured; LRA and true peak are None with status `too_short`

### Requirement: versioned profile persistence

The system SHALL persist one versioned `LoudnessProfile` JSON per track carrying its own
source identity (mtime/size captured after any tag write, plus FLAC audio_md5 when
available), its analysis version, and engine fingerprint.

#### Scenario: tag write-back does not invalidate measurements
- **WHEN** tags are written to a track after analysis
- **THEN** the stored profile remains valid on the next scan without re-decoding

#### Scenario: sibling profiles survive write-back
- **WHEN** loudness tags are written to a non-FLAC track
- **THEN** existing spectral, danceability and edge profiles remain valid on next scan

#### Scenario: new column survives rescans
- **WHEN** `save_scan_results` runs for any track
- **THEN** an existing loudness profile is preserved unless audio identity changed

### Requirement: target-band pool filter

The system SHALL provide a user-selectable LUFS target with hard tolerance band applied as
a playlist pool filter returning filtered tracks plus coverage warnings. Tracks without a
measured profile SHALL stay in the pool exempt from the band while library coverage is
incomplete, and warnings SHALL report coverage numbers.

#### Scenario: partial coverage stays honest
- **GIVEN** 3,412 of 10,392 tracks measured
- **WHEN** the strategy builds a playlist
- **THEN** unmeasured tracks remain eligible and the warning states the coverage numbers

### Requirement: tag write-back

The system SHALL write back analysis results to file tags when values change: a
human-readable summary in the COMMENT field and a structured `XFINAUDIO_LOUDNESS` custom
tag with payload schema version and engine fingerprint. This is the documented exception
to XfinAudio's read-only scanning contract.

#### Scenario: idempotent writes
- **WHEN** analysis values are unchanged since the last write-back
- **THEN** the file is not rewritten

#### Scenario: recovery from tags
- **GIVEN** a track whose DB row lacks a loudness profile but whose structured tag exists
- **WHEN** the library is scanned
- **THEN** measurements are restored from the structured tag where format support allows,
  without decoding audio

### Requirement: governance contract amendment

The system's documentation (README EN/ES, AGENTS.md, CONTRIBUTING.md) SHALL state the
read-only scanning exception for loudness tag write-back, pinned by tests.

#### Scenario: docs pinning
- **WHEN** the documentation test suite runs
- **THEN** amended contract text presence is asserted in all four documents
