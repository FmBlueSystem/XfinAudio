# Archive Report: Fix Derived-Profile Cache Identity

- **Change:** `fix-derived-profile-cache-identity`
- **Archive date:** `2026-08-22`
- **Artifact store:** OpenSpec
- **Final status:** Complete; final verification verdict was PASS WITH WARNINGS.

## Final-State Evidence

The canonical independent verification report was validator-admitted and native settlement completed. The final evidence is:

- 3/3 requirements compliant.
- 6/6 scenarios compliant.
- Focused tests: 75 passed.
- Full suite: 1,691 passed.
- Pyright: 0 errors and 0 warnings.
- Coverage: 91.14%.
- Ruff check and format checks passed.
- Release gate passed.

The only warning is pre-existing: `uv.lock` records editable project version `1.8.0` while `pyproject.toml` records `1.8.2`. `uv.lock` was restored and remains outside this change's scope.

No loudness code, schema, audio, serialization, or source scope beyond `TrackRepository` and its tests was changed by this SDD change. The user-owned `docs/reviews/loudness-module-review.md` was not touched.

## Completion and Review Gates

- Structured native status reported tasks `10/10`, apply `all_done`, verify `all_done`, archive `ready`, and no blocked reasons.
- The structured status had no `reviewGate` key. Archive therefore proceeded under ordinary repository policy; no review receipt was required or expected.
- The persisted `tasks.md` contains 10 checked implementation tasks and no unchecked tasks.

## Spec Synchronization

The full capability spec was copied mechanically from:

`openspec/changes/fix-derived-profile-cache-identity/specs/derived-profile-cache-identity/spec.md`

to:

`openspec/specs/derived-profile-cache-identity/spec.md`

The final archived delta and main capability spec are byte-identical.

### Verbatim spec-copy diff output

Command: `diff -r openspec/changes/fix-derived-profile-cache-identity/specs/derived-profile-cache-identity/spec.md <temporary-copy>`

```text
```

Exit status: `0`.

### Verbatim final spec-identity diff output

Command: `diff -r openspec/changes/archive/2026-08-22-fix-derived-profile-cache-identity/specs/derived-profile-cache-identity/spec.md openspec/specs/derived-profile-cache-identity/spec.md`

```text
```

Exit status: `0`.

## Archive Move

The complete change folder was moved mechanically to:

`openspec/changes/archive/2026-08-22-fix-derived-profile-cache-identity/`

The active source folder no longer exists. The archived folder contains the proposal, delta spec, design, tasks, apply progress, verify report, and this additive archive report.

### Verbatim archive readback diff output

The pre-move recursive snapshot was compared with the archived folder before this archive report was added. The archive report is additive and therefore intentionally excluded from that comparison.

Command: `diff -r <pre-move-snapshot>/source openspec/changes/archive/2026-08-22-fix-derived-profile-cache-identity`

```text
```

Exit status: `0`.

## Scope Notes

The archived change preserves the repository's existing working-tree modifications to `src/xfinaudio/library/track_repository.py` and `tests/test_track_repository.py`; no commit was created. No other source or user-owned review artifact was modified by archive operations.
