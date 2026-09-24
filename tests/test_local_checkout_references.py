"""Live repository files must not point at another local checkout.

A second clone of this repository lived in a different folder for months, and
several operational files pointed at it: the OpenSpec project config, a restart
handoff, and a stray test script. Anything following those pointers worked on a
tree that was hundreds of commits behind, and two separate archived changes had
already recorded the defect without fixing it.
"""

from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "openspec" / "config.yaml"
# Assembled rather than written literally: this file is tracked, and the guard
# below scans tracked files, so a literal path here would make it flag itself.
MACHINE_LOCAL_CHECKOUT = "/".join(("", "Users", "freddymolina", "Documents", "audio"))
# Historical change records and review evidence may cite the old checkout; they
# are the record of what happened, not instructions for what to do next.
HISTORICAL_PREFIXES = ("openspec/changes/", "docs/reviews/")
# An ODD feature ledger is a live working document -- it holds the next tasks -- so
# it cites the old checkout only from inside the shapes these ledgers use for
# evidence: an evidence table row or a correction blockquote. Anywhere else in a
# ledger the path is a pointer, and a pointer to the wrong tree is the defect this
# module exists for.
LEDGER_CITATION_SHAPES = ("|", ">")
# The convention key is matched by meaning rather than by one spelling: the removed
# pointer used ``skill_registry``, and a rewrite to ``skill-registry`` names the same
# convention.
SKILL_REGISTRY_KEY = "skillregistry"


def config_text() -> str:
    """Read the OpenSpec project configuration as text."""
    return CONFIG_PATH.read_text(encoding="utf-8")


def tracked_files() -> list[str]:
    """Return the repository-relative paths git tracks."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def declared_block(key: str) -> str:
    """Return the lines nested under the first ``key:`` declaration.

    Read as text on purpose: PyYAML is not a dependency of this project. Indentation
    is what the format uses to decide which section a line belongs to, so a literal
    can no longer be satisfied by a declaration that lives in another section.
    """
    lines = config_text().splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{key}:" and not line.strip().startswith(f"{key}: "):
            continue
        indent = len(line) - len(line.lstrip(" "))
        block: list[str] = []
        for follower in lines[index + 1 :]:
            if follower.strip() and len(follower) - len(follower.lstrip(" ")) <= indent:
                break
            block.append(follower)
        return "\n".join(block)
    return ""


def declares_skill_registry(line: str) -> bool:
    """Whether a configuration line declares the skill-registry convention."""
    stripped = line.strip()
    if stripped.startswith("#") or ":" not in stripped:
        return False
    key = stripped.split(":", maxsplit=1)[0]
    return key.replace("-", "").replace("_", "").lower() == SKILL_REGISTRY_KEY


def ledger_mentions_that_are_pointers(text: str) -> list[str]:
    """Return a ledger's mentions of the old checkout that are not citations."""
    pointers: list[str] = []
    for line in text.splitlines():
        if MACHINE_LOCAL_CHECKOUT not in line or line.strip().startswith(LEDGER_CITATION_SHAPES):
            continue
        pointers.append(line.strip())
    return pointers


def test_config_exists() -> None:
    assert CONFIG_PATH.exists()


def test_config_names_no_machine_local_path() -> None:
    """Regression: ``project.root`` named a different, independent checkout."""
    offenders = [line.strip() for line in config_text().splitlines() if "/Users/" in line]

    assert offenders == [], f"machine-local path in openspec/config.yaml: {offenders}"


def test_project_root_is_the_repository_root() -> None:
    """The tooling resolves the project root with ``git rev-parse --show-toplevel``.

    A repository-relative ``.`` is the only value that keeps that meaning in any
    clone, on any machine.
    """
    root_line = next(line for line in config_text().splitlines() if line.strip().startswith("root:"))

    assert root_line.split(":", maxsplit=1)[1].strip().strip('"').strip("'") == "."


def test_declared_skill_registry_resolves_when_present() -> None:
    """A declared convention must point at a file the clone actually contains.

    ``conventions.skill_registry`` named ``.atl/skill-registry.md``, which does
    not exist anywhere: ``.atl/`` is git-ignored, so the pointer resolved only
    on the machine that wrote it. A convention this repository does not
    maintain must not be declared.
    """
    declared = [
        line.split(":", maxsplit=1)[1].strip() for line in config_text().splitlines() if declares_skill_registry(line)
    ]
    missing = [value for value in declared if not (PROJECT_ROOT / value).exists()]

    assert missing == [], f"openspec/config.yaml declares an unresolvable skill registry: {missing}"


