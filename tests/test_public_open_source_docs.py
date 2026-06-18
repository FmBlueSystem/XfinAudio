"""Public open-source readiness documentation tests."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"
CONTRIBUTING = PROJECT_ROOT / "CONTRIBUTING.md"
SECURITY = PROJECT_ROOT / "SECURITY.md"
NOTICE = PROJECT_ROOT / "NOTICE.md"
PUBLIC_DOCS = [README, CONTRIBUTING, SECURITY, NOTICE]


def read(path: Path) -> str:
    """Read a repository text file."""
    return path.read_text(encoding="utf-8")


def test_public_open_source_docs_exist() -> None:
    for path in PUBLIC_DOCS:
        assert path.exists(), f"Missing public repository document: {path.name}"


def test_readme_describes_project_scope_workflow_and_release_caveats() -> None:
    text = read(README)

    required_fragments = [
        "XfinAudio is a GPL-3.0-only desktop DJ playlist assistant",
        "Python 3.11",
        "uv sync --locked",
        "uv run pytest -q",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "does not mutate audio files",
        "does not mutate live Serato database V2 files",
        "explicit safe export/backup/validation flow",
        "Release gates",
        "docs/repository-publication-checklist.md",
        "[docs/harmonic-mixing.md](docs/harmonic-mixing.md)",
        "PySide6/Qt",
        "mutagen",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text
    assert "manual desktop qa" in text.lower()

    forbidden_fragments = [
        "signing completed",
        "notarization completed",
        "DMG completed",
        "legal clearance is complete",
    ]
    for fragment in forbidden_fragments:
        assert fragment.lower() not in text.lower()


def test_contributing_sets_dev_workflow_tdd_and_safety_boundaries() -> None:
    text = read(CONTRIBUTING)

    required_fragments = [
        "Python 3.11",
        "uv sync --locked",
        "uv run pytest -q",
        "uv run ruff check .",
        "uv run ruff format --check .",
        "test first",
        "No audio mutation",
        "No live Serato database V2 mutation",
        "app-owned database, settings, and export files",
        "Issues",
        "Pull requests",
        "docs/repository-publication-checklist.md",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_security_sets_disclosure_placeholder_scope_and_dependency_caveats() -> None:
    text = read(SECURITY)

    required_fragments = [
        "Pre-release",
        "Responsible disclosure",
        "Do not include private audio libraries",
        "No live Serato writes by design",
        "does not mutate audio files",
        "PySide6/Qt",
        "mutagen",
        "third-party dependencies",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_notice_records_license_dependency_inventory_and_legal_limits() -> None:
    text = read(NOTICE)

    required_fragments = [
        "GPL-3.0-only",
        "third-party dependency inventory",
        "evidence only",
        "PySide6/Qt",
        "mutagen",
        "binary/app bundle redistribution",
        "legal review",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text
