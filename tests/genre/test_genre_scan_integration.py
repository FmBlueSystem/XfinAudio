"""Integration tests for the scan -> enrichment hook (PR5 Task 5.4).

Verifies the optional ``enrichment_service`` parameter on
``scan_folder`` and ``MetadataScanService.scan``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xfinaudio.genre.enrichment_service import EnrichmentService
from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.settings import GenreEnrichmentSettings
from xfinaudio.library.scan_service import scan_folder


def _read_tags_factory() -> Any:
    def read_tags(path: Path) -> dict[str, list[str]]:
        return {
            "title": [path.stem],
            "artist": ["Test Artist"],
            "bpm": ["120.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiI4QSIsInNvdXJjZSI6Im1peGVkaW5rZXkifQ=="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
            "genre": ["Disco"],
        }

    return read_tags


def _list_paths(paths: list[Path]) -> Any:
    return lambda _folder: paths


def test_scan_folder_attaches_genre_decision_when_enrichment_enabled() -> None:
    root = Path("/library")
    paths = [root / "a.flac", root / "b.flac"]

    class _Provider:
        name = "stub"

        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, track: object) -> list[GenreCandidate]:
            self.calls += 1
            return [
                GenreCandidate(
                    canonical_genre="Tech House",
                    raw_label="tech house",
                    source="stub",
                    confidence=0.9,
                )
            ]

    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"stub": True},
        source_trust={"stub": 1.0},
    )
    provider = _Provider()
    service = EnrichmentService(providers=[provider], settings=settings)  # type: ignore[list-item]

    records = scan_folder(
        root,
        list_paths=_list_paths(paths),
        read_tags=_read_tags_factory(),
        enrichment_service=service,
    )

    assert len(records) == 2
    assert all(r.genre_decision is not None for r in records)
    assert all(r.genre_decision.primary == "Tech House" for r in records)  # type: ignore[union-attr]
    assert provider.calls == 2
    # Original file-tag genre must be preserved untouched.
    assert all(r.genre == "Disco" for r in records)


def test_scan_folder_skips_enrichment_when_service_disabled() -> None:
    root = Path("/library")
    paths = [root / "a.flac"]
    service = EnrichmentService(
        providers=[],
        settings=GenreEnrichmentSettings(enabled=False, providers={}),
    )

    records = scan_folder(
        root,
        list_paths=_list_paths(paths),
        read_tags=_read_tags_factory(),
        enrichment_service=service,
    )

    assert len(records) == 1
    assert records[0].genre_decision is None


def test_scan_folder_skips_enrichment_when_service_omitted() -> None:
    root = Path("/library")
    paths = [root / "a.flac"]

    records = scan_folder(
        root,
        list_paths=_list_paths(paths),
        read_tags=_read_tags_factory(),
    )

    assert len(records) == 1
    assert records[0].genre_decision is None


def test_scan_folder_keeps_genre_decision_none_when_no_signal() -> None:
    """A provider that returns no candidates leaves the track with no decision."""
    root = Path("/library")
    paths = [root / "a.flac"]

    class _EmptyProvider:
        name = "empty"

        def fetch(self, track: object) -> list[GenreCandidate]:
            return []

    settings = GenreEnrichmentSettings(enabled=True, providers={"empty": True}, source_trust={"empty": 1.0})
    service = EnrichmentService(
        providers=[_EmptyProvider()],  # type: ignore[list-item]
        settings=settings,
    )

    records = scan_folder(
        root,
        list_paths=_list_paths(paths),
        read_tags=_read_tags_factory(),
        enrichment_service=service,
    )

    assert len(records) == 1
    assert records[0].genre_decision is None
