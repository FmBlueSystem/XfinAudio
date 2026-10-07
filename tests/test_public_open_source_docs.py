"""Public open-source readiness documentation tests."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"
CONTRIBUTING = PROJECT_ROOT / "CONTRIBUTING.md"
SECURITY = PROJECT_ROOT / "SECURITY.md"
NOTICE = PROJECT_ROOT / "NOTICE.md"
AGENTS = PROJECT_ROOT / "AGENTS.md"
PUBLIC_DOCS = [README, CONTRIBUTING, SECURITY, NOTICE, AGENTS]


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
        "Python 3.12",
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
        "Qt/PySide6 is no longer a dependency of XfinAudio",
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

    for line in text.splitlines():
        if "Test suite" in line or "Suite de tests" in line:
            assert not re.search(r"\d+\s+tests", line), (
                f"Hardcoded test count found in README suite-status line: {line!r}"
            )


def test_contributing_sets_dev_workflow_tdd_and_safety_boundaries() -> None:
    text = read(CONTRIBUTING)

    required_fragments = [
        "Python 3.12",
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


def test_loudness_disclosure_matches_default_enabled_comment_replacement() -> None:
    for path in (AGENTS, CONTRIBUTING, README, SECURITY):
        text = read(path)
        assert "enabled by default" in text
        assert "both analysis and automatic tag writing" in text
        assert "replaces existing comments" in text
        assert "explicit tag-write setting" not in text
    readme = read(README)
    assert "activado por defecto" in readme
    assert "análisis y la escritura automática" in readme
    assert "reemplaza los comentarios existentes" in readme
    assert "all ID3 COMM frames" in readme
    assert "does not restore replaced comments" in readme


def test_readme_describes_current_optional_ai_without_release_overclaims() -> None:
    project = tomllib.loads(read(PROJECT_ROOT / "pyproject.toml"))["project"]
    text = read(README)
    assert f"XfinAudio {project['version']}" in text
    assert f"Python {project['requires-python'].removeprefix('>=')}" in text
    notes_path = f"docs/release-notes-v{project['version']}.md"
    assert notes_path in text
    assert f"XfinAudio {project['version']}" in read(PROJECT_ROOT / notes_path)
    for fragment in (
        "## Optional AI and local control",
        "## IA opcional y control local",
        "NaN (Nan Builders)",
        "[secure AI setup](docs/ai-settings.md)",
        "[configuración segura de IA](docs/ai-settings.md#configuración-segura-en-español)",
        "No playback detection",
        "No detecta la reproducción",
        "Historical manual QA",
        "QA manual histórico",
    ):
        assert fragment in text
    for stale_claim in (
        "Python 3.11",
        "Full internationalization",
        "Internacionalización completa",
        "validated on macOS",
        "validado en macOS",
        "XfinAudio ships as an unsigned",
        "XfinAudio se distribuye como `.app`/`.dmg` sin firmar",
    ):
        assert stale_claim not in text


def test_security_sets_disclosure_placeholder_scope_and_dependency_caveats() -> None:
    text = read(SECURITY)

    required_fragments = [
        "Pre-release",
        "Responsible disclosure",
        "Do not include private audio libraries",
        "No live Serato writes by design",
        "does not mutate audio files outside loudness tag writing",
        "Qt/PySide6 is no longer a dependency of XfinAudio",
        "mutagen",
        "third-party dependencies",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text


def test_agents_governs_repo_root_without_hardcoded_path() -> None:
    text = read(AGENTS)

    assert "governs this repository root" in text
    assert "/Users/" not in text


def test_notice_records_license_dependency_inventory_and_legal_limits() -> None:
    text = read(NOTICE)

    required_fragments = [
        "GPL-3.0-only",
        "third-party dependency inventory",
        "evidence only",
        "Qt/PySide6 is no longer a dependency of XfinAudio",
        "mutagen",
        "binary/app bundle redistribution",
        "legal review",
        "No legal advice or legal clearance is implied",
    ]
    for fragment in required_fragments:
        assert fragment in text
