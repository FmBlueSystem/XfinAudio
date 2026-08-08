# Verify Report: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest -q` | PASS — 1505 passed |
| `uv run pyright src tests` | PASS — 0 errors |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS |
| CI (PR #340) | PASS — green on merge |

## Requirement verification

| Requirement | Evidence | Status |
|---|---|---|
| R1. Colour strategies take the context route | `tests/test_prep_copilot_controller.py::test_controller_routes_colour_strategies_through_the_bound_anchor_context` — the context route fired once, the plain route zero times, and the generation call carried the context's records plus `/music/anchor.flac`. The ordinary path is guarded by the pre-existing `::test_controller_delegates_plan_generation_to_injected_boundary`, which asserts `color_anchor_path is None` inside its stub | PASS |
| R2. Display labels normalise | `tests/test_prep_copilot_controller.py::test_controller_routes_colour_display_labels_through_the_bound_anchor_context` — `currentData()` empty, text `"Same Color"`; asserts the colour route fired AND that `request.strategy == "same_color"`, so the internal name reaches the plan chain too | PASS |
| R3. Every variant gates against the same anchor | `tests/test_prep_copilot.py::test_build_prep_copilot_plan_forwards_the_bound_anchor_to_every_variant` (all three forwards recorded); `::test_variant_that_filters_out_the_bound_colour_anchor_fails_closed` and `::test_same_color_energy_variant_that_filters_out_the_bound_anchor_fails_closed` (the genre-filtered variant returns `ordered_tracks == []` with an "anchor is missing" warning, while the anchor-keeping variant returns exactly the anchor) | PASS |
| R4. Unbound anchor falls back to internal resolution | `tests/test_prep_copilot_controller.py::test_controller_lets_an_unbound_colour_anchor_fall_back_to_internal_resolution` — runs the real generation chain (only the state transition is stubbed). Every variant comes back with tracks, and `/music/red.flac` is excluded, proving an anchor was resolved and the gate ran rather than failing closed | PASS |
| R5. Seams spell the anchor in their type | `PlanBuilder` and `PlanGenerationBuilder` are `Protocol`s declaring `*, color_anchor_path: str | None = None`; `uv run pyright src tests` clean with `generate_prep_copilot_plan` forwarding unconditionally | PASS |
| R6. Anchor is not intent state | `DJSetIntent` and `PrepCopilotGenerationRequest` are unchanged in the diff; the reason is recorded in the `generate_prep_copilot_plan` and `build_prep_copilot_plan` docstrings | PASS |

## Non-functional verification

- One existing test stub changed signature, forced by R5's keyword contract:
  `tests/test_application_prep_copilot.py`'s `fake_plan_builder` gained
  `*, color_anchor_path: str | None = None`. Its assertions are unchanged.
- Suite grew 1499 → 1505; no existing test regressed.
- Review budget: ~105 production + ~320 test changed lines, within the 400-line budget.

## Out of scope confirmation

- The bounded colour gate and the anchor-binding chain below Prep Copilot are unchanged;
  they were shipped and verified by `resolve-color-review-findings` (PR #339).
- `PrepCopilotController`'s reaches into `MainWindow` privates through `_state` were
  **not** addressed here, and this change added a second near-verbatim copy of the
  colour-route branch. Both were left as declared follow-ups and closed on
  `chore/color-anchor-followups`.
