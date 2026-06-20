# Spec: Vertical flow construction foundation

## Requirement: Vertical workflow ownership

XfinAudio SHALL build the next product increment as a vertical workflow that starts from library scan input, produces recommendation output, and preserves the result through playlist save/export boundaries.

### Scenario: UI triggers the vertical workflow

Given the user initiates the workflow from the desktop UI,
When scan/recommend/save/export actions are requested,
Then UI components SHALL delegate to controllers or coordinators instead of owning product decisions.

### Scenario: Application coordinates the workflow

Given the workflow spans scan, recommendation, saved playlists, and export,
When orchestration is needed across modules,
Then application-layer use cases SHALL coordinate domain services and ports without importing PySide6 or desktop modules.

## Requirement: Business policy stays outside UI

Recommendation, readiness, metadata, and export policy SHALL remain in domain/application modules rather than widgets, dialogs, or MainWindow.

### Scenario: Recommendation policy changes

Given recommendation rules need to evolve,
When a rule changes,
Then the change SHALL be testable through domain or application tests without requiring QWidget construction.

## Requirement: Infrastructure stays behind boundaries

Filesystem, repository, settings, audio-library, and export writer access SHALL stay behind explicit adapters or ports when the workflow needs substitution for tests.

### Scenario: Workflow test avoids real external systems

Given a vertical workflow unit test,
When persistence or export behavior is needed,
Then the test SHALL use fakes or in-memory ports rather than writing live Serato DB V2 files or mutating audio files.
