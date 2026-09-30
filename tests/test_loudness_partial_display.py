"""Partial numeric measurements remain visible without presenting unstable LRA."""

from xfinaudio.audio.loudness import FfmpegLoudnessAdapter
from xfinaudio.desktop.screens.library_screen import LibraryScreen


def test_partial_keeps_lufs_truepeak_and_qualifies_lra(qapp):
    screen = LibraryScreen()
    p = FfmpegLoudnessAdapter("/not-executed", engine_fingerprint="synthetic").parse_stderr(
        "I: -20.0 LUFS\nLRA: 20.0 LU\nPeak: -17.0 dBFS\n", duration_seconds=3
    )
    screen.set_loudness_details(p, visible=True)
    text = screen.loudness_detail_label.text()
    assert "LUFS: -20.0" in text
    assert "True peak: -17.0 dBTP" in text
    assert "LRA: not stable (under 60 s)" in text
