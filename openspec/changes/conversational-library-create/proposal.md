# Conversational Library and Create

Approved scope: natural-language Library filters and confirmation-first Create.
All track selection/order stays in the existing deterministic local engine.
Audio, DSP, settings persistence, review/editor, live Serato and dependencies are out of scope.
Risk: model suggestions or stale UI constraints silently changing a plan. Mitigation:
validate locally, preview visibly, require confirmation, reject stale completions.
Rollback: revert the ordered feature commits; no database migration.
Success: offline Library filtering is editable, Create never plans before confirmation,
constraints survive, retry/cancel work, and no extra inventory is shared by default.

## Explicit chained review slices (each <=400 changed lines)
1. SDD contract and test plan
2. Validated offline Library query model/parser and focused tests
3. Library QWidget editable filter panel and integration tests
4. Create confirmation QWidget and tests
5. Confirmation-first controller and lifecycle tests
6. Intent privacy/validation and tests
7. Constraint/stale-result hardening, regression verification and SDD evidence
Split any slice further before its diff exceeds the budget. Conventional commits,
no pushes, merge, deployment, provider calls, real credentials or dependency changes.
