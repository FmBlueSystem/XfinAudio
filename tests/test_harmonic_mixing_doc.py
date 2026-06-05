"""Harmonic mixing guide publication-readiness tests."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC = PROJECT_ROOT / "HARMONIC_MIXING.md"


def read_doc() -> str:
    """Read the harmonic mixing guide."""
    return DOC.read_text(encoding="utf-8")


def test_harmonic_mixing_doc_matches_public_project_contract() -> None:
    text = read_doc()

    required_fragments = [
        "# XfinAudio — Harmonic Playlist Recommendation",
        "metadata-driven playlist assistant",
        "not a mixing engine",
        "GPL-3.0-only",
        "Mixed In Key",
        "Camelot",
        "does not mutate audio files",
        "does not mutate live Serato database V2 files",
        "safe export/backup/validation flow",
        "uv run xfinaudio",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text
    assert "manual desktop qa" in text.lower()


def test_harmonic_mixing_doc_does_not_advertise_unimplemented_cli_or_dsp_scope() -> None:
    text = read_doc()
    forbidden_fragments = [
        "xfinaudio scan <folder>",
        "xfinaudio recommend <folder>",
        "xfinaudio export <playlist-id>",
        "C++ audio engine",
        "Render de mezcla final",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in text
