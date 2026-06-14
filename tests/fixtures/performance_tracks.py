"""Deterministic track fixtures for performance baseline tests."""

from __future__ import annotations

from xfinaudio.library.models import TrackRecord

# Common Camelot keys and BPM values used to create varied but deterministic tracks.
_CAMELOT_KEYS = ["8A", "8B", "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"]
_BPMS = [120.0, 122.0, 124.0, 125.0, 126.0, 128.0, 130.0, 132.0]


def make_complete_tracks(count: int) -> list[TrackRecord]:
    """Generate ``count`` deterministic complete TrackRecords for benchmarking."""
    tracks: list[TrackRecord] = []
    for i in range(count):
        key = _CAMELOT_KEYS[i % len(_CAMELOT_KEYS)]
        bpm = _BPMS[i % len(_BPMS)]
        energy = (i % 10) + 1
        tracks.append(
            TrackRecord(
                path=f"/music/perf/track_{i:05d}.mp3",
                title=f"Perf Track {i}",
                artist=f"Artist {i % 50}",
                bpm=bpm,
                camelot_key=key,
                energy_level=energy,
                duration=240.0,
                genre="House",
                tags=["house", "electronic"],
                metadata_status="complete",
                source_fields={"TBPM": str(bpm), "TKEY": key},
            )
        )
    return tracks
