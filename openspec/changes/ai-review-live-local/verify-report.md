# Focused verification — 2026-09-30

143 focused tests passed (3.45s) on the worker branch with temporary HOME,
QT_QPA_PLATFORM=offscreen and AI disabled by default. Provider tests use injected
transports with synthetic keys; no real provider or audio transmission was used.

## Requirement evidence

- R1: narrator controller tests reproduce then reject stale success/failure,
  already-queued delivery, cancellation/retry and old-thread cleanup.
- R2: real Qt mouse clicks cover loading, Cancel, Configure AI, disabled-service
  error recovery and successful injected retry. Invalid/empty/oversized responses
  reject with retryable guidance. Provider HTML renders as literal PlainText.
- R3: local Review facts include computed scores, weakest transition explanations,
  readiness issues and normalized existing Prep alternatives; unrelated sets or
  conflicting current locks/exclusions hide comparison candidates.
- R4: transport assertions cover computed facts, unknown missing metadata and
  redaction of paths embedded in warnings/readiness, plus anonymous unknown tracks.
- R5: pure Live gate requires fresh engine readiness and current constraints;
  absent/invalid/missing metadata/stale supplied readiness and raw-library bypass
  fail closed. Session signature includes identities, content, controls and score
  configuration; periodic identical sync preserves current track/history.
- R6: genuine engine scores rank alternatives. Every proposed complete remaining
  order is revalidated. Played/outside/excluded paths cannot load; controls and
  arc order remain intact. Real clicks exercise load/history and invalidation.
- R7: engine-selected replacement preview compares original/proposed score and
  readiness without changing the recommendation, respecting protected tracks,
  exclusions, generation policy, current scoring and loudness settings.

## Commands and checks

Focused pytest files: test_ai_narrator_controller, test_ai_set_narrator,
test_review_assistance, test_review_screen, test_review_view_model,
test_live_assistance, test_live_assistant_screen, test_main_window_live,
test_review_ai_interactions (all .py).

Focused pyright: 0 errors/warnings with --pythonpath pointing to the shared venv.
Focused Ruff check: passed. Ruff format --check: 13 files already formatted.
All conventional-commit review slices remain below 400 changed lines.
An offscreen 1200x800 Review capture was visually checked: actions fit, facts and
replacement details are collapsed by default, and table space is preserved.

The initial window smoke run without temporary HOME failed on the sandbox's
read-only real home; rerunning with temporary HOME passed. Initial focused
pyright without explicit interpreter could not resolve shared-venv packages;
the explicit --pythonpath run passed. Neither required product changes.
The new widget/controller tests explicitly dispose Qt connections/objects to
avoid a QApplication teardown crash; their focused and combined reruns pass.

## Integration boundary

Coordinator owns shell/navigation/state/window signal wiring and the full exact-
tree release gate. This worker did not run the full suite/coverage/release gate,
push, merge, deploy, change dependencies or touch audio/Serato files. Final gate
result remains pending in the integration change, not represented as passed here.
