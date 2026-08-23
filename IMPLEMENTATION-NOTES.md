# Implementation Notes

## add-loudness-module WU1a

- The minimum loudness duration is **3.0 seconds**. EBU R128 short-term loudness uses a
  3-second window, so this is the smallest duration at which LRA and true-peak values are
  retained by this module. Shorter material still preserves integrated LUFS and is typed
  `too_short` with LRA and dBTP unset.
- The golden fixture was captured from FFmpeg 8.0.1 against the synthetic 1 kHz WAV; the shipped bundle must use the same parser fixture or replace it when its pinned build is selected.
- `pyloudnorm` is a development-only conformance oracle. The runtime adapter remains the
  pinned FFmpeg command/parser boundary and never imports or invokes `pyloudnorm`.
- Process execution, preflight, timeout, cancellation, and orphan reaping remain WU1b.

## Autonomous blockers

### Native SDD runtime budget

The WU1 runtime objective is blocked at revision
`sha256:1e2e61ee5d3a9f086ab8b4ab5bc018f4a4bf2a0aa815c08caeb8aad288237aad`.
The native ledger counted 671 changed lines because the 354-line recovered binding contract
was committed after the WU1 objective was acquired, alongside the 327-line WU1a slice. Both
commits are independently below 400 lines, but native accounting correctly requires an
explicit maintainer reset before another apply or verification run. The autonomous mandate
does not authorize silently mutating that audit authority, so WU1b and WU2-WU4 were not
launched.

Required maintainer action:

```bash
gentle-ai sdd-attempt reset --cwd <repo> --change add-loudness-module \
  --expected-revision sha256:1e2e61ee5d3a9f086ab8b4ab5bc018f4a4bf2a0aa815c08caeb8aad288237aad \
  --request-id <unique-id> \
  --reason "Separate the recovered binding-contract import from the sub-400-line WU1 implementation slices" \
  --actor <maintainer>
```

### Audio-mutation governance

WU3 tasks 3.3-3.5 require writing COMMENT and `XFINAUDIO_LOUDNESS` tags, while the current
root `AGENTS.md` makes "No audio mutation" non-negotiable. WU4 task 4.6 proposes amending
that rule only after WU3, so the specified order cannot be executed without violating the
active repository instructions. Section 14 records product approval but does not itself
amend the active governance contract. This blocker must be resolved before WU3 write-back.
