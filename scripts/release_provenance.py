#!/usr/bin/env python3
"""Local release-process evidence, not a cryptographic publisher attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import stat
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE_COMMAND = ["uv", "run", "python", "scripts/release_gate_check.py", "--run"]


class ProvenanceError(RuntimeError):
    """Source or bundle does not match the gated release candidate."""


def source_commit(root: Path, expected: str | None = None) -> str:
    """Require clean tracked, staged and non-ignored untracked source at HEAD."""

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()

    if git("status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none"):
        raise ProvenanceError("Release packaging requires a clean source checkout")
    commit = git("rev-parse", "--verify", "HEAD")
    if expected is not None and commit != expected:
        raise ProvenanceError("Source commit changed since the release gate")
    return commit


def project_version(root: Path) -> str:
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    if (
        not isinstance(version, str)
        or not version
        or any(c not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.!+-" for c in version)
    ):
        raise ProvenanceError("Invalid project version for release filename")
    return version


def output_directory(root: Path, output: Path) -> Path:
    """Resolve relative paths before chdir and reject root build/dist outputs."""
    output = output.resolve()
    root = root.resolve()
    if output == root or any(output.is_relative_to(root / name) for name in ("build", "dist")):
        raise ProvenanceError("Release output must stay outside project-root build/dist")
    return output


def bundle_digest(bundle: Path, version: str) -> str:
    """Hash contents, paths, types and modes; never follow external links."""
    if bundle.is_symlink() or not bundle.is_dir():
        raise ProvenanceError("Expected a real app bundle directory")
    bundle = bundle.resolve()
    digest = hashlib.sha256()
    for path in [bundle, *sorted(bundle.rglob("*"))]:
        mode = path.lstat().st_mode
        content = ""
        if stat.S_ISLNK(mode):
            if not path.resolve().is_relative_to(bundle) or not path.exists():
                raise ProvenanceError("Bundle contains an external or broken symlink")
            content = os.readlink(path)
        elif stat.S_ISREG(mode):
            with path.open("rb") as stream:
                content = hashlib.file_digest(stream, "sha256").hexdigest()
        elif not stat.S_ISDIR(mode):
            raise ProvenanceError("Bundle contains an unsupported special file")
        entry = [path.relative_to(bundle).as_posix(), mode, content]
        digest.update(json.dumps(entry, ensure_ascii=True).encode() + b"\n")
    with (bundle / "Contents/Info.plist").open("rb") as stream:
        if plistlib.load(stream).get("CFBundleShortVersionString") != version:
            raise ProvenanceError("Bundle version does not match the source project")
    return digest.hexdigest()


def evidence_data(root: Path, bundle: Path, commit: str) -> dict[str, object]:
    source_commit(root, commit)
    version = project_version(root)
    return {
        "schema_version": 1,
        "source_commit": commit,
        "project_version": version,
        "gate_command": GATE_COMMAND,
        "bundle_sha256": bundle_digest(bundle, version),
    }


def record(root: Path, bundle: Path, commit: str, evidence: Path) -> None:
    """Called only after the shell pipeline's successful exact-source gate."""
    data = evidence_data(root, bundle, commit)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=evidence.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, evidence)
    finally:
        temporary.unlink(missing_ok=True)


def verify(root: Path, bundle: Path, commit: str, evidence: Path) -> None:
    """Refuse stale evidence or any changed bundle before execution/staging."""
    actual = json.loads(evidence.read_text())
    if actual != evidence_data(root, bundle, commit):
        raise ProvenanceError("Bundle provenance/integrity mismatch; rebuild from clean source")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("source", "version", "output", "record", "verify"))
    parser.add_argument("--commit")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "source":
            print(source_commit(PROJECT_ROOT, args.commit))
        elif args.action == "version":
            print(project_version(PROJECT_ROOT))
        elif args.action == "output" and args.output is not None:
            print(output_directory(PROJECT_ROOT, args.output))
        elif args.action in ("record", "verify") and all((args.bundle, args.commit, args.evidence)):
            operation = record if args.action == "record" else verify
            operation(PROJECT_ROOT, args.bundle, args.commit, args.evidence)
        else:
            parser.error("Missing required output or bundle/commit/evidence arguments")
    except (ProvenanceError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"error: release provenance: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
