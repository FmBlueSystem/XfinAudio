#!/usr/bin/env python3
"""Render an evidence-based third-party dependency/license inventory."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import json
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNKNOWN = "Not provided in package metadata"
PYSIDE_QT_REVIEW_NOTE = "PySide6/Qt licensing requires legal review before binary redistribution."
LEGAL_LIMITATIONS = [
    "XfinAudio source is GPL-3.0-only, but dependency metadata does not clear redistribution obligations.",
    "Package metadata may be incomplete, ambiguous, or different from the license terms that apply to redistribution.",
    PYSIDE_QT_REVIEW_NOTE,
    "mutagen and other third-party dependencies require legal review before binary redistribution.",
    "No legal clearance or binary redistribution approval is implied by this inventory.",
]


class InventoryError(RuntimeError):
    """Raised when the dependency/license inventory cannot be produced safely."""


def normalize_name(name: str) -> str:
    """Normalize a Python distribution name for matching."""
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    """Extract a distribution name from a PEP 508-style requirement string."""
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
    if not match:
        raise InventoryError(f"could not parse dependency requirement: {requirement}")
    return match.group(1)


def read_project_dependency_names(project_root: Path) -> list[str]:
    """Read direct runtime, dev, and build dependency names from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    requirements: list[str] = []
    requirements.extend(data.get("project", {}).get("dependencies", []))
    for dependency_group in data.get("dependency-groups", {}).values():
        if isinstance(dependency_group, list):
            requirements.extend(item for item in dependency_group if isinstance(item, str))
    requirements.extend(data.get("build-system", {}).get("requires", []))

    names: list[str] = []
    seen: set[str] = set()
    for requirement in requirements:
        name = requirement_name(requirement)
        normalized = normalize_name(name)
        if normalized not in seen:
            seen.add(normalized)
            names.append(name)
    return names


def distribution_index() -> dict[str, importlib_metadata.Distribution]:
    """Index installed distributions by normalized package name."""
    indexed: dict[str, importlib_metadata.Distribution] = {}
    for distribution in importlib_metadata.distributions():
        metadata = cast(Any, distribution.metadata)
        name = metadata.get("Name")
        if name:
            indexed[normalize_name(name)] = distribution
    return indexed


def first_project_url(metadata: Any, label: str) -> str | None:
    """Return the first Project-URL value matching a label."""
    for project_url in metadata.get_all("Project-URL", []):
        if "," not in project_url:
            continue
        project_label, url = project_url.split(",", 1)
        if project_label.strip().lower() == label.lower():
            return url.strip()
    return None


def homepage_from_metadata(metadata: Any) -> str:
    """Read homepage or project URL metadata when available."""
    return (
        metadata.get("Home-page")
        or first_project_url(metadata, "Homepage")
        or first_project_url(metadata, "Home")
        or first_project_url(metadata, "Source")
        or first_project_url(metadata, "Repository")
        or UNKNOWN
    )


def license_metadata(metadata: Any) -> str:
    """Read license field or license classifiers from package metadata."""
    license_field = metadata.get("License")
    if license_field and license_field.strip():
        return " ".join(license_field.split())
    license_classifiers = [
        classifier for classifier in metadata.get_all("Classifier", []) if classifier.startswith("License ::")
    ]
    if license_classifiers:
        return "; ".join(license_classifiers)
    return UNKNOWN


def package_record(name: str, distribution: importlib_metadata.Distribution | None) -> dict[str, str]:
    """Build one package inventory record from installed distribution metadata."""
    if distribution is None:
        record = {
            "name": name,
            "version": UNKNOWN,
            "license_metadata": UNKNOWN,
            "summary": UNKNOWN,
            "homepage": UNKNOWN,
            "legal_review_note": (
                "Package was declared by the project but not found in installed distribution metadata."
            ),
        }
    else:
        metadata = cast(Any, distribution.metadata)
        actual_name = metadata.get("Name") or name
        record = {
            "name": actual_name,
            "version": getattr(distribution, "version", None) or metadata.get("Version") or UNKNOWN,
            "license_metadata": license_metadata(metadata),
            "summary": metadata.get("Summary") or UNKNOWN,
            "homepage": homepage_from_metadata(metadata),
            "legal_review_note": "",
        }
    if normalize_name(record["name"]) in {"pyside6", "pyside6-addons", "pyside6-essentials", "shiboken6"}:
        record["legal_review_note"] = PYSIDE_QT_REVIEW_NOTE
    return record


