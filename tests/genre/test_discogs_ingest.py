"""Tests for Discogs dump ingestion (PR3, Task 3.1).

Uses small in-memory XML fixtures (a tiny subset of the real Discogs monthly
dump schema). All ingestion is offline: no network is involved.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from xfinaudio.genre.providers.discogs import ingest_discogs_dump

DISCOGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<discogs>
  <releases>
    <release id="100">
      <artists>
        <artist>
          <name>Some Artist</name>
        </artist>
      </artists>
      <title>Tech Track</title>
      <styles>
        <style>Tech House</style>
        <style>Deep House</style>
      </styles>
    </release>
    <release id="101">
      <artists>
        <artist>
          <name>Other Artist</name>
        </artist>
      </artists>
      <title>Genre Only Release</title>
      <genres>
        <genre>Electronic</genre>
      </genres>
    </release>
    <release id="102">
      <artists>
        <artist>
          <name>Variant Artist</name>
        </artist>
      </artists>
      <title>Same Title</title>
      <styles>
        <style>Techno</style>
      </styles>
    </release>
    <release id="103">
      <artists>
        <artist>
          <name>Variant Artist</name>
        </artist>
      </artists>
      <title>Same Title</title>
      <styles>
        <style>Peak Time Techno</style>
      </styles>
    </release>
  </releases>
</discogs>
"""


def _write_fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "discogs_fixture.xml"
    fixture.write_text(DISCOGS_XML, encoding="utf-8")
    return fixture


def test_ingest_writes_cache_table(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)
    cache = tmp_path / "discogs_cache.sqlite"

    rows = ingest_discogs_dump(fixture, cache)

    assert rows > 0
    assert cache.exists()
    conn = sqlite3.connect(cache)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert "discogs_release_style" in tables


def test_ingest_uses_styles_and_skips_genres(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)
    cache = tmp_path / "discogs_cache.sqlite"

    ingest_discogs_dump(fixture, cache)

    conn = sqlite3.connect(cache)
    try:
        # Release 100 has styles; release 101 has only genres (no styles) and should NOT appear.
        style_rows = list(conn.execute("SELECT DISTINCT artist_norm, title_norm FROM discogs_release_style"))
    finally:
        conn.close()
    keys = {(a, t) for a, t in style_rows}
    assert ("some artist", "tech track") in keys
    assert ("other artist", "genre only release") not in keys


def test_ingest_resolves_styles_via_crosswalk(tmp_path: Path) -> None:
    """Aliases like 'techno' are resolved to canonical 'Techno' at ingest time."""
    fixture = _write_fixture(tmp_path)
    cache = tmp_path / "discogs_cache.sqlite"

    ingest_discogs_dump(fixture, cache)

    conn = sqlite3.connect(cache)
    try:
        rows = list(
            conn.execute(
                "SELECT canonical_style FROM discogs_release_style WHERE artist_norm = ?",
                ("variant artist",),
            )
        )
    finally:
        conn.close()
    styles = {r[0] for r in rows}
    assert "Techno" in styles
    assert "Peak Time Techno" in styles


def test_ingest_is_idempotent(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)
    cache = tmp_path / "discogs_cache.sqlite"

    first = ingest_discogs_dump(fixture, cache)
    second = ingest_discogs_dump(fixture, cache)

    # Second run should not duplicate rows.
    conn = sqlite3.connect(cache)
    try:
        count = conn.execute("SELECT COUNT(*) FROM discogs_release_style").fetchone()[0]
    finally:
        conn.close()
    assert second == first  # same row count reported
    assert count == first  # DB has the same number of rows as a single ingest


def test_ingest_handles_missing_styles_gracefully(tmp_path: Path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<discogs>
  <releases>
    <release id="200">
      <artists><artist><name>Solo</name></artist></artists>
      <title>No Styles</title>
    </release>
  </releases>
</discogs>
"""
    fixture = tmp_path / "minimal.xml"
    fixture.write_text(xml, encoding="utf-8")
    cache = tmp_path / "cache.sqlite"

    rows = ingest_discogs_dump(fixture, cache)

    assert rows == 0
    conn = sqlite3.connect(cache)
    try:
        count = conn.execute("SELECT COUNT(*) FROM discogs_release_style").fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_ingest_creates_cache_dirs(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path)
    cache = tmp_path / "nested" / "dir" / "cache.sqlite"

    rows = ingest_discogs_dump(fixture, cache)

    assert rows > 0
    assert cache.exists()
