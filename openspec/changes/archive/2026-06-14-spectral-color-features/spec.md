# Specification: Spectral Color Features

## Requirement 1: Offline spectral analysis of audio files

The system SHALL extract read-only spectral features from supported audio files during scan.

### Scenario 1.1: Synthetic red track

- **GIVEN** a synthetic 100 Hz sine wave saved as `assets/synthetic_color_tests/red_100hz.wav`
- **WHEN** the spectral analyzer processes the file
- **THEN** the resulting `SpectralProfile` SHALL have `dominant_color` equal to `RED`
- **AND** `red_ratio` SHALL be greater than 0.8

### Scenario 1.2: Synthetic green track

- **GIVEN** a synthetic 500 Hz sine wave saved as `assets/synthetic_color_tests/green_500hz.wav`
- **WHEN** the spectral analyzer processes the file
- **THEN** the resulting `SpectralProfile` SHALL have `dominant_color` equal to `GREEN`
- **AND** `green_ratio` SHALL be greater than 0.8

### Scenario 1.3: Synthetic blue track

- **GIVEN** a synthetic 8000 Hz sine wave saved as `assets/synthetic_color_tests/blue_8000hz.wav`
- **WHEN** the spectral analyzer processes the file
- **THEN** the resulting `SpectralProfile` SHALL have `dominant_color` equal to `BLUE`
- **AND** `blue_ratio` SHALL be greater than 0.8

### Scenario 1.4: Real track labeled red

- **GIVEN** a real track the DJ labels as red (e.g., `Lipps Inc - Funkytown`)
- **WHEN** the spectral analyzer processes the file
- **THEN** the resulting `SpectralProfile` SHALL have `dominant_color` equal to `RED`

### Scenario 1.5: Real track labeled green

- **GIVEN** a real track the DJ labels as green (e.g., `Anita Ward - Ring My Bell`)
- **WHEN** the spectral analyzer processes the file
- **THEN** the resulting `SpectralProfile` SHALL have `dominant_color` equal to `GREEN`

### Scenario 1.6: Analyzer handles failures gracefully

- **GIVEN** an unsupported or corrupt audio file
- **WHEN** the spectral analyzer processes the file
- **THEN** it SHALL return `None` for the spectral profile
- **AND** it SHALL NOT raise an unhandled exception
- **AND** it SHALL NOT mutate the audio file

## Requirement 2: Spectral feature persistence

The system SHALL cache spectral features in the app-owned SQLite database.

### Scenario 2.1: Features survive restart

- **GIVEN** a track whose spectral profile has been computed and saved
- **WHEN** the application restarts and loads the library
- **THEN** the `TrackRecord` returned by the repository SHALL include the saved `SpectralProfile`

### Scenario 2.2: Features are updated on re-scan

- **GIVEN** a track with an existing spectral profile in the database
- **WHEN** the track file is re-scanned
- **THEN** the database SHALL store the newly computed profile

## Requirement 3: Spectral similarity scoring

The system SHALL include a spectral similarity component in transition scoring.

### Scenario 3.1: Similar colors score high

- **GIVEN** two tracks both with `dominant_color` `RED`
- **WHEN** a transition between them is scored
- **THEN** the `spectral` component score SHALL be greater than 0.7

### Scenario 3.2: Different colors score low

- **GIVEN** one track with `dominant_color` `RED` and another with `dominant_color` `GREEN`
- **WHEN** a transition between them is scored
- **THEN** the `spectral` component score SHALL be less than 0.5

### Scenario 3.3: Missing spectral data does not block scoring

- **GIVEN** one or both tracks lack a spectral profile
- **WHEN** a transition between them is scored
- **THEN** the spectral component SHALL be ignored or receive a neutral score
- **AND** the total transition score SHALL still be computable

## Requirement 4: User-facing spectral warnings

The system SHALL warn the DJ when adjacent recommended tracks have a large spectral jump.

### Scenario 4.1: Red-to-green transition warning

- **GIVEN** a recommended sequence containing a `RED` track followed by a `GREEN` track
- **WHEN** the recommendation is reviewed
- **THEN** the transition warning list SHALL contain a human-readable spectral mismatch warning

### Scenario 4.2: No false warning for similar colors

- **GIVEN** a recommended sequence containing two adjacent `GREEN` tracks
- **WHEN** the recommendation is reviewed
- **THEN** the transition SHALL NOT contain a spectral mismatch warning

## Requirement 5: Optional dependency

The system SHALL remain usable when the spectral analysis dependency is not installed.

### Scenario 5.1: Scan without spectral dependency

- **GIVEN** a system where the spectral analyzer dependency is unavailable
- **WHEN** a folder is scanned
- **THEN** metadata scan SHALL complete normally
- **AND** tracks SHALL have `spectral_profile` equal to `None`
- **AND** recommendation SHALL fall back to existing metadata-only scoring
