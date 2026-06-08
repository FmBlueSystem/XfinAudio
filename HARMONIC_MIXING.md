# XfinAudio — Harmonic Playlist Recommendation

XfinAudio is a GPL-3.0-only metadata-driven playlist assistant. It recommends playlist order from existing metadata; it is not a mixing engine.

The project assumes DJs may already use tools such as Mixed In Key for key, BPM, energy, and tag metadata. XfinAudio reads metadata, normalizes it, scores transitions, explains recommendations, and exports playlist artifacts. It does not detect keys or BPM from audio waveforms.

> **Trademark notice:** Mixed In Key, Camelot, Camelot Wheel, and Camelot System are trademarks of Mixed In Key LLC. Serato and Serato DJ Pro are trademarks of Serato Limited. These marks are referenced for descriptive and interoperability purposes only.

## Safety and scope

XfinAudio is intentionally non-destructive:

- It does not mutate audio files.
- It does not render, mix, crossfade, time-stretch, pitch-shift, or analyze waveforms.
- It does not perform key detection, BPM detection, beat tracking, cue detection, phrase detection, stem separation, or final mix rendering.
- It does not mutate live Serato database V2 files.
- Serato crate writes stay behind the documented explicit safe export/backup/validation flow.
- Manual desktop QA is still required before release claims involving real DJ workflows.

No legal advice or legal clearance is implied by this guide. Binary/app bundle redistribution still needs legal review for GPLv3 and third-party dependencies.

## Metadata inputs

Before expanding scoring policy, inspect real metadata examples because Mixed In Key and DJ libraries can write tags differently across formats.

| Data | Common sources |
|------|----------------|
| BPM | Standard BPM fields or format-specific tags |
| Key/Camelot | Initial Key, TKEY, comments, grouping, or tool-specific fields |
| Energy | Grouping, comments, custom fields, or combined text fields |
| Genre/tags | Genre, grouping, comments, or DJ library annotations |

The metadata contract and current inspection findings live in `docs/help-3-mixed-in-key-metadata-contract.md`.

## Harmonic scoring basis

The recommendation engine uses Camelot-compatible scoring and combines it with BPM, energy, and tag/vibe signals when available.

| Transition | Example | Typical score intent |
|------------|---------|----------------------|
| Same key | `8A -> 8A` | Highest compatibility |
| Camelot neighbor | `8A -> 7A` / `8A -> 9A` | Smooth compatible movement |
| Relative major/minor | `8A <-> 8B` | Compatible mood shift |
| Controlled energy boost | `8A -> 10A` | Useful but less neutral |
| Incompatible jump | `8A -> 3B` | Low compatibility |

Default transition weights are documented in code and settings tests:

```json
{
  "weights": {
    "harmonic": 0.40,
    "bpm": 0.25,
    "energy": 0.25,
    "tags": 0.10
  }
}
```

If optional tag/vibe metadata is missing or incomplete, recommendations should surface warnings instead of pretending the metadata is complete.

## Playlist strategies

Current strategy names are metadata policy choices, not audio processing modes.

| Strategy | Goal |
|----------|------|
| `harmonic` | Prefer smooth harmonic movement |
| `energy-build` | Increase energy progressively |
| `warmup` | Favor lower/mid energy paths |
| `peak-time` | Favor high-energy compatible paths |
| `same-energy` | Maintain a stable energy band |
| `same-vibe` | Use tags/genre when reliable |

## Sequence optimization

Pairwise transition scores are not enough; the system must order tracks.

```text
<=20 tracks: exact Held-Karp path search
>20 tracks: greedy plus local improvement
```

This keeps small playlists exact while avoiding impractical exhaustive search for larger libraries.

## Desktop usage

For the current desktop app, use the source/development launcher:

```bash
uv run xfinaudio
```

The desktop flow is:

```text
Choose existing audio folder
  -> scan metadata
  -> review complete/incomplete metadata
  -> choose strategy and DJ controls
  -> generate recommendation
  -> inspect transition explanations and warnings
  -> export artifacts only to a safe location
```

Do not infer release readiness from this guide alone. Use `docs/release-readiness-smoke.md` and `docs/repository-publication-checklist.md` for release/source-publication gates.

## DJ assistant behavior

Every transition should be explainable with:

- key score;
- BPM score;
- energy score;
- tag/vibe score;
- final score;
- warnings for missing or questionable metadata.

The DJ should remain in control through options such as start/end tracks, locked tracks, excluded tracks, manual ordering, regeneration, and scoring weights.

## Future ideas, not current scope

These are explicitly not part of the current product scope unless separately designed, tested, and approved:

- Tonnetz or TPS tonal distance;
- downbeat or phrase detection;
- vocal clash detection;
- timbre similarity;
- embeddings;
- mashability scoring;
- beat-synchronous transitions;
- generated transitions;
- crossfade or mix rendering.
