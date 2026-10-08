"""Repository publication artifact hygiene tests.

The publication tree is what git would publish, not what happens to sit in a
working directory. A local editor or Finder artefact that ``.gitignore`` already
excludes cannot reach a source distribution, so treating one as a publication
defect fails the release gate on a developer's machine while nothing publishable
is affected.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATTERNS = [".DS_Store", "*.bak"]
FORBIDDEN_ROOT_FILES = ["apiJira.txt", "context.md"]


def candidate_paths(root: Path = PROJECT_ROOT) -> set[str]:
    """Return the repository-relative paths that would actually be published.

    ``git ls-files`` reports the index, which is both the publication tree and
    the thing a contributor controls. Walking the filesystem instead makes every
    ignored local artefact look like a release blocker.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {entry for entry in result.stdout.split("\0") if entry}


def publication_offenders(paths: Iterable[str]) -> list[str]:
    """Return inspected paths matching a forbidden local or backup pattern."""
    return sorted(path for path in paths if any(PurePosixPath(path).match(pat) for pat in FORBIDDEN_PATTERNS))


def test_publication_tree_has_no_local_or_backup_artifacts() -> None:
    assert publication_offenders(candidate_paths()) == []


def test_publication_root_has_no_local_private_handoff_files() -> None:
    offenders = [name for name in FORBIDDEN_ROOT_FILES if name in candidate_paths()]

    assert offenders == []


def test_publication_gate_reads_the_index_not_the_filesystem(tmp_path: Path) -> None:
    """Regression: a git-ignored artefact on disk must never fail the gate.

    The gate rglobbed the working tree, so a root ``.DS_Store`` failed the
    release gate on macOS while git had never seen the file. The same name, once
    force-added to the index, must fail instead: that is the artefact that would
    actually be published.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")
    (repo / ".DS_Store").write_text("", encoding="utf-8")

    assert publication_offenders(candidate_paths(repo)) == []

    _git(repo, "add", "-f", ".DS_Store")

    assert publication_offenders(candidate_paths(repo)) == [".DS_Store"]


def test_gitignore_excludes_local_and_backup_artifacts() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".DS_Store" in gitignore
    assert "*.bak" in gitignore
    assert "apiJira.txt" in gitignore
    assert "context.md" in gitignore
    assert ".release-evidence/" in gitignore


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
