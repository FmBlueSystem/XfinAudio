"""Third-party dependency and license inventory tests."""

from __future__ import annotations

import importlib.util
import json
from email.message import Message
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "third_party_license_inventory.py"
INVENTORY_DOC = PROJECT_ROOT / "docs" / "third-party-license-inventory.md"
PACKAGING_STRATEGY_DOC = PROJECT_ROOT / "docs" / "packaging-strategy.md"
RELEASE_EVIDENCE_DOC = PROJECT_ROOT / "docs" / "release-candidate-evidence.md"
OPEN_SOURCE_RELEASE_BACKLOG_DOC = PROJECT_ROOT / "docs" / "open-source-release-backlog.md"

_inventory_spec = importlib.util.spec_from_file_location("third_party_license_inventory", INVENTORY_SCRIPT_PATH)
assert _inventory_spec is not None
assert _inventory_spec.loader is not None
third_party_license_inventory = importlib.util.module_from_spec(_inventory_spec)
_inventory_spec.loader.exec_module(third_party_license_inventory)


class FakeDistribution:
    """Minimal importlib.metadata distribution fake for inventory tests."""

    def __init__(
        self,
        name: str,
        version: str,
        *,
        license_text: str | None = None,
        classifiers: list[str] | None = None,
        summary: str | None = None,
        homepage: str | None = None,
        project_urls: list[str] | None = None,
    ) -> None:
        self.metadata = Message()
        self.metadata["Name"] = name
        self.metadata["Version"] = version
        if license_text is not None:
            self.metadata["License"] = license_text
        if summary is not None:
            self.metadata["Summary"] = summary
        if homepage is not None:
            self.metadata["Home-page"] = homepage
        for classifier in classifiers or []:
            self.metadata["Classifier"] = classifier
        for project_url in project_urls or []:
            self.metadata["Project-URL"] = project_url


def fake_distributions() -> list[FakeDistribution]:
    return [
        FakeDistribution(
            "PySide6",
            "6.7.0",
            classifiers=["License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"],
            summary="Python bindings for Qt",
            project_urls=["Homepage, https://pypi.org/project/PySide6/"],
        ),
        FakeDistribution(
            "mutagen",
            "1.47.0",
            license_text="GPL-2.0-or-later",
            summary="Read and write audio tags",
            homepage="https://mutagen.readthedocs.io/",
        ),
        FakeDistribution("pytest", "8.4.0", summary="pytest test framework"),
    ]


def test_json_inventory_includes_metadata_and_legal_limitations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(third_party_license_inventory.importlib_metadata, "distributions", fake_distributions)
    monkeypatch.setattr(
        third_party_license_inventory,
        "read_project_dependency_names",
        lambda _root: ["mutagen", "PySide6", "pytest"],
    )

    inventory = third_party_license_inventory.build_inventory(PROJECT_ROOT)

    assert inventory["limitations"] == third_party_license_inventory.LEGAL_LIMITATIONS
    assert [package["name"] for package in inventory["packages"]] == ["mutagen", "PySide6", "pytest"]
    pyside = inventory["packages"][1]
    assert pyside["version"] == "6.7.0"
    assert pyside["license_metadata"] == "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
    assert pyside["summary"] == "Python bindings for Qt"
    assert pyside["homepage"] == "https://pypi.org/project/PySide6/"
    assert pyside["legal_review_note"] == third_party_license_inventory.PYSIDE_QT_REVIEW_NOTE


def test_markdown_rendering_flags_missing_license_metadata_and_pyside_qt_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(third_party_license_inventory.importlib_metadata, "distributions", fake_distributions)
    monkeypatch.setattr(
        third_party_license_inventory,
        "read_project_dependency_names",
        lambda _root: ["PySide6", "pytest"],
    )

    markdown = third_party_license_inventory.render_inventory(
        third_party_license_inventory.build_inventory(PROJECT_ROOT),
        output_format="markdown",
    )

    assert "# Third-party dependency/license inventory" in markdown
    assert "| PySide6 | 6.7.0 | License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3) |" in markdown
    assert "| pytest | 8.4.0 | Not provided in package metadata |" in markdown
    assert third_party_license_inventory.PYSIDE_QT_REVIEW_NOTE in markdown
    assert "No legal clearance or binary redistribution approval is implied" in markdown


def test_cli_writes_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "inventory.json"
    monkeypatch.setattr(third_party_license_inventory.importlib_metadata, "distributions", fake_distributions)
    monkeypatch.setattr(
        third_party_license_inventory,
        "read_project_dependency_names",
        lambda _root: ["mutagen"],
    )

    assert third_party_license_inventory.main(["--format", "json", "--output", str(output_path)]) == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["packages"][0]["name"] == "mutagen"


@pytest.mark.parametrize("unsafe_dir", ["build", "dist"])
def test_cli_refuses_output_under_project_root_build_or_dist(unsafe_dir: str, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    unsafe_output = project_root / unsafe_dir / "inventory.md"
    project_root.mkdir()

    with pytest.raises(third_party_license_inventory.InventoryError, match=f"project-root {unsafe_dir}/"):
        third_party_license_inventory.validate_output_path(unsafe_output, project_root=project_root)


def test_docs_reference_inventory_and_pending_legal_review() -> None:
    inventory_doc = INVENTORY_DOC.read_text(encoding="utf-8")
    packaging_strategy = PACKAGING_STRATEGY_DOC.read_text(encoding="utf-8")
    release_evidence = RELEASE_EVIDENCE_DOC.read_text(encoding="utf-8")
    open_source_release_backlog = OPEN_SOURCE_RELEASE_BACKLOG_DOC.read_text(encoding="utf-8")

    assert "uv run python scripts/third_party_license_inventory.py" in inventory_doc
    assert "PySide6/Qt licensing requires legal review" in inventory_doc
    assert "No legal clearance or binary redistribution approval is implied" in inventory_doc
    assert "docs/third-party-license-inventory.md" in packaging_strategy
    assert "third-party dependency/license inventory" in release_evidence
    assert "legal review" in open_source_release_backlog
