# Same Color & Energy Strategy Specification

## Purpose

Define the observable behavior of the `same_color_energy` playlist
recommendation strategy, which composes the existing hard anchor-color
prefilter with the existing hard ±1 energy-tolerance band as combined,
non-negotiable constraints. This capability is strictly additive: it MUST
NOT alter the behavior of the existing `same_color` or `same_energy`
strategies.

## Requirements

### Requirement: Strategy Registration and Enumeration

The system MUST register a `same_color_energy` strategy profile (label
"Same Color & Energy") in `_STRATEGIES`, extend the `StrategyName` Literal
to include it, and make it discoverable through the same enumeration
surfaces used by every other strategy.

#### Scenario: Strategy is selectable via the catalog

- GIVEN the strategy catalog is queried through `list_strategy_catalog()` or
  `available_strategies()`
- WHEN the catalog is enumerated
- THEN `same_color_energy` MUST appear with its display label
- AND selecting it MUST resolve to a valid `_STRATEGIES` entry with no
  bespoke UI wiring required

#### Scenario: Strategy name is statically typed

- GIVEN the `StrategyName` Literal type
- WHEN `pyright` checks `src` and `tests`
- THEN `"same_color_energy"` MUST be a valid `StrategyName` member with no
  new type errors

### Requirement: Hard Anchor-Color Prefilter Applies

When `same_color_energy` is the active strategy, the system MUST apply the
same hard anchor-color prefilter used by `same_color`, using identical
anchor resolution: locked/start-path track first, then majority
manual-prefix color, then the first profiled track's color.

#### Scenario: Candidates are filtered to the anchor's dominant color

- GIVEN an anchor track with a resolved dominant spectral color
- WHEN recommendations are generated under `same_color_energy`
- THEN every non-control candidate in the result MUST share the anchor's
  dominant color

#### Scenario: Anchor resolution mirrors same_color

- GIVEN no locked/start-path track exists but manual-prefix tracks
  establish a majority color
- WHEN the anchor color is resolved for `same_color_energy`
- THEN the resolved anchor color MUST be identical to what `same_color`
  would resolve for the same pool

### Requirement: Hard Energy Band Composes With the Color Filter

When `same_color_energy` is active, the system MUST apply
`energy_tolerance=1` via the existing anchor-relative
`_apply_energy_tolerance` mechanism, and this energy band MUST be combined
with, not substituted for, the color prefilter.

#### Scenario: Candidates satisfy both constraints simultaneously

- GIVEN an anchor track with a resolved color and energy value
- WHEN recommendations are generated under `same_color_energy`
- THEN every non-control candidate MUST share the anchor's color AND fall
  within ±1 of the anchor's energy value

### Requirement: Control Paths Are Preserved

Locked, start, end, and manual control tracks MUST pass through both the
color and energy filters exactly as they do for `same_color` and
`same_energy`, without being excluded or re-scored by the new combined
filtering.

#### Scenario: Locked and manual tracks remain in the result

- GIVEN a playlist with locked, start, end, and manual-prefix tracks
- WHEN recommendations are generated under `same_color_energy`
- THEN all control tracks MUST remain present in their existing positions,
  unaffected by the color or energy filters

### Requirement: Empty-Pool Fallback With Strategy-Aware Warning

When the combined color-and-energy filter leaves no viable candidates, the
system MUST fall back to the existing `same_color` fallback-to-unfiltered
scoring path and MUST emit a warning that attributes the fallback to
`same_color_energy`, without altering the existing warning text used by
`same_color` or `same_energy` alone.

#### Scenario: Fallback activates on an empty filtered pool

- GIVEN the combined color-and-energy filter excludes every non-control
  candidate
- WHEN recommendations are generated under `same_color_energy`
- THEN the system MUST fall back to unfiltered scoring
- AND a warning MUST be emitted naming `same_color_energy` (or its display
  label) as the strategy that triggered the fallback

#### Scenario: Existing strategy warnings are unaffected

- GIVEN `same_color` or `same_energy` triggers its own respective fallback
- WHEN the corresponding warning is emitted
- THEN its wording MUST remain byte-identical to current behavior

### Requirement: Existing Strategies Are Unaffected

Introducing `same_color_energy`, including any widened color-filter
dispatch, MUST NOT change the observable recommendation output, warnings,
or fallback behavior of `same_color` or `same_energy` for any existing
input. The `description` copy of those profiles is exempt from this
requirement and is governed by the Guarantee-Explicit Descriptions
requirement below.

#### Scenario: same_color output is unchanged

- GIVEN a fixed pool of tracks and anchor
- WHEN recommendations are generated under `same_color` before and after
  this change
- THEN the ordered candidate list and any warnings MUST be identical

#### Scenario: same_energy output is unchanged

- GIVEN a fixed pool of tracks and anchor
- WHEN recommendations are generated under `same_energy` before and after
  this change
- THEN the ordered candidate list and any warnings MUST be identical

### Requirement: Guarantee-Explicit Descriptions

The `description` of `same_color_energy`, `same_color`, and `same_energy`
MUST state the profile's actual guarantee explicitly: whether the
constraint is a hard filter or a weighted preference, and the concrete
bound where one exists (anchor color; ±1 energy band).

#### Scenario: new strategy description states both hard constraints

- GIVEN the registered `same_color_energy` profile
- WHEN its description is read (registry or UI description line)
- THEN it MUST state that the anchor color is a hard filter AND that
  energy is held to a hard ±1 band around the anchor

#### Scenario: existing descriptions state their guarantees

- GIVEN the registered `same_color` and `same_energy` profiles
- WHEN their descriptions are read
- THEN `same_color` MUST state that the anchor color is a hard filter and
  that energy is weighted but not limited, and `same_energy` MUST state the
  hard ±1 energy band and that color is weighted but not limited (spectral
  weight defaults to 0.10 in scoring, so color is never fully ignored)
