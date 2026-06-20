from __future__ import annotations

from pathlib import Path

from xfinaudio.library.scan_planning import plan_supported_audio_paths


def test_plan_supported_audio_paths_filters_sorts_and_deduplicates() -> None:
    root = Path("/library")
    alpha = root / "Alpha.FLAC"
    beta = root / "nested" / "beta.mp3"

    planned = plan_supported_audio_paths(
        root,
        list_paths=lambda folder: [
            root / "notes.txt",
            beta,
            alpha,
            beta,
            root / "cover.jpg",
        ],
    )

    assert planned == [alpha, beta]
