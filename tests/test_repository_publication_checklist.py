"""Repository publication checklist documentation tests."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = PROJECT_ROOT / "docs" / "repository-publication-checklist.md"


def read(path: Path) -> str:
    """Read a repository text file."""
    return path.read_text(encoding="utf-8")


def test_repository_publication_checklist_exists() -> None:
    assert CHECKLIST.exists()


def test_repository_publication_checklist_preserves_source_release_boundaries() -> None:
    text = read(CHECKLIST)

    required_fragments = [
        "GPL-3.0-only",
        "source publication",
        "do not publish binary artifacts",
        "do not claim signing, notarization, or DMG completion",
        "do not claim legal clearance",
        "uv run python scripts/release_gate_check.py --run --report-json",
        ".github/workflows/non-audio-release-gates.yml",
        "GitHub Actions",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "NOTICE.md",
        "manual desktop QA",
        "clean macOS account validation",
        "PySide6/Qt",
        "mutagen",
        "no live Serato database V2 mutation",
        "No private audio files or library databases",
    ]
    normalized = text.lower()
    for fragment in required_fragments:
        assert fragment.lower() in normalized

    forbidden_fragments = [
        "binary release is ready",
        "legal clearance is complete",
        "notarization completed",
        "DMG completed",
    ]
    for fragment in forbidden_fragments:
        assert fragment.lower() not in normalized
