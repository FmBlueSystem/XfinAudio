#!/usr/bin/env python3
"""Run the complete configured pytest suite in fresh whole-file coverage batches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = Path(__file__).with_name("coverage_batch_plugin.py")


def plan_batches(items: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    """Target a process size without splitting a file or omitting any test."""
    if type(size) is not int or not 1 <= size <= 1000:
        raise ValueError("Batch size must be an integer from 1 to 1000")
    if not items:
        raise ValueError("Empty test collection")
    files: dict[str, list[dict[str, str]]] = {}
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"file", "nodeid"}:
            raise ValueError("Invalid collection manifest")
        filename, nodeid = item["file"], item["nodeid"]
        if not isinstance(filename, str) or not isinstance(nodeid, str) or not nodeid:
            raise ValueError("Invalid collection identity")
        relative = PurePosixPath(filename)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("Test file escapes project root")
        if nodeid in seen:
            raise ValueError("Duplicate collected test identity")
        seen.add(nodeid)
        files.setdefault(filename, []).append(item)
    batches: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    for group in files.values():
        if current and len(current) + len(group) > size:
            batches.append(current)
            current = []
        current.extend(group)
    if current:
        batches.append(current)
    return batches


def validate_coverage_data(paths: set[Path]) -> dict[str, str]:
    """Verify each process saved a real, non-symlink data file before combining."""
    from coverage import CoverageData
    from coverage.exceptions import CoverageException

    if not paths:
        raise ValueError("Batch produced no isolated coverage data")
    result = {}
    for filename in sorted(paths):
        if filename.is_symlink() or not filename.is_file() or filename.stat().st_size == 0:
            raise ValueError("Invalid coverage data file")
        try:
            CoverageData(basename=str(filename)).read()
        except CoverageException as error:
            raise ValueError("Invalid coverage data file") from error
        result[filename.name] = hashlib.sha256(filename.read_bytes()).hexdigest()
    return result


def source_fingerprint(root: Path) -> str:
    """Reject source/config drift while testing; generated caches are excluded."""
    paths = {root / "pyproject.toml", root / "uv.lock", *root.glob("*.py")}
    for directory in ("src", "tests", "scripts"):
        paths.update((root / directory).rglob("*.py"))
    digest = hashlib.sha256()
    for filename in sorted(path for path in paths if path.is_file()):
        if filename.resolve() != filename or not filename.is_relative_to(root):
            raise ValueError("Source fingerprint cannot follow symlinks")
        digest.update(str(filename.relative_to(root)).encode())
        digest.update(hashlib.sha256(filename.read_bytes()).digest())
    return digest.hexdigest()


def run(root: Path, evidence: Path | None, batch_size: int) -> int:
    root = root.resolve(strict=True)
    if type(batch_size) is not int or not 1 <= batch_size <= 1000:
        raise ValueError("Batch size must be from 1 to 1000")
    if os.environ.get("PYTEST_ADDOPTS", "").strip():
        raise ValueError("Unset PYTEST_ADDOPTS: the sharded gate cannot select a subset")
    if evidence is None:
        temporary_root = Path(tempfile.gettempdir()).resolve()
        if temporary_root.is_relative_to(root):
            raise ValueError("Coverage evidence must be outside the source checkout")
        evidence = Path(tempfile.mkdtemp(prefix="xfinaudio-coverage-", dir=temporary_root))
    else:
        evidence = evidence.resolve(strict=False)
        if evidence.is_relative_to(root):
            raise ValueError("Coverage evidence must be outside the source checkout")
        if evidence.exists():
            raise ValueError("Evidence directory must be new; old coverage cannot be reused")
        evidence.mkdir(parents=True)
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "status": "running",
        "projectRoot": str(root),
        "batchSizeTarget": batch_size,
        "commands": [],
        "batches": [],
    }
    destination = evidence / "manifest.json"

    def save() -> None:
        destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def fail(message: str, code: int = 1) -> int:
        manifest.update(status="failed", error=message)
        save()
        print(f"FAIL sharded coverage: {message}; evidence: {evidence}", flush=True)
        return code

    save()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
    }
    env["COVERAGE_FILE"] = str(evidence / ".coverage")
    env["PYTHONPATH"] = str(evidence) + os.pathsep + env.get("PYTHONPATH", "")
    shutil.copyfile(PLUGIN, evidence / "xfin_coverage_collection.py")
    pytest = [
        "-m",
        "pytest",
        "-q",
        "-c",
        str(root / "pyproject.toml"),
        "--rootdir",
        str(root),
        "-p",
        "xfin_coverage_collection",
    ]
    coverage = [sys.executable, "-m", "coverage"]
    rcfile = "--rcfile=" + str(root / "pyproject.toml")

    def command(arguments: list[str], logname: str) -> int:
        manifest["commands"].append(arguments)
        save()
        with (evidence / logname).open("w", encoding="utf-8") as log:
            completed = subprocess.run(arguments, cwd=root, env=env, text=True, stdout=log, stderr=subprocess.STDOUT)
        return completed.returncode

    try:
        fingerprint = source_fingerprint(root)
        manifest["sourceFingerprint"] = fingerprint
        collection = evidence / "collection.json"
        result = command(
            [sys.executable, *pytest, "--collect-only", "--xfin-collection-output", str(collection)], "collection.log"
        )
        if result:
            return fail("Complete test collection failed", result)
        items = json.loads(collection.read_text(encoding="utf-8"))
        batches = plan_batches(items, batch_size)
        manifest.update(collectedCount=len(items), batchCount=len(batches))
        save()
        print(
            f"Collected {len(items)} tests; {len(batches)} fresh whole-file batches; evidence: {evidence}", flush=True
        )
        measured: dict[str, str] = {}
        for index, batch in enumerate(batches, 1):
            if source_fingerprint(root) != fingerprint:
                return fail("Python source or project configuration changed during the gate")
            expected = evidence / f"batch-{index:03}-expected.json"
            actual = evidence / f"batch-{index:03}-collected.json"
            expected.write_text(json.dumps(batch), encoding="utf-8")
            files = list(dict.fromkeys(item["file"] for item in batch))
            arguments = [
                *coverage,
                "run",
                rcfile,
                "--parallel-mode",
                *pytest,
                "--xfin-collection-output",
                str(actual),
                "--xfin-expected-collection",
                str(expected),
                *files,
            ]
            before_data = set(evidence.glob(".coverage.*"))
            result = command(arguments, f"batch-{index:03}.log")
            manifest["batches"].append({"index": index, "count": len(batch), "files": files, "returnCode": result})
            save()
            if result:
                return fail(f"Batch {index}/{len(batches)} failed", result)
            data_files = validate_coverage_data(set(evidence.glob(".coverage.*")) - before_data)
            measured.update(data_files)
            manifest["batches"][-1]["coverageFiles"] = data_files
            save()
            execution = json.loads(Path(str(actual) + ".run.json").read_text(encoding="utf-8"))
            if (
                json.loads(actual.read_text(encoding="utf-8")) != batch
                or execution["exitStatus"] != 0
                or set(execution["executed"]) != {item["nodeid"] for item in batch}
            ):
                return fail(f"Batch {index} did not execute its exact manifest")
            print(f"PASS batch {index}/{len(batches)} ({len(batch)} tests)", flush=True)
        if source_fingerprint(root) != fingerprint:
            return fail("Python source or project configuration changed during the gate")
        if validate_coverage_data(set(evidence.glob(".coverage.*"))) != measured:
            return fail("Coverage data changed or disappeared before combining")
        for name, args in [
            ("coverage-combine", ["combine", rcfile, "--keep", str(evidence)]),
            ("coverage-report", ["report", rcfile]),
        ]:
            result = command([*coverage, *args], name + ".log")
            if result:
                return fail(f"{name} failed", result)
        manifest["status"] = "passed"
        save()
        print((evidence / "coverage-report.log").read_text(encoding="utf-8"), end="")
        print(f"PASS complete sharded coverage: {len(items)} tests; {evidence}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        return fail(str(error))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.project_root, args.evidence_dir, args.batch_size)
    except (OSError, ValueError) as error:
        print(f"FAIL sharded coverage: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
