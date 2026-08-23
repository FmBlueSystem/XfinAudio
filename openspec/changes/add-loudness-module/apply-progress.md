# Apply Progress: add-loudness-module

## Status

WU1a complete under strict TDD. Further runtime-bearing work is blocked by the native SDD
attempt ledger pending an explicit maintainer reset; WU1b and WU2-WU4 remain pending.

## Completed Tasks

- [x] 1.1 Loudness port, versioned Pydantic profile, statuses, and post-write identity fields.
- [x] 1.2 Shell-free injectable FFmpeg command construction with explicit first-audio mapping.
- [x] 1.3 Strict pinned-build stderr parser with malformed-output rejection.
- [x] 1.6 Synthetic golden stderr fixtures and a development-only `pyloudnorm` LUFS-I epsilon oracle.
- [x] 1.7 Three-second duration floor: integrated LUFS retained; LRA/dBTP omitted with `too_short`.

## TDD Cycle Evidence

| Tasks | Test file | Layer | Safety net | RED | GREEN | Refactor |
|---|---|---|---|---|---|---|
| 1.1–1.3, 1.6–1.7 | `tests/audio/test_loudness.py` | Unit boundary | New module | `uv run pytest -q tests/audio/test_loudness.py` → collection error: `ModuleNotFoundError: xfinaudio.audio.loudness` | Same command → 5 passed | Replaced `str, Enum` with `StrEnum`; tests remained green. Added a short-output RED case (1 failed, 4 passed), then parsed LUFS before optional short-track values. |

## Work Unit Evidence

| Evidence | Result |
|---|---|
| Focused test | `uv run pytest -q tests/audio/test_loudness.py` — 5 passed in 1.63s |
| Static checks | Focused Ruff check/format passed; `uv run pyright src tests` reported 0 errors, 0 warnings. |
| Runtime harness | N/A — WU1a intentionally constructs/parses the command boundary only. Subprocess execution, timeout, cancellation, and preflight are WU1b. |
| Rollback boundary | Revert `src/xfinaudio/audio/loudness.py`, `tests/audio/test_loudness.py`, `tests/fixtures/loudness/`, `pyproject.toml`, `uv.lock`, and `IMPLEMENTATION-NOTES.md`. |

## Remaining Tasks

- [ ] 1.4 Capability preflight.
- [ ] 1.5 Timeout, cancellation, process-group handling, and orphan reaping.
- [ ] WU2–WU4, except the maintainer-authorized governance reorder recorded below.

## Scope Notes

- Duration floor is 3.0 seconds because EBU short-term windows are 3 seconds; see `IMPLEMENTATION-NOTES.md`.
- `pyloudnorm` is a bounded development dependency used only by the LUFS sanity test, not by runtime code.
- No user-library audio was touched. A committed synthetic WAV fixture was created and read only to capture its golden FFmpeg stderr fixture.
- Native attempt `WU1` settled as passed but exceeded its ledger budget because the recovered
  354-line contract import occurred after acquisition. Revision and reset requirements are
  recorded in `IMPLEMENTATION-NOTES.md`; no automatic reset was performed.
- The prior WU3 audio-mutation governance conflict is resolved by the maintainer-authorized
  task 4.6 reorder below. Future tag writes remain limited to the loudness module's explicit
  setting and are not part of this slice.

## Authorized Governance Reorder (4.6)

Maintainer approval moved task 4.6 ahead of WU3 so the active repository rules explicitly
authorize the only planned audio-file mutation before tag write-back is implemented.

- [x] 4.6 Amended `AGENTS.md`, `CONTRIBUTING.md`, and README English/Spanish sections:
  scanning remains read-only; the loudness module is the single documented exception and
  may write loudness tags only through its explicit setting.

| Task | RED | GREEN | Focused proof |
|---|---|---|---|
| 4.6 | `uv run pytest -q tests/test_public_open_source_docs.py` → 1 failed, 6 passed; missing governance sentence in `AGENTS.md` | Documentation amendment | Same command → 7 passed in 0.43s; focused Ruff/format and Pyright passed |

No tag-write code or other WU3 behavior was implemented in this slice.
