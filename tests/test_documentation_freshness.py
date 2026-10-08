"""Shipped documentation must only point at things that still exist.

Removing the Qt desktop in 4e31a3a was a code change, and the documents were
left behind: they still name ``src/xfinaudio/desktop/main_window.py``, the
translation scripts, ``scripts/pyinstaller_build_smoke.py`` and a
``uv run xfinaudio`` console script that no release ever declared. A reader who
follows those instructions wastes a session before discovering they cannot run,
so the documentation is guarded like code.

Documents that record history are allowed to keep the old paths when they say
so: a blockquote banner in the opening lines makes the whole document a record,
and a parenthesised ``(historical`` marker makes a single evidence row one.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
ARCHITECTURE_PREFIX = "docs/architecture/"
ARCHITECTURE_REGISTRY = "docs/architecture/README.md"
# The commit that removed the Qt desktop, the PySide6 dependency and the
# ``src/xfinaudio/desktop`` package. A historical architecture note has to name
# it so a reader knows which tree the note describes.
QT_REMOVAL_COMMIT = "4e31a3a"
# A document declares itself a record with a blockquote banner in its opening
# lines; a single line declares itself a record with a parenthesised marker. The
# two shapes are deliberately different: prose that merely mentions history --
# "Earlier checkpoints below are historical evidence" -- must not exempt a whole
# document, but an evidence row that cites a removed file can say so in place.
HISTORICAL_WORD = re.compile(r"historical", re.IGNORECASE)
LINE_HISTORICAL_MARKER = "(historical"
HISTORICAL_HEAD_LINES = 12
# Working notes, local ledgers and SDD records describe what was true when they
# were written; they are evidence, not instructions, so they are out of scope.
EXCLUDED_PREFIXES = ("docs/reviews/", "docs/superpowers/", "odd/", "openspec/")
EXCLUDED_FILENAMES = ("AGENTS.md",)
# Repository paths a reader is expected to open, resolved against the tree. The
# lookbehind keeps the pattern out of URLs, where the same suffix follows a
# slash and points at a published document rather than at this checkout.
REFERENCE_PATTERN = re.compile(
    r"(?<![\w/])[A-Za-z0-9_.-]*(?:src|tests|scripts|packaging|desktop-electron|assets|docs)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+"
)
UV_RUN_PATTERN = re.compile(r"uv run (?:--[a-z-]+ )*([A-Za-z][A-Za-z0-9_.-]*)")
# Commands ``uv run`` resolves without a console script: the tools this project
# depends on. Anything else -- such as the removed ``xfinaudio`` launcher -- has
# to exist in ``[project.scripts]``.
UV_RUN_KNOWN_TARGETS = frozenset({"python", "pytest", "ruff", "pyright", "pyinstaller"})


def tracked_documents() -> list[str]:
    """Return the tracked Markdown documents that describe the current tree."""
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        line
        for line in result.stdout.splitlines()
        if line
        and not line.startswith(EXCLUDED_PREFIXES)
        and Path(line).name not in EXCLUDED_FILENAMES
        and not Path(line).name.startswith(("PLAN", "SPEC-"))
    ]


def document_text(relative_path: str) -> str:
    """Read a tracked document as text."""
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def is_historical_record(text: str) -> bool:
    """Whether a document declares itself, in a blockquote banner, a record."""
    head = text.splitlines()[:HISTORICAL_HEAD_LINES]
    return any(line.strip().startswith(">") and HISTORICAL_WORD.search(line) for line in head)


def missing_references(text: str) -> list[str]:
    """Return repository paths the document names that do not exist.

    A document that declares itself a record is skipped whole; a document that
    describes the live tree can still exempt a single evidence row with the
    line marker when it cites a path that was removed.
    """
    if is_historical_record(text):
        return []
    missing: set[str] = set()
    for line in text.splitlines():
        if LINE_HISTORICAL_MARKER in line:
            continue
        for reference in REFERENCE_PATTERN.findall(line):
            reference = reference.strip("./").rstrip(".")
            if not reference or "*" in reference:
                continue
            if not (PROJECT_ROOT / reference).exists():
                missing.add(reference)
    return sorted(missing)


def declared_console_scripts() -> set[str]:
    """Return the console scripts ``pyproject.toml`` declares, if any."""
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return set(project.get("project", {}).get("scripts", {}))


def undeclared_uv_targets(text: str) -> list[str]:
    """Return ``uv run <name>`` commands that cannot resolve in this project."""
    if is_historical_record(text):
        return []
    allowed = UV_RUN_KNOWN_TARGETS | declared_console_scripts()
    undeclared: set[str] = set()
    for line in text.splitlines():
        if LINE_HISTORICAL_MARKER in line:
            continue
        for target in UV_RUN_PATTERN.findall(line):
            if target not in allowed:
                undeclared.add(target)
    return sorted(undeclared)


def architecture_documents() -> list[str]:
    """Return the tracked architecture notes, registry excluded."""
    return [
        path for path in tracked_documents() if path.startswith(ARCHITECTURE_PREFIX) and path != ARCHITECTURE_REGISTRY
    ]


def test_there_are_documents_and_architecture_notes_to_guard() -> None:
    """A guard that silently matches nothing would always pass."""
    assert tracked_documents()
    assert architecture_documents()


def test_shipped_documents_only_reference_existing_paths() -> None:
    offenders = {path: missing for path in tracked_documents() if (missing := missing_references(document_text(path)))}

    assert offenders == {}, f"documents reference paths that do not exist: {offenders}"


def test_readme_does_not_advertise_the_removed_translation_workflow() -> None:
    """The Qt translator scripts were deleted with the Qt desktop."""
    readme = document_text("README.md")

    assert "update_translations.py" not in readme
    assert "fill_spanish_translations.py" not in readme


def test_ai_settings_document_names_the_labels_the_panel_ships() -> None:
    """The AI settings document kept the removed Qt dialog's vocabulary.

    It told a reader to press **OK**, to use **Choose existing env file** and to
    look for a **Configure AI** action. The Electron panel is the shipped
    surface, so the document has to name the controls that exist there.
    """
    document = document_text("docs/ai-settings.md")
    view = (PROJECT_ROOT / "desktop-electron" / "renderer" / "optional-ai-view.ts").read_text(encoding="utf-8")

    assert "Guardar ajustes de IA" in view
    assert "Elegir archivo de credenciales" in view
    assert "Pressing **OK**" not in document
    assert "Configure AI" not in document
    assert "Choose existing env file" not in document
    assert "Pulsa **OK**" not in document
    assert "Guardar ajustes de IA" in document


def test_removed_qt_translation_artifacts_are_not_shipped() -> None:
    """The Qt Linguist sources and their compiled ``.qm`` files died with Qt.

    Nothing loads a ``.qm`` catalogue, no script compiles a ``.ts`` file and no
    console script feeds them, so only two leftovers kept them alive: a lint
    override for a deleted script and a wheel force-include that copied binary
    Qt catalogues into every published build.
    """
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert "fill_spanish_translations.py" not in pyproject
    assert "assets/translations" not in pyproject
    assert not list((PROJECT_ROOT / "translations").rglob("*.ts"))
    assert not list((PROJECT_ROOT / "assets" / "translations").rglob("*.qm"))


def test_documents_only_invoke_uv_commands_that_resolve() -> None:
    offenders = {
        path: undeclared for path in tracked_documents() if (undeclared := undeclared_uv_targets(document_text(path)))
    }

    assert offenders == {}, f"documents invoke commands that cannot run: {offenders}"


def test_architecture_notes_declare_their_status_and_are_registered() -> None:
    """Each note must say which tree it describes, and the index must list it."""
    unlabelled: list[str] = []
    unanchored: list[str] = []
    for path in architecture_documents():
        text = document_text(path)
        head = "\n".join(text.splitlines()[:HISTORICAL_HEAD_LINES])
        if not is_historical_record(text) and "(current" not in head:
            unlabelled.append(path)
        elif is_historical_record(text) and QT_REMOVAL_COMMIT not in text:
            unanchored.append(path)

    assert unlabelled == [], f"architecture notes do not declare their status: {unlabelled}"
    assert unanchored == [], f"historical architecture notes do not name {QT_REMOVAL_COMMIT}: {unanchored}"


def test_architecture_registry_lists_every_note_and_the_live_shape() -> None:
    assert (PROJECT_ROOT / ARCHITECTURE_REGISTRY).exists(), f"{ARCHITECTURE_REGISTRY} is missing"
    registry = document_text(ARCHITECTURE_REGISTRY)
    notes = [Path(path).name for path in architecture_documents()]

    undocumented = [name for name in notes if name not in registry]
    stale = [name for name in re.findall(r"\((?!https?:)([A-Za-z0-9_.-]+\.md)\)", registry) if name not in notes]

    assert undocumented == [], f"docs/architecture/README.md does not list: {undocumented}"
    assert stale == [], f"docs/architecture/README.md lists documents that do not exist: {stale}"
    assert "desktop-electron" in registry, "the index must point at the live desktop shell"
    assert "xfinaudio.headless" in registry, "the index must point at the live core entrypoint"


def test_replacing_a_path_with_a_historical_marker_keeps_it_a_record() -> None:
    """The marker is the escape hatch, so it has to work at both levels."""
    missing = "tests/test_main_window.py"
    assert missing_references(f"run uv run pytest {missing}\n") == [missing]
    assert missing_references(f"run uv run pytest {missing} (historical Qt-era test)\n") == []
    assert missing_references(f"{missing} (historical: removed with the Qt desktop)\n") == []
    assert missing_references(f"> **Historical (PySide6 era):** see {missing}.\n") == []
    assert undeclared_uv_targets("uv run xfinaudio\n") == ["xfinaudio"]
    assert undeclared_uv_targets("> **Historical (Qt era):** run uv run xfinaudio.\n") == []
    assert is_historical_record("> **Historical (PySide6 era):** describes the removed Qt desktop.\n")
    assert not is_historical_record("\n" * HISTORICAL_HEAD_LINES + f"> **Historical:** see {missing}\n")
    assert not is_historical_record("Earlier checkpoints below are historical evidence.\n")
    assert not is_historical_record("The Qt desktop is history; workflows below remain for reference.\n")


def test_missing_reference_in_a_tracked_document_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End to end: the guard must flag a live document, not only read its helpers."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "live.md").write_text("See `src/xfinaudio/desktop/main_window.py`.\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "tracked_documents", lambda: ["docs/live.md"])

    with pytest.raises(AssertionError):
        test_shipped_documents_only_reference_existing_paths()


def test_declared_launcher_is_accepted_and_removed_launcher_is_not() -> None:
    """``uv run xfinaudio`` is the defect; a declared console script would be fine."""
    assert undeclared_uv_targets("uv run pytest -q\n") == []
    assert undeclared_uv_targets("uv run xfinaudio\n") == ["xfinaudio"]
    assert undeclared_uv_targets("uv run xfinaudio (historical Qt launcher)\n") == []