def build_inventory(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Build the third-party inventory for direct project dependencies."""
    dependency_names = read_project_dependency_names(project_root)
    installed = distribution_index()
    packages = [package_record(name, installed.get(normalize_name(name))) for name in dependency_names]
    packages.sort(key=lambda item: item["name"].lower())
    return {
        "schema_version": 1,
        "project": "XfinAudio",
        "source": "Direct dependencies from pyproject.toml matched to installed importlib.metadata distributions.",
        "packages": packages,
        "limitations": LEGAL_LIMITATIONS,
    }


def markdown_table_text(value: object) -> str:
    """Escape a value for Markdown table cells."""
    text = "—" if value is None or value == "" else str(value)
    return text.replace("\n", " ").replace("\r", " ").replace("|", "\\|")


def render_markdown(inventory: dict[str, Any]) -> str:
    """Render inventory data as Markdown."""
    lines = [
        "# Third-party dependency/license inventory",
        "",
        (
            "This inventory is generated from direct project dependency declarations and installed Python "
            "package metadata."
        ),
        "It is evidence for release readiness review, not legal clearance.",
        "",
        "## Packages",
        "",
        "| Name | Version | License metadata | Summary | Homepage / project URL | Legal review note |",
        "|------|---------|------------------|---------|------------------------|-------------------|",
    ]
    for package in inventory["packages"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_table_text(package["name"]),
                    markdown_table_text(package["version"]),
                    markdown_table_text(package["license_metadata"]),
                    markdown_table_text(package["summary"]),
                    markdown_table_text(package["homepage"]),
                    markdown_table_text(package["legal_review_note"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Limitations and legal review gates", ""])
    lines.extend(f"- {limitation}" for limitation in inventory["limitations"])
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "uv run python scripts/third_party_license_inventory.py",
            (
                "uv run python scripts/third_party_license_inventory.py --format json --output "
                "/tmp/xfinaudio-third-party-inventory.json"
            ),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def render_inventory(inventory: dict[str, Any], *, output_format: str) -> str:
    """Render an inventory as Markdown or JSON."""
    if output_format == "markdown":
        return render_markdown(inventory)
    if output_format == "json":
        return json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    raise InventoryError(f"unsupported output format: {output_format}")


def validate_output_path(output_path: Path, *, project_root: Path = PROJECT_ROOT) -> Path:
    """Reject output paths under project-root build/ or dist/."""
    resolved_project_root = project_root.resolve()
    resolved_output = output_path.expanduser().resolve()
    for artifact_dir in ("build", "dist"):
        forbidden_root = resolved_project_root / artifact_dir
        if resolved_output == forbidden_root or forbidden_root in resolved_output.parents:
            raise InventoryError(f"refusing to write inventory under project-root {artifact_dir}/")
    return resolved_output


def build_parser() -> argparse.ArgumentParser:
    """Build the inventory CLI parser."""
    parser = argparse.ArgumentParser(description="Render XfinAudio third-party dependency/license inventory.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format.")
    parser.add_argument("--output", type=Path, help="Optional output path; stdout is used by default.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the third-party inventory CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rendered = render_inventory(build_inventory(PROJECT_ROOT), output_format=args.format)
        if args.output is None:
            sys.stdout.write(rendered)
        else:
            output_path = validate_output_path(args.output, project_root=PROJECT_ROOT)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            print(f"Wrote third-party dependency/license inventory to {output_path}")
    except InventoryError as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
