#!/usr/bin/env python3
"""Review and repair tracks whose title and artist tags are swapped.

Reads the library database to find candidates, shows the evidence for each one,
and rewrites the audio file's tags only after you confirm that specific track.

Nothing is written without a per-track yes. Every change is journalled, so a
whole run can be undone with --revert.

Usage:
    scripts/fix_swapped_tags.py                 # review candidates one by one
    scripts/fix_swapped_tags.py --list          # print the shortlist, write nothing
    scripts/fix_swapped_tags.py --revert JOURNAL  # restore tags from a journal

The heuristic cannot tell a swap from a track genuinely named after a band
(a real library had "Poison" by Block & Crown flagged), which is exactly why
each one is confirmed by hand.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

src_root = Path(__file__).resolve().parent.parent / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from mutagen._file import File as MutagenFile  # noqa: E402

from xfinaudio.library.models import TrackRecord  # noqa: E402
from xfinaudio.metadata.swapped_tags import SwapCandidate, find_swapped_title_artist  # noqa: E402

_DEFAULT_DB = Path.home() / ".xfinaudio" / "xfinaudio.sqlite3"


def load_records(db_path: Path) -> list[TrackRecord]:
    """Read title/artist/path from the library database, read-only."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT path, title, artist FROM tracks").fetchall()
    finally:
        connection.close()
    return [
        TrackRecord(path=row["path"], title=row["title"], artist=row["artist"], metadata_status="complete")
        for row in rows
    ]


def _write_tags(path: Path, title: str, artist: str) -> None:
    audio = MutagenFile(path, easy=False)
    if audio is None or audio.tags is None:
        raise RuntimeError(f"no readable tags in {path}")
    audio.tags["title"] = [title]
    audio.tags["artist"] = [artist]
    audio.save()


def _describe(candidate: SwapCandidate, index: int, total: int) -> str:
    return (
        f"\n[{index}/{total}] {Path(candidate.path).name}\n"
        f"    now:      title={candidate.current_title!r}  artist={candidate.current_artist!r}\n"
        f"    proposed: title={candidate.suggested_title!r}  artist={candidate.suggested_artist!r}\n"
        f"    evidence: {candidate.artist_occurrences} other tracks credit "
        f"{candidate.current_title!r} as the artist"
    )


def review(candidates: list[SwapCandidate], journal_path: Path) -> int:
    """Walk the candidates, applying only the ones confirmed. Returns the count applied."""
    applied: list[dict[str, str]] = []
    total = len(candidates)
    for index, candidate in enumerate(candidates, start=1):
        print(_describe(candidate, index, total))
        if not Path(candidate.path).is_file():
            print("    SKIPPED: file not found")
            continue
        answer = input("    swap them? [y/N/q] ").strip().lower()
        if answer == "q":
            print("    stopping here")
            break
        if answer != "y":
            print("    left as is")
            continue
        try:
            _write_tags(Path(candidate.path), candidate.suggested_title, candidate.suggested_artist)
        except Exception as error:  # noqa: BLE001 - report and continue to the next file
            print(f"    FAILED: {error}")
            continue
        applied.append(
            {
                "path": candidate.path,
                "previous_title": candidate.current_title,
                "previous_artist": candidate.current_artist,
                "new_title": candidate.suggested_title,
                "new_artist": candidate.suggested_artist,
            }
        )
        print("    written")

    if applied:
        journal_path.write_text(json.dumps(applied, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRewrote {len(applied)} file(s).")
        print(f"Journal: {journal_path}")
        print(f"Undo with: {sys.argv[0]} --revert {journal_path}")
        print("Re-scan the library so the app picks up the new tags.")
    else:
        print("\nNothing was written.")
    return len(applied)


def revert(journal_path: Path) -> int:
    """Restore the tags recorded in a journal. Returns the count restored."""
    entries = json.loads(journal_path.read_text(encoding="utf-8"))
    restored = 0
    for entry in entries:
        try:
            _write_tags(Path(entry["path"]), entry["previous_title"], entry["previous_artist"])
        except Exception as error:  # noqa: BLE001 - report and continue
            print(f"FAILED {entry['path']}: {error}")
            continue
        restored += 1
    print(f"Restored {restored} of {len(entries)} file(s). Re-scan the library.")
    return restored


def main(argv: list[str] | None = None) -> int:
    """Review swapped title/artist tags and repair the confirmed ones."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB, help="Library database to read.")
    parser.add_argument("--list", action="store_true", help="Print the shortlist and exit without writing.")
    parser.add_argument("--revert", type=Path, help="Restore tags from a journal written by a previous run.")
    args = parser.parse_args(argv)

    if args.revert is not None:
        if not args.revert.is_file():
            print(f"error: journal not found: {args.revert}", file=sys.stderr)
            return 2
        revert(args.revert)
        return 0

    if not args.db.is_file():
        print(f"error: database not found: {args.db}", file=sys.stderr)
        return 2

    candidates = find_swapped_title_artist(load_records(args.db))
    if not candidates:
        print("No swapped title/artist tags found.")
        return 0

    if args.list:
        print(f"{len(candidates)} candidate(s), strongest evidence first:\n")
        print(f"{'title (now)':<28}{'artist (now)':<38}{'evidence':>9}")
        for candidate in candidates:
            print(
                f"{candidate.current_title[:26]:<28}"
                f"{candidate.current_artist[:36]:<38}"
                f"{candidate.artist_occurrences:>9}"
            )
        print("\nRun without --list to review and repair them one by one.")
        return 0

    print(f"{len(candidates)} candidate(s). Each one is confirmed individually; nothing is written otherwise.")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    journal_path = args.db.parent / f"swapped-tags-{stamp}.json"
    review(candidates, journal_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
