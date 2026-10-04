# Fail-closed Electron IPC action dispatch and parity guard

## Intent

Make the Electron `xfin:action` boundary fail closed when an action is not handled, and freeze
the three-way action parity between `validateRequest`'s allowlist, the `main.ts` dispatch switch
and the `preload.ts` bridge, so drift is caught by a test instead of shipping.

This is the **narrow first work unit** of the Electron IPC contract change. It changes no user
behavior, adds no feature, and touches no Python, audio, Serato, or renderer code.

## Evidence that motivates the change (verified on this branch)

Counted from source on 2026-10-03, expanding the two spread tables:

| Surface | File | Count |
|---|---|---|
| Allowlist seen by `validateRequest` (48 literal + 6 `OFFLINE_FIELDS` + 6 `REVIEW_CONTROL_FIELDS`) | `desktop-electron/src/security.ts:35`, `offline-security.ts:2`, `review-security.ts:3` | 60 |
| `action()` dispatch cases | `desktop-electron/src/main.ts:109-181` | 60 |
| Dispatch actions exposed on `window.xfin` | `desktop-electron/src/preload.ts:3-42` | 60 |

The three sets are currently a bijection, so the parent's "60 match" premise is confirmed — but it
is *accidental and untested*: two thirds of the allowlist live in spread objects, and no test
asserts the relation in either direction. The `action()` switch (`main.ts:109`) has **no
`default:` arm**, so the moment the allowlist grows past the switch (for example by adding a key
to `OFFLINE_FIELDS` or `REVIEW_CONTROL_FIELDS`) the call resolves `undefined` silently instead of
rejecting. That is the latent fail-open this change closes.

## Scope

In scope (this work unit):
- One `default:` arm in the `action()` switch that throws `Unsupported action`.
- One focused structural/runtime guard test that asserts the fail-closed arm and the three-way
  action-set bijection, including preload key-to-method agreement.
- SDD artifacts under `openspec/changes/electron-ipc-contract/`.

Out of scope (explicitly not this work unit):
- Deriving the allowlist from a single dispatch table, or moving dispatch into an importable
  module. Recorded in `design.md` as the larger alternative.
- Adding, removing, or renaming any action, parameter, or user-facing control.
- Any Python backend method registry. Backend routing differs from the UI surface (see the
  no-assumption note in `design.md`), so parity is defined over the three TypeScript files only.
- Renderer, packaging, release, or publication work.

## Risks

- A source-text guard test can drift from real behavior if `main.ts` is restructured without
  updating the extraction. Mitigated by pairing it with a runtime probe against the compiled
  `security.js` and by the `default:` arm, which makes the runtime behavior self-evident.
- The guard freezes a 60-action surface. Adding a legitimate action now requires updating its
  allowlist and bridge; that is the intended cost and is cheaper than a silent runtime failure.

## Rollback

Remove the one `default:` line from `main.ts` and the new test file. No schema, data, dependency,
or runtime-state change exists, so rollback is a two-file revert with no migration.

## Success criteria

- `action()` rejects any action that passes `validateRequest` but has no dispatch case.
- A single focused test fails if the allowlist, the dispatch switch, or the preload bridge drift.
- The 60/60/60 bijection holds as a tested invariant.

## Review slices

Delivery is two local commits on `feat/electron-ipc-contract`; no push or PR. Slice A commits
these planning artifacts plus minimal `apply-progress`/`verify-report` placeholders (rollback:
docs-only revert; checks: `git show --stat` lists only docs). Slice B commits the one-line
`default` throw in `action()`, the guard test, and the expanded progress/report under RED then
GREEN (rollback: revert that single commit; checks: the verify commands in `tasks.md`). Each
slice stays under 400 added lines. The wider hardening in `design.md` needs its own chain.
