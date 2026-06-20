# Spec: Quality readiness required fields

## Requirement: Readiness blocks when required track fields are absent

XfinAudio SHALL block DJ readiness when any recommended track lacks BPM, Camelot key, or energy metadata, even if the track status says complete.

### Scenario: Complete track has missing required field values

Given a recommended track has `metadata_status` set to complete,
And its BPM, Camelot key, or energy field is absent,
When the DJ readiness report is built,
Then the Required metadata check SHALL be blocked.
