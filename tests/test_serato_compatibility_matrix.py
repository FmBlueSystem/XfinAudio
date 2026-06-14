"""Tests for the Serato compatibility matrix documentation."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = PROJECT_ROOT / "docs" / "serato-compatibility-matrix.md"
FIXTURE_DOC_PATH = PROJECT_ROOT / "docs" / "serato-fixture-compatibility.md"


def test_compatibility_matrix_document_exists() -> None:
    """The compatibility matrix doc must exist."""
    assert MATRIX_PATH.exists()


def test_compatibility_matrix_contains_table() -> None:
    """The matrix must include a Markdown table with version and validation columns."""
    content = MATRIX_PATH.read_text(encoding="utf-8")
    assert "| Serato version / workflow |" in content
    assert "| Fixture byte validation |" in content
    assert "| Live library import |" in content


def test_compatibility_matrix_acknowledges_live_limitations() -> None:
    """The matrix must clearly state that live import and live writes are not verified."""
    content = MATRIX_PATH.read_text(encoding="utf-8")
    assert "Not verified" in content
    assert "live" in content.lower()
    assert "dry-run by default" in content.lower()


def test_fixture_compatibility_doc_links_to_matrix() -> None:
    """The fixture compatibility doc must reference the matrix."""
    content = FIXTURE_DOC_PATH.read_text(encoding="utf-8")
    assert "serato-compatibility-matrix.md" in content
