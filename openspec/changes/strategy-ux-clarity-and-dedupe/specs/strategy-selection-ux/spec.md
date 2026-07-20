# Strategy Selection UX Specification

## Purpose

Define the observable behavior of the strategy selector's explanation
label and the selector's item labels. The selector MUST always describe
the currently selected strategy, and MUST display human-readable names
while every downstream consumer keeps resolving the correct internal
strategy.

## Requirements

### Requirement: Immediate Description Refresh on Selection

The system MUST update `strategy_explanation_label` to the newly
selected strategy's description as soon as the strategy combo's
selection changes, without requiring a tab switch, window resize, or any
other unrelated render trigger.

#### Scenario: Switching strategies updates the label immediately

- GIVEN the strategy combo currently shows `harmonic_journey` and its
  description is visible in `strategy_explanation_label`
- WHEN the user selects `same_color_energy` in the combo
- THEN `strategy_explanation_label` MUST immediately show
  `same_color_energy`'s description
- AND no tab switch or other render trigger is required to see the update

#### Scenario: Live-observed regression is fixed

- GIVEN the build screen is rendered and the user changes the combo
  selection between any two strategies (e.g. `same_color` to
  `same_color_energy`) without switching tabs
- WHEN the selection change completes
- THEN the label MUST show the newly selected strategy's description,
  not the previously selected strategy's description

### Requirement: Selector Shows Display Names

The strategy combo MUST list every strategy's `display_name` (e.g.
"Same Color & Energy") as the visible item text, while preserving the
internal strategy name as the item's underlying data so selection
resolves to the correct internal strategy.

#### Scenario: Combo items show display names

- GIVEN the strategy combo is populated from `available_strategies()`
- WHEN the combo is rendered
- THEN every visible item text MUST be the strategy's `display_name`
- AND no internal strategy name (e.g. `same_color_energy`) MUST appear
  as visible item text

#### Scenario: Selecting a display name resolves the internal strategy

- GIVEN the user selects an item showing a display name
- WHEN recommendation generation reads the current selection
- THEN it MUST resolve to the correct internal strategy name via the
  existing strategy resolution seam

### Requirement: Downstream Consumers Keep Working

Recommendation generation, `prefilter_strategy_candidates`, the prep
copilot, saved playlists, and exports MUST continue to function
correctly after the combo switches to display names.

#### Scenario: Recommendation and prep copilot resolve the selection

- GIVEN a strategy selected via its display name
- WHEN a playlist recommendation or a prep copilot variant is generated
- THEN generation MUST succeed using the resolved internal strategy,
  with no behavior change versus selecting by internal name

### Requirement: Persisted and Exported Artifacts Record Internal Names

Saved playlists and export artifacts MUST keep recording the internal
strategy name (`recommendation.strategy.name`), never the display name,
regardless of how the strategy was selected in the UI.

#### Scenario: Export JSON keeps the internal name

- GIVEN a recommendation generated after selecting a strategy by its
  display name
- WHEN the recommendation is saved or exported
- THEN `recommendation.strategy.name` MUST be the internal strategy name
- AND it MUST NOT be the display name

### Requirement: Filtering Semantics and Descriptions Are Unaffected

Introducing display-name selection and the immediate label refresh
MUST NOT change `same_color`, `same_energy`, or `same_color_energy`
filtering/scoring behavior, nor any strategy's `description` text.

#### Scenario: Strategy descriptions are unchanged

- GIVEN the registered strategy profiles before and after this change
- WHEN each strategy's `description` is read
- THEN the description text MUST be byte-identical to before this change

#### Scenario: Filtering output is unchanged

- GIVEN a fixed pool of tracks and anchor
- WHEN recommendations are generated under `same_color`, `same_energy`,
  or `same_color_energy` before and after this change
- THEN the ordered candidate list and any warnings MUST be identical
