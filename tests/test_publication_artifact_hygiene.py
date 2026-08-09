"""Repository publication artifact hygiene tests."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATTERNS = [".DS_Store", "*.bak"]
FORBIDDEN_ROOT_FILES = ["apiJira.txt", "context.md"]
IGNORED_RUNTIME_DIRS = {".venv", ".pytest_cache", ".ruff_cache", "__pycache__"}


def is_publication_path(path: Path) -> bool:
    """Return whether a path belongs to the publication tree under test."""
    return not IGNORED_RUNTIME_DIRS.intersection(path.relative_to(PROJECT_ROOT).parts)


def test_publication_tree_has_no_local_or_backup_artifacts() -> None:
    offenders = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for pattern in FORBIDDEN_PATTERNS
        for path in PROJECT_ROOT.rglob(pattern)
        if is_publication_path(path)
    )

    assert offenders == []


def test_publication_root_has_no_local_private_handoff_files() -> None:
    offenders = [name for name in FORBIDDEN_ROOT_FILES if (PROJECT_ROOT / name).exists()]

    assert offenders == []


def test_gitignore_excludes_local_and_backup_artifacts() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".DS_Store" in gitignore
    assert "*.bak" in gitignore
    assert "apiJira.txt" in gitignore
    assert "context.md" in gitignore
    assert ".release-evidence/" in gitignore


def test_pyinstaller_spec_stamps_the_project_version_on_the_bundle() -> None:
    """Regression: the bundle reported 0.0.0 regardless of pyproject.

    macOS shows CFBundleShortVersionString in Get Info and stamps it on every
    crash report, so a hardcoded 0.0.0 makes two builds indistinguishable at
    the exact moment you need to tell them apart.
    """
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    spec = (root / "packaging" / "pyinstaller" / "xfinaudio.spec").read_text(encoding="utf-8")
    project_version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

    assert "version=app_version" in spec, "BUNDLE must receive a version"
    assert 'tomllib.loads((project_root / "pyproject.toml")' in spec, "version must come from pyproject, not a literal"
    assert project_version not in spec, "the version must be read, never pasted into the spec"
