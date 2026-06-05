"""Source package hygiene check tests."""

from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "source_package_hygiene_check.py"
VALID_METADATA = (
    "Metadata-Version: 2.4\n"
    "Name: xfinaudio\n"
    "License-Expression: GPL-3.0-only\n"
    "Description-Content-Type: text/markdown\n\n"
    "# XfinAudio\n"
)


def load_source_package_hygiene_check():
    """Load the source package hygiene script module."""
    assert SCRIPT_PATH.exists(), "source package hygiene check script is missing"
    spec = importlib.util.spec_from_file_location("source_package_hygiene_check", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_sdist(path: Path, members: dict[str, str]) -> None:
    """Write a minimal sdist tarball with the provided member names."""
    with tarfile.open(path, "w:gz") as archive:
        for name, content in members.items():
            file_path = path.parent / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            archive.add(file_path, arcname=name)


def write_wheel(path: Path, members: dict[str, str]) -> None:
    """Write a minimal wheel zip with the provided member names."""
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_script_exists_and_exposes_release_gate_command() -> None:
    module = load_source_package_hygiene_check()

    assert module.RELEASE_GATE_COMMAND == ["uv", "build", "--out-dir", "<tempdir>"]


def test_inspect_sdist_rejects_forbidden_private_files(tmp_path: Path) -> None:
    module = load_source_package_hygiene_check()
    sdist = tmp_path / "xfinaudio-0.1.0.tar.gz"
    required_members = {f"xfinaudio-0.1.0/{name}": "public" for name in module.REQUIRED_SDIST_FILES}
    required_members["xfinaudio-0.1.0/apiJira.txt"] = "private"
    write_sdist(sdist, required_members)

    with pytest.raises(module.SourcePackageHygieneError, match="apiJira.txt"):
        module.inspect_sdist(sdist)


def test_inspect_sdist_requires_public_source_documents(tmp_path: Path) -> None:
    module = load_source_package_hygiene_check()
    sdist = tmp_path / "xfinaudio-0.1.0.tar.gz"
    members = {f"xfinaudio-0.1.0/{name}": "public" for name in module.REQUIRED_SDIST_FILES if name != "NOTICE.md"}
    write_sdist(sdist, members)

    with pytest.raises(module.SourcePackageHygieneError, match="NOTICE.md"):
        module.inspect_sdist(sdist)


def test_inspect_wheel_requires_metadata_license_and_description(tmp_path: Path) -> None:
    module = load_source_package_hygiene_check()
    wheel = tmp_path / "xfinaudio-0.1.0-py3-none-any.whl"
    write_wheel(
        wheel,
        {
            "xfinaudio/__init__.py": "",
            "xfinaudio-0.1.0.dist-info/METADATA": VALID_METADATA,
        },
    )

    metadata = module.inspect_wheel(wheel)

    assert metadata["license"] == "GPL-3.0-only"
    assert metadata["has_readme_description"] is True


def test_inspect_wheel_rejects_forbidden_artifacts(tmp_path: Path) -> None:
    module = load_source_package_hygiene_check()
    wheel = tmp_path / "xfinaudio-0.1.0-py3-none-any.whl"
    write_wheel(
        wheel,
        {
            "xfinaudio/__init__.py": "",
            "dist/local.txt": "artifact",
            "xfinaudio-0.1.0.dist-info/METADATA": VALID_METADATA,
        },
    )

    with pytest.raises(module.SourcePackageHygieneError, match="dist/"):
        module.inspect_wheel(wheel)


def test_build_check_uses_temp_out_dir_and_rejects_root_build_dist_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_source_package_hygiene_check()
    project_root = tmp_path / "project"
    project_root.mkdir()
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path, check: bool) -> object:
        calls.append((command, cwd))
        out_dir = Path(command[-1])
        assert out_dir != project_root / "dist"
        (out_dir / "xfinaudio-0.1.0.tar.gz").write_bytes(b"not inspected here")
        (out_dir / "xfinaudio-0.1.0-py3-none-any.whl").write_bytes(b"not inspected here")
        (project_root / "build").mkdir()
        return object()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "inspect_sdist", lambda path: {"path": path})
    monkeypatch.setattr(module, "inspect_wheel", lambda path: {"path": path})

    with pytest.raises(module.SourcePackageHygieneError, match="project-root build"):
        module.run_hygiene_check(project_root)

    assert calls
    assert calls[0][0][:3] == ["uv", "build", "--out-dir"]
    assert not calls[0][0][-1].startswith(str(project_root))
