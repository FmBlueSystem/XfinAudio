"""Source handoffs exclude generated trees and never follow repository symlinks."""

import hashlib
import subprocess
import sys
import tarfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "create_source_archive.py"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('fixture')\n")
    subprocess.run(["git", "-C", str(root), "add", "src"], check=True)
    return root


def _run(root: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), str(output)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_archive_excludes_dependency_symlinks_and_is_reproducible(tmp_path: Path):
    root = _repo(tmp_path)
    external = tmp_path / "dependencies"
    external.mkdir()
    (external / "private-fixture.txt").write_text("must not enter source")
    (root / "desktop-electron").mkdir()
    (root / "desktop-electron" / "node_modules").symlink_to(external)
    (root / "desktop-electron" / "package-lock.json").write_text("{}")
    (root / ".out").mkdir()
    (root / ".out" / "generated.js").write_text("generated")
    outputs = [tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"]
    for output in outputs:
        assert _run(root, output).returncode == 0
        with tarfile.open(output) as archive:
            assert archive.getnames() == ["desktop-electron/package-lock.json", "src/app.py"]
            assert all(item.isfile() for item in archive.getmembers())
    assert hashlib.sha256(outputs[0].read_bytes()).digest() == hashlib.sha256(outputs[1].read_bytes()).digest()


def test_archive_rejects_unexpected_file_or_parent_symlink_without_output(tmp_path: Path):
    for directory in (False, True):
        case = tmp_path / str(directory)
        case.mkdir()
        root = _repo(case)
        external = case / "external"
        external.mkdir()
        (external / "fixture.txt").write_text("not source")
        (root / "unexpected").symlink_to(external if directory else external / "fixture.txt")
        output = case / "source.tar.gz"
        result = _run(root, output)
        assert result.returncode != 0
        assert "symlink" in result.stderr.lower()
        assert not output.exists()


def test_archive_refuses_output_inside_source_and_sensitive_dotfiles(tmp_path: Path):
    root = _repo(tmp_path)
    assert _run(root, root / "source.tar.gz").returncode != 0
    (root / ".env").write_text("FIXTURE=not-a-secret")
    output = tmp_path / "source.tar.gz"
    assert _run(root, output).returncode != 0
    assert not output.exists()
