#!/usr/bin/env python3
"""Manual QA harness for XfinAudio against a real Mixed In Key processed folder.

This script is intentionally separate from the test suite. The maintainer runs it
against a private MIK-processed library to produce evidence that the scan,
persistence, recommendation, and export paths behave correctly on real audio.

The script never writes to the user's real Serato library; it uses a temporary
_Serato_/Subcrates folder under the system temp directory.
"""

from __future__ import annotations

import argparse
import datetime
import subprocess
import tempfile
from pathlib import Path

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.exporting.serato_crate import write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import plan_serato_playlist_export
from xfinaudio.library.scan_service import MetadataScanService
from xfinaudio.library.track_repository import TrackRepository

DEFAULT_STRATEGIES = ("build", "same_energy", "peak_time", "warmup")
EVIDENCE_PATH = Path(__file__).resolve().parents[1] / "docs" / "qa-manual-mik-evidence.md"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run manual XfinAudio QA against a Mixed In Key processed folder.")
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing MIK-processed audio files.",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=list(DEFAULT_STRATEGIES),
        help="Strategy names to test (default: build same_energy peak_time warmup).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE_PATH,
        help="Path for the generated Markdown evidence file.",
    )
    parser.add_argument(
        "--git-commit",
        action="store_true",
        help="Capture the current git commit hash in the evidence.",
    )
    return parser.parse_args(argv)


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_qa(folder: Path, strategies: list[str]) -> dict:
    if not folder.exists():
        raise SystemExit(f"Folder does not exist: {folder}")
    if not folder.is_dir():
        raise SystemExit(f"Path is not a directory: {folder}")

    with tempfile.TemporaryDirectory(prefix="xfinaudio-mik-qa-") as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "qa.db"
        repository = TrackRepository(db_path)
        workflow = PlaylistWorkflowService(scan_service=MetadataScanService(), repository=repository)

        scan_result = workflow.scan_folder(folder)
        persisted = repository.list_tracks()

        recommendations: dict[str, dict] = {}
        for strategy_name in strategies:
            try:
                rec_result = workflow.recommend(persisted, strategy_name)
                report = rec_result.quality_report
                readiness = "ready" if report.warning_count == 0 else "needs_review"
                recommendations[strategy_name] = {
                    "track_count": len(rec_result.recommendation.ordered_tracks),
                    "warnings": rec_result.recommendation.warnings,
                    "readiness": readiness,
                }
            except Exception as exc:  # pragma: no cover - harness safety
                recommendations[strategy_name] = {"error": str(exc)}

        serato_folder = tmp_path / "_Serato_"
        (serato_folder / "Subcrates").mkdir(parents=True)
        export_results: list[dict] = []
        for strategy_name in strategies:
            rec = recommendations.get(strategy_name)
            if rec is None or "error" in rec:
                continue
            try:
                workflow_result = workflow.recommend(persisted, strategy_name)
                plan = plan_serato_playlist_export(f"QA {strategy_name}", workflow_result.recommendation, serato_folder)
                write_result = write_serato_crate(plan, confirm=True)
                export_results.append(
                    {
                        "strategy": strategy_name,
                        "crate_path": str(write_result.written_path),
                        "track_count": len(plan.relative_paths),
                        "validated": write_result.validated,
                    }
                )
            except Exception as exc:  # pragma: no cover - harness safety
                export_results.append({"strategy": strategy_name, "error": str(exc)})

        return {
            "folder": str(folder.resolve()),
            "scan": {
                "total_supported": len(persisted),
                "complete": scan_result.complete_count,
                "incomplete": scan_result.incomplete_count,
                "cancelled": scan_result.cancelled,
            },
            "recommendations": recommendations,
            "exports": export_results,
        }


def _render_evidence(result: dict, commit: str | None) -> str:
    lines: list[str] = [
        "# XfinAudio — Real Mixed In Key QA Evidence",
        "",
        f"- **Generated**: {datetime.datetime.now(tz=datetime.UTC).isoformat()}",
        f"- **Folder**: `{result['folder']}`",
    ]
    if commit:
        lines.append(f"- **Git commit**: `{commit}`")
    lines.extend(
        [
            "",
            "## Scan results",
            "",
            f"- Total supported tracks: {result['scan']['total_supported']}",
            f"- Complete metadata: {result['scan']['complete']}",
            f"- Incomplete metadata: {result['scan']['incomplete']}",
            f"- Cancelled: {result['scan']['cancelled']}",
            "",
            "## Recommendations",
            "",
        ]
    )

    for strategy_name, rec in result["recommendations"].items():
        lines.append(f"### {strategy_name}")
        if "error" in rec:
            lines.append(f"- Error: {rec['error']}")
        else:
            lines.append(f"- Tracks recommended: {rec['track_count']}")
            lines.append(f"- DJ readiness: {rec['readiness']}")
            if rec["warnings"]:
                lines.append("- Warnings:")
                for warning in rec["warnings"]:
                    lines.append(f"  - {warning}")
            else:
                lines.append("- Warnings: none")
        lines.append("")

    lines.extend(["## Serato crate exports (temporary)", ""])
    for export in result["exports"]:
        if "error" in export:
            lines.append(f"- {export['strategy']}: ERROR {export['error']}")
        else:
            lines.append(
                f"- {export['strategy']}: {export['track_count']} tracks, "
                f"validated={export['validated']}, crate={export['crate_path']}"
            )

    lines.extend(
        [
            "",
            "## Maintainer sign-off",
            "",
            "- [ ] I inspected the scan results and they match the source folder.",
            "- [ ] I inspected at least one generated Serato crate in a hex/text viewer.",
            "- [ ] I verified that no files were written outside the temporary evidence folder.",
            "- [ ] I confirm this evidence was generated against a real Mixed In Key processed library.",
            "",
            "<!-- MIK-QA-STATUS: completed -->",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = _run_qa(args.folder, args.strategies)

    if result["scan"]["complete"] == 0:
        print("ERROR: No complete tracks found. Check that the folder contains MIK-processed audio.")
        return 1

    commit = _git_commit() if args.git_commit else None
    evidence = _render_evidence(result, commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(evidence, encoding="utf-8")
    print(f"QA evidence written to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
