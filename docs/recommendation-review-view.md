# Recommendation Review View

Date: 2026-06-04

## Scope

The desktop recommendation review view lets DJs inspect recommendation quality before any export workflow. It renders existing recommendation, explanation, and quality report data only.

## What the view shows

After a recommendation is generated, `MainWindow` displays:

- a review summary with track count, transition count, average transition score, and warning count;
- the ordered recommendation table already used for recommended tracks;
- a transition review table with order, from/to track labels, key score, BPM score, energy score, tag score, final score, and human-readable warnings;
- export guidance that tells the user to inspect the review table before exporting to a safe folder.

Initial and no-scan states keep the review summary/table empty with the message: `No recommendation is ready for review.`

## Data sources

The view uses existing data produced by `PlaylistWorkflowService.recommend()`:

- `PlaylistRecommendation` for ordered tracks;
- `PlaylistExplanation.transitions` for component and final transition scores;
- `RecommendationQualityReport` for summary counts.

Raw explanation warnings are preserved. UI cells render warnings through the existing human-readable recommendation warning formatter.

## Out of scope

This view does not add or change:

- recommendation algorithms;
- desktop export workflow controls;
- audio mutation, DSP, rendering, or analysis;
- live Serato writes.

## Automated verification

Focused tests cover initial state, summary formatting, review summary rendering after recommendation, transition review table headers/cells, human-readable warning rendering, export guidance, and clearing review state when no scanned records are available.
