# Tasks: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

1. [x] **Proposal** — intent, the four gaps, scope boundaries, success criteria.
2. [x] **Specification** — GIVEN/WHEN/THEN for R1–R6.
3. [x] **Design** — alternatives for where the anchor travels (G3), what a variant does
   when it loses the anchor (G3), combo normalisation (G2), and seam typing (G4).
4. [x] **Route colour strategies through the bound context (G1 / R1)** —
   `PrepCopilotController.generate` calls
   `_desktop_color_anchor_candidate_context` for `COLOR_FILTER_STRATEGIES` and keeps
   every other strategy on the byte-identical records route.
5. [x] **Normalise combo display labels (G2 / R2)** — `_internal_strategy_name` wraps
   `resolve_strategy_name`; unresolvable text passes through untouched.
6. [x] **Thread the anchor into every variant (G3 / R3)** — keyword-only
   `color_anchor_path` on `generate_prep_copilot_plan`, `build_prep_copilot_plan` and
   `_build_variant`, forwarded into `recommend_playlist` for all three variants.
7. [x] **Pin fail-closed and the unbound fallback (R3 / R4)** — a variant that filters
   the anchor away returns empty with a warning; `None` still reaches the real chain so
   `recommend_playlist` resolves internally.
8. [x] **Type the plan-builder seams (G4 / R5)** — `PlanBuilder` and
   `PlanGenerationBuilder` become `Protocol`s carrying the keyword contract; the
   conditional forwarding collapses to an unconditional one.
9. [x] **Verify** — `uv run pytest -q`, `uv run pyright src tests`, `uv run ruff check .`,
   `uv run ruff format --check .`; version 1.7.4 → 1.7.5 with `uv.lock` synced.
10. [x] **Archive** — retroactive artifacts authored from the merged commit; see
    `archive-report.md` for what was and was not synced.
