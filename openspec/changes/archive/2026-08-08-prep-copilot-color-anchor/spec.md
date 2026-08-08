# Specification: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

## Requirements

### R1. Colour strategies take the anchor-bound context route (G1)

**GIVEN** the Prep Copilot strategy combo resolves to `same_color` or `same_color_energy`
**WHEN** `PrepCopilotController.generate` gathers candidates
**THEN** it calls the colour-anchor candidate-context route and uses that context's
`records` and `color_anchor_path`, and it does **not** call the plain records route.

**GIVEN** any other strategy
**THEN** it calls the plain records route and forwards `color_anchor_path=None`,
byte-identically to the behaviour before this change.

### R2. Display labels normalise to internal strategy names (G2)

**GIVEN** a strategy combo populated without item data, so `currentData()` is empty and
the caller falls back to `currentText()` (for example `"Same Color"`)
**WHEN** `generate` decides which route the strategy takes
**THEN** the value is first resolved to its internal strategy name (`"same_color"`), so
the colour route is reached and the generation request carries the internal name.

**GIVEN** combo text that resolves to no registered strategy
**THEN** it is passed through untouched. It already fails downstream in
`recommend_playlist` with a reported error; raising at the combo would turn a deep,
reported failure into an unhandled one in the UI.

### R3. Every variant gates against the same bound anchor (G3)

**GIVEN** `build_prep_copilot_plan(tracks, intent, color_anchor_path=<path>)`
**THEN** all three variants (`safe`, `balanced`, `adventurous`) pass that same `<path>`
into `recommend_playlist`.

**GIVEN** a variant whose filter (for example `genre_focus`) removes `<path>` from its
track list
**THEN** that variant **fails closed** — an empty `ordered_tracks` plus an
anchor-is-missing warning — rather than rebinding a different anchor and gating the set
against a different colour.

**GIVEN** a variant that retains `<path>`
**THEN** its gate measures candidates against that track. For `same_color_energy` this
means both axes: a same-colour/wrong-energy candidate and a same-energy/wrong-colour
candidate are both excluded.

### R4. An unbound anchor is a fallback, not a failure (G3)

**GIVEN** the candidate-context seam returns `color_anchor_path=None` because it could
bind no anchor
**THEN** `None` flows unchanged through the whole generation chain so
`recommend_playlist` resolves an anchor itself, exactly as the main desktop
recommendation route does — the variants plan normally and do not fail closed.

A supplied-but-absent path and a never-bound `None` remain different facts.

### R5. The plan-builder seams spell the anchor in their type (G4)

**GIVEN** `application.prep_copilot.PlanBuilder` and
`desktop.prep_copilot.PlanGenerationBuilder`
**THEN** each is a `Protocol` whose `__call__` declares
`*, color_anchor_path: str | None = None`, so an injected builder that cannot accept the
bound anchor is a type error at the seam rather than a `TypeError` at generation time.

**GIVEN** `generate_prep_copilot_plan`
**THEN** it forwards `color_anchor_path` unconditionally — no branch — because `None` is
precisely what tells the builder to resolve an anchor itself.

### R6. The anchor stays a parameter, not intent state

**GIVEN** `DJSetIntent` and `PrepCopilotGenerationRequest`
**THEN** neither carries `color_anchor_path`. They model what the DJ asked for; the
anchor path is machine-bound identity produced by the candidate-planning seam, and
conflating them would make it look user-settable.

## Non-functional

- No existing Prep Copilot test may break except where a stub signature is forced to
  accept the new keyword.
- The change stays within the 400-line review budget.
