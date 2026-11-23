# XfinAudio 2.41.0 Release Notes

Date: 2026-11-22

## Summary

2.41.0 is an **unreleased beta/source candidate** built on 2.40.0. It closes the
**53 edge-profile «fallidas»** that the 2.39.0 profile run left behind. Three
different things were hiding under the same «failed» label, and only one of them
was a real failure:

- **32 tracks are simply too short** for the two fixed 30-second edge windows.
  They are not edge failures at all: they are **not applicable**, they are no
  longer queued or retried for the edge stage, and the library reports them
  separately as **«32 no aplican (menos de 65 s)»**.
- **One track is a bootleg whose audio ends 71 seconds before the file does**.
  The outro window is exact digital silence, which has no spectrum to classify.
  It is now logged as **silence**, not as a decode failure.
- **20 files are genuinely damaged**, and they stay damaged: after the DJ's own
  decision they were **deliberately left as they are**, and they keep counting
  as failed and keep being retried.

The first two changes are code. The third is a decision, recorded here so nobody
later mistakes the 21 remaining failures for a regression.

## Tracks under 65 s are «no aplican», not failures

The edge profile classifies a fixed 30-second intro window and a fixed 30-second
outro window, so a track shorter than **65 s** (`_MIN_EDGE_TRACK_SECONDS`) cannot
carry one. The analysis already returned `None` for those tracks, but the status
counted every `None` as **failed**, so 32 perfectly healthy short tracks sat in
the same bucket as corrupted files.

What changed:

- `edge_profile_not_applicable(duration)` decides from the **duration the scan
  already stored**, with no extra decode.
- Those tracks are kept **out of the edge stage queue**, out of the retry, and
  out of `edgePendingCount`.
- A track now counts as **ready** with spectral + danceability + (an edge profile
  **or** not applicable), so the ready count is honest.
- The status payload gains **`edgeNotApplicableCount`**, an **additive** field.
  Nothing was renamed or removed, and a client that ignores unknown fields keeps
  working.
- The renderer validates **`edgeReady + notApplicable + pending = total`**, reads
  a **missing** field as **0** (so an older core still renders), and shows the
  Spanish line **«N no aplican (menos de 65 s)»** only when **N > 0** — the line
  is not printed on an empty library.
- **Already-stored profiles are not changed and not deleted.** A track that has
  an edge profile keeps it even if a later metadata edit shortens its duration.

## The Eurythmics bootleg: silence, not a decode failure

«Eurythmics - Sweet Dreams Ricci Bootleg.flac» was the one red herring of the 21:
`flac -t` passes, the file decodes, and it still had no edge profile.

The cause is the recording, not the code:

- The file is **365.87 s** long, but the audible audio ends at **294.20 s**. The
  remaining **71.68 s are exact digital silence**.
- The outro window is read at `duration - 30 s`, well inside that silent tail. It
  **decodes completely and carries zero energy**, so there is no spectrum to
  classify and the edge profile is legitimately `None`.
- Because that is a property of the recording and **not a bug**, the analysis was
  **not changed** and no stored value moved. What changed is the message: an
  empty window is now logged at **INFO** as **digital silence with no spectrum to
  classify**, and explicitly **not** as a decode failure. A damaged file now
  looks different in the log from a healthy file with a silent tail.

This track **still counts as failed and is still retried**. The alternative — keep
the intro profile when the tail cannot be read — was considered and **dropped**;
it is not part of this release.

## Damaged FLAC files are left as they are on purpose

The remaining **20** tracks of the 21 report decode errors under `flac -t`
(`END_OF_STREAM` / `ABORTED`): truncated or corrupt files where libsndfile fails
`psf_fseek` near the tail. The mid-track windows still decode; the tail does not.

After the DJ reviewed the list, the decision was **«omitir los archivos dañados y
continuar con los demás»**: **no new code reads or repairs them**. So:

- They keep **today's behaviour**: counted as **failed** and retried by
  **«Completar / reintentar perfiles»**.
- **Their source files are never modified** — no rewrite, no truncation fix, no
  silent re-encode. This release writes no audio.

## Live numbers after this change

Measured on the live library, read-only:

| Measure | Before | After |
|---|---|---|
| Ready tracks | 10337 | **10369** |
| Edge not applicable | counted as failed | **32** (14.8–63.9 s) |
| Edge pending | 53 | **21** (252.5–591.5 s) |

The 21 that remain are the 20 damaged files plus the Eurythmics bootleg, all of
them 252.5–591.5 s long. Nothing was deleted from the library and no stored
profile was rewritten.

## How it was verified

- Python: **full suite 3780 passed**; `ruff` and `pyright` clean.
- Renderer: **1104 pass / 0 fail**, build clean.
- Differential status payload against the previous code: the only difference is
  **`edgeNotApplicableCount: 0`**, so no existing client count moved.
- Release metadata: `tests/test_electron_candidate_metadata.py` and the public
  docs tests pass; `pyproject.toml`, `uv.lock`, `desktop-electron/package.json`,
  `desktop-electron/package-lock.json` and this file agree on **2.41.0**.

## Known limitations

- The 20 damaged files stay failed forever until they are re-ripped by hand.
  That is the accepted outcome, not an open bug.
- The Eurythmics bootleg also stays failed: its outro window is real silence, so
  there is nothing to classify. If that track ever matters, the fix is a better
  master, not a code change.
- «No aplican» is decided by the **stored** duration, so a track whose stored
  duration is wrong is classified from that wrong value until it is rescanned.
- The 2.41.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
