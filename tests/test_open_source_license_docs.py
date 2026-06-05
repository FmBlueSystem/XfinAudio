"""Open-source GPLv3 project posture tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LICENSE_FILE = PROJECT_ROOT / "LICENSE"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
OPEN_SOURCE_DOC = PROJECT_ROOT / "docs" / "open-source-license.md"
KEY_DOCS = [
    PROJECT_ROOT / "docs" / "third-party-license-inventory.md",
    PROJECT_ROOT / "docs" / "packaging-strategy.md",
    PROJECT_ROOT / "docs" / "release-candidate-evidence.md",
    PROJECT_ROOT / "docs" / "open-source-release-backlog.md",
    PROJECT_ROOT / "docs" / "release-notes-template.md",
    PROJECT_ROOT / "docs" / "release-readiness-smoke.md",
]
SOURCE_AND_PLAN_POSTURE_FILES = [
    PROJECT_ROOT / "src" / "xfinaudio" / "config" / "settings.py",
    PROJECT_ROOT / "tests" / "test_playlist_strategies.py",
    PROJECT_ROOT / "docs" / "plans" / "2026-06-04-packaging-strategy-release-notes.md",
    PROJECT_ROOT / "docs" / "plans" / "2026-06-04-pyinstaller-packaging-spike.md",
]

LEGACY_POSTURE_DOCS = [
    PROJECT_ROOT / "docs" / "IMPLEMENTATION_HANDOFF.md",
    PROJECT_ROOT / "docs" / "xfinaudio-stack-and-scope-decision.md",
    PROJECT_ROOT / "docs" / "macos-signing-notarization-dmg-plan.md",
    PROJECT_ROOT / "docs" / "pyinstaller-packaging-spike.md",
    PROJECT_ROOT / "docs" / "help-8-release-hardening.md",
    PROJECT_ROOT / "docs" / "plans" / "2026-06-03-help-8-release-hardening.md",
    PROJECT_ROOT / "docs" / "plans" / "2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md",
]


def read(path: Path) -> str:
    """Read a repository text file."""
    return path.read_text(encoding="utf-8")


def test_license_file_exists_with_gplv3_markers() -> None:
    license_text = read(LICENSE_FILE)

    assert "GNU GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3, 29 June 2007" in license_text
    assert "Everyone is permitted to copy and distribute verbatim copies" in license_text


def test_pyproject_declares_gplv3_only_metadata() -> None:
    pyproject = tomllib.loads(read(PYPROJECT))

    assert pyproject["project"]["license"] == "GPL-3.0-only"
    assert "License :: OSI Approved :: GNU General Public License v3 (GPLv3)" in pyproject["project"]["classifiers"]


def test_pyproject_declares_public_source_metadata() -> None:
    pyproject = tomllib.loads(read(PYPROJECT))
    project = pyproject["project"]
    classifiers = project["classifiers"]

    assert project["readme"] == "README.md"
    assert "Development Status :: 3 - Alpha" in classifiers
    assert "Environment :: MacOS X" in classifiers
    assert "Intended Audience :: End Users/Desktop" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Topic :: Multimedia :: Sound/Audio" in classifiers


def test_open_source_license_doc_states_model_and_legal_caveats() -> None:
    doc = read(OPEN_SOURCE_DOC)

    assert "XfinAudio source is distributed as a full open-source project under GPL-3.0-only" in doc
    assert "Redistribution must comply with GPLv3" in doc
    assert "No legal advice or legal clearance is implied" in doc
    assert "PySide6/Qt" in doc
    assert "mutagen" in doc
    assert "third-party dependencies" in doc
    assert "binary" in doc.lower()
    assert "legal review" in doc.lower()


def test_stale_commercial_filenames_are_not_used() -> None:
    assert not (PROJECT_ROOT / "docs" / "commercial-backlog.md").exists()
    assert (PROJECT_ROOT / "docs" / "open-source-release-backlog.md").exists()
    assert not (PROJECT_ROOT / "docs" / "help-8-commercial-hardening.md").exists()
    assert (PROJECT_ROOT / "docs" / "help-8-release-hardening.md").exists()
    assert not (PROJECT_ROOT / "docs" / "plans" / "2026-06-03-help-8-commercial-hardening.md").exists()
    assert (PROJECT_ROOT / "docs" / "plans" / "2026-06-03-help-8-release-hardening.md").exists()


def test_key_docs_keep_binary_dependency_review_pending_without_clearance_claims() -> None:
    combined = "\n".join(read(path) for path in KEY_DOCS)

    assert "GPL-3.0-only" in combined
    assert "PySide6/Qt" in combined
    assert "mutagen" in combined
    assert "binary" in combined.lower()
    assert "legal review" in combined.lower()
    assert "No legal clearance" in combined
    assert "legal clearance is implied" in combined


def test_key_docs_do_not_keep_closed_or_commercial_clearance_posture() -> None:
    combined = "\n".join(read(path) for path in KEY_DOCS).lower()

    forbidden_phrases = [
        "closed-source",
        "closed source",
        "commercial release claim",
        "commercial release claims",
        "commercial distribution approval",
        "commercial clearance",
        "commercially safer desktop product",
        "commercial desktop",
    ]

    for phrase in forbidden_phrases:
        assert phrase not in combined


def test_source_and_plan_wording_do_not_keep_stale_commercial_posture() -> None:
    combined = "\n".join(read(path) for path in SOURCE_AND_PLAN_POSTURE_FILES).lower()

    forbidden_phrases = [
        "commercial-safe defaults",
        "custom commercial strategy extension",
        "commercial distribution",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in combined


def test_legacy_posture_docs_are_updated_for_full_gplv3_open_source_release() -> None:
    combined = "\n".join(read(path) for path in LEGACY_POSTURE_DOCS)
    normalized = combined.lower()

    forbidden_phrases = [
        "commercial desktop dj playlist assistant",
        "commercial desktop tool",
        "commercial stack",
        "commercial safety policy",
        "commercial persistence",
        "commercial macos distribution path",
        "commercial release claim",
        "commercial release claims",
        "commercial signing",
    ]

    for phrase in forbidden_phrases:
        assert phrase not in normalized

    assert "GPL-3.0-only" in combined
    assert "full open-source" in normalized
    assert "PySide6/Qt" in combined
    assert "mutagen" in combined
    assert "third-party dependencies" in normalized
    assert "binary" in normalized
    assert "legal review" in normalized
    assert "No legal clearance" in combined
