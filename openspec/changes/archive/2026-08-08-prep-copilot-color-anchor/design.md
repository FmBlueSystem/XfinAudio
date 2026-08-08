# Design: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

## Decision question

Prep Copilot builds three variants from one candidate pool, each with its own filters.
The bound colour anchor has to survive that fan-out. Where does it travel, and what
should a variant do when its own filter removes the anchor?

## Alternatives considered

### G3 — How the anchor reaches each variant

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. An explicit `color_anchor_path` keyword threaded through `generate_prep_copilot_plan` → `build_prep_copilot_plan` → `_build_variant` → `recommend_playlist` | The anchor is visible at every hop, so no layer can quietly drop it. Matches the keyword `recommend_playlist` already accepts from the main desktop route. | Four signatures gain a keyword. | **Selected.** |
| B. A field on `DJSetIntent` | Rides an existing object all the way down; zero new parameters. | `DJSetIntent` models what the human asked for — name, strategy, target count, genre focus. The anchor is machine-bound identity from the candidate-planning seam. Putting it there makes it read as user-settable and invites a future UI to set it. | Rejected. |
| C. A field on `PrepCopilotGenerationRequest` | Same. | Same reason: the request carries what the DJ typed into the UI. | Rejected. |

### G3 — What a variant does when its filter removes the anchor

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Fail closed — empty recommendation plus an anchor-is-missing warning | Honest. The anchor identity was bound for this pool; a variant that loses it has no basis to gate colour at all. | One of the three variants can come back empty. | **Selected** — this is the whole point of binding. It is also already `recommend_playlist`'s behaviour for a supplied-but-absent path, so Prep Copilot inherits it rather than inventing a rule. |
| B. Re-resolve within the variant's own track list | Never empty. | Restores exactly the bug: a genre-focused variant would gate the DJ's set against a different colour than the pool was planned for. | Rejected. |
| C. Re-add the anchor to the variant's list | Never empty, anchor preserved. | Silently overrides the DJ's own genre filter. | Rejected. |

### G2 — Normalising the combo value

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. `resolve_strategy_name`, passing genuinely unknown text through untouched | Fixes the silent miss. Unknown text keeps failing where it already failed — deep in `recommend_playlist`, reported. | The pass-through looks permissive until you read why. | **Selected**; the reason lives in `_internal_strategy_name`'s docstring. |
| B. Raise on unresolvable text | Fails fast. | Turns a deep, *reported* error into an unhandled exception in the UI — worse for the DJ, not better. | Rejected. |
| C. Test both the data value and the display label against the colour set | No resolver needed. | Two membership tests to keep in step with the strategy registry, which is the drift the shared `COLOR_FILTER_STRATEGIES` constant exists to prevent. | Rejected. |

### G4 — Typing the plan-builder seams

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. `Protocol` with the keyword spelled in `__call__` | The bound anchor becomes part of the contract: a builder that cannot accept it is a type error at the seam. | More verbose than an alias. | **Selected.** |
| B. Keep `Callable[..., Any]` / `Callable[[list[TrackRecord], DJSetIntent], PrepCopilotPlan]` | Shorter. | `Callable[..., Any]` types nothing, and the positional form cannot express a keyword-only parameter at all — the failure would surface as a runtime `TypeError` during generation. | Rejected. |

### Process — SDD artifacts for this change

Same decision, and the same reasoning, as its predecessor: authored **retroactively**
from the merged commit, because `AGENTS.md` requires durable `openspec/` artifacts for
every non-trivial change and PR #340 shipped without them. See `archive-report.md` →
"Artifact provenance".

## Architecture impact

- `desktop/prep_copilot.py` — `_internal_strategy_name` helper; `generate` branches on
  `COLOR_FILTER_STRATEGIES`; `PlanGenerationBuilder` becomes a `Protocol`.
- `application/prep_copilot.py` — `PlanBuilder` becomes a `Protocol`;
  `generate_prep_copilot_plan` gains keyword-only `color_anchor_path` and forwards it
  unconditionally.
- `recommendation/prep_copilot.py` — `build_prep_copilot_plan` and `_build_variant` gain
  keyword-only `color_anchor_path`, passed into `recommend_playlist` per variant.
- No change to the gate itself, to `DJSetIntent`, or to
  `PrepCopilotGenerationRequest`.

## Affected files

- `src/xfinaudio/application/prep_copilot.py`
- `src/xfinaudio/desktop/prep_copilot.py`
- `src/xfinaudio/recommendation/prep_copilot.py`
- `tests/test_application_prep_copilot.py`
- `tests/test_prep_copilot.py`
- `tests/test_prep_copilot_controller.py`

## Safety

- No audio mutation, no DSP scope change, no live Serato Database V2 writes.
- Pure in-memory planning and filtering.
