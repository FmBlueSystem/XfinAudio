# Specification: quality-manual-overlap

## Requirement: Manual overlap uses distinct manual reference paths

### Scenario: Duplicate manual paths are ignored for overlap denominator
Given a generated recommendation containing `/music/a.flac` and `/music/b.flac`
And a manual reference list containing `/music/a.flac`, `/music/a.flac`, and `/music/missing.flac`
When a quality report is built
Then the manual overlap ratio is `0.5`
And the duplicate `/music/a.flac` does not reduce the denominator.

### Scenario: Empty manual paths remain zero overlap
Given any generated recommendation
And an empty manual reference list
When a quality report is built
Then the manual overlap ratio is `0.0`.