def test_skill_registry_declared_under_a_renamed_key_is_still_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard matched one spelling of the key, so a rename kept the pointer.

    ``skill_registry`` was the name the pointer happened to use, not something the
    configuration format fixes. A key renamed to ``skill-registry`` re-declares the
    same unresolvable convention and has to be caught the same way.
    """
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: "conventions:\n  skill-registry: .atl/skill-registry.md\n",
    )

    with pytest.raises(AssertionError):
        test_declared_skill_registry_resolves_when_present()


def test_skill_registry_declared_under_a_renamed_key_passes_when_it_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction: a declared registry the clone contains is not an offence."""
    registry = tmp_path / ".atl" / "skill-registry.md"
    registry.parent.mkdir(parents=True)
    registry.write_text("# registry\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: "conventions:\n  skill_registry: .atl/skill-registry.md\n",
    )

    test_declared_skill_registry_resolves_when_present()


def test_declared_source_and_test_roots_exist() -> None:
    for key, relative in (("source_roots", "src/xfinaudio"), ("test_roots", "tests")):
        assert f"- {relative}" in declared_block(key), f"{relative} must stay declared under {key}:"
        assert (PROJECT_ROOT / relative).is_dir()


def test_declared_test_roots_cannot_be_satisfied_by_another_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``- tests`` appears under ``pytest.testpaths`` too, so the literal matched twice.

    The guard asked whether the text contains the literal, anywhere, and then
    whether the directory exists. Dropping ``test_roots`` left it green on the
    strength of a declaration in a different section, which is not what the
    assertion claims to check.
    """
    (tmp_path / "src" / "xfinaudio").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: textwrap.dedent(
            """
            project:
              source_roots:
                - src/xfinaudio
            testing:
              pytest:
                testpaths:
                  - tests
            """
        ),
    )

    with pytest.raises(AssertionError):
        test_declared_source_and_test_roots_exist()


def referenced_change_paths(text: str) -> list[str]:
    """Extract change paths, dropping sentence punctuation the regex may swallow.

    The character class matches ``.`` and ``/``, so a reference written at the
    end of a sentence captures its closing period and the guard then reports a
    path that does exist as missing.
    """
    return [reference.rstrip("./") for reference in re.findall(r"openspec/changes/[\w./-]+", text)]


def test_referenced_change_paths_exist() -> None:
    """A config pointing at a change nobody can find sends the next session hunting.

    ``current_intent`` referenced a change's design document long after that
    change had been archived under a dated directory.
    """
    missing = [
        reference for reference in referenced_change_paths(config_text()) if not (PROJECT_ROOT / reference).exists()
    ]

    assert missing == [], f"openspec/config.yaml references missing paths: {missing}"


def test_change_path_references_ignore_a_sentence_final_period(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The regex captures ``.``, so a sentence-final reference kept its period.

    The guard then reported a change directory that does exist as missing.
    """
    (tmp_path / "openspec" / "changes" / "demo-change").mkdir(parents=True)
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        sys.modules[__name__],
        "config_text",
        lambda: "reference_history:\n  - openspec/changes/demo-change.",
    )

    test_referenced_change_paths_exist()


def test_no_operational_file_points_at_another_local_checkout() -> None:
    """Regression: three live files told the reader to work in a different clone.

    The OpenSpec config named it as the project root, the restart handoff told a
    human to re-open it, and a test script put its ``src`` on ``sys.path``.
    """
    offenders: list[str] = []
    for relative in tracked_files():
        if relative.startswith(HISTORICAL_PREFIXES) or Path(relative).name.startswith("PLAN"):
            continue
        try:
            text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if MACHINE_LOCAL_CHECKOUT not in text:
            continue
        if relative.startswith("odd/tasks/"):
            offenders.extend(f"{relative}: {pointer}" for pointer in ledger_mentions_that_are_pointers(text))
            continue
        offenders.append(relative)

    assert offenders == [], f"live files point at another checkout: {offenders}"


def test_ledger_that_instructs_work_in_the_other_checkout_is_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``odd/tasks/`` exemption was written for a quoted evidence row.

    ``odd/tasks/harden-release-gates.md`` records the old checkout inside an evidence
    table, and the whole tree was exempted for that. Exempting the tree also permits
    the shape that matters most: a ledger's directive fields send the next session
    back to a tree nobody works in any more.
    """
    ledger = tmp_path / "odd" / "tasks" / "demo-ledger.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(f"**Worktree:** {MACHINE_LOCAL_CHECKOUT}\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "tracked_files", lambda: ["odd/tasks/demo-ledger.md"])

    with pytest.raises(AssertionError):
        test_no_operational_file_points_at_another_local_checkout()


def test_ledger_that_quotes_the_other_checkout_as_evidence_is_a_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The recorded defect is a citation, so the guard has to keep accepting it."""
    ledger = tmp_path / "odd" / "tasks" / "demo-ledger.md"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        f"| E1 | `project.root` named `{MACHINE_LOCAL_CHECKOUT}` | the path is gone. |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "tracked_files", lambda: ["odd/tasks/demo-ledger.md"])

    test_no_operational_file_points_at_another_local_checkout()
