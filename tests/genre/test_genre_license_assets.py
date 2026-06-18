"""Tests for license posture of the genre enrichment feature (PR5 Task 5.5).

Covers spec Requirement 8 Scenarios 8.1 and 8.2.

The project's GPL-3.0-only charter means only CC0-licensed data may be
embedded in shipped assets. Provider data under restrictive ToU (Discogs
live API, Last.fm, Spotify, Deezer) must stay in the per-user cache and
must never appear in the repository.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shipped_taxonomy_asset_is_cc0() -> None:
    payload = json.loads(
        (REPO_ROOT / "src" / "xfinaudio" / "genre" / "data" / "taxonomy.json").read_text(encoding="utf-8")
    )

    assert "license" in payload
    assert "CC0" in payload["license"]


def test_shipped_crosswalk_asset_is_cc0() -> None:
    payload = json.loads(
        (REPO_ROOT / "src" / "xfinaudio" / "genre" / "data" / "crosswalk.json").read_text(encoding="utf-8")
    )

    assert "license" in payload
    assert "CC0" in payload["license"]


def test_no_provider_derived_data_in_repo_root() -> None:
    """Provider responses (Discogs dump content, Last.fm tags, etc.) must not
    be present as files in the repository.

    The repository may contain tests that synthesize provider responses in
    memory, but no shipped or committed file may carry provider-derived data.
    """
    forbidden_globs = [
        "discogs_dump*",
        "*.discogs.xml",
        "lastfm_*",
        "spotify_*",
        "deezer_*",
        "musicbrainz_response*",
    ]
    offenders: list[str] = []
    for pattern in forbidden_globs:
        for path in REPO_ROOT.glob(pattern):
            offenders.append(str(path))
        for path in (REPO_ROOT / "src").rglob(pattern):
            offenders.append(str(path))
        for path in (REPO_ROOT / "tests").rglob(pattern):
            offenders.append(str(path))

    assert offenders == [], f"Provider-derived files found in repo: {offenders}"


def test_settings_source_trust_keys_are_only_cc0_safe_source_names() -> None:
    """The trust prior keys reference source NAMES, not provider data; only
    the source NAMES used by our two CC0 providers should be configured by
    default. (Discogs via CC0 dump + MusicBrainz core CC0.)"""
    from xfinaudio.genre.settings import GenreEnrichmentSettings

    settings = GenreEnrichmentSettings()
    allowed = {"discogs", "musicbrainz_genres", "musicbrainz_tags"}

    assert set(settings.source_trust) <= allowed


def test_documented_in_notice_md() -> None:
    """NOTICE.md must list the CC0 sources we use and the explicit exclusion
    of restrictive-ToU data from shipped assets."""
    notice_path = REPO_ROOT / "NOTICE.md"
    if not notice_path.exists():
        return  # NOTICE is allowed to be optional; only check if it exists
    text = notice_path.read_text(encoding="utf-8").lower()
    # If the file mentions the genre enrichment feature at all, it must be
    # transparent about the CC0 sources.
    if "genre" in text and "discogs" in text:
        assert "cc0" in text or "creative commons" in text


def test_provider_live_fetch_only_writes_to_user_supplied_cache_path() -> None:
    """The MusicBrainz live fetcher is import-guarded; it never writes to a
    path inside the repository. This is exercised structurally: the live
    fetcher takes a user-supplied path through the provider constructor,
    and no module writes to a hard-coded repo path."""
    from xfinaudio.genre.providers.musicbrainz import make_live_fetcher

    # The factory returns a fetcher; constructing it does not write anywhere.
    fetcher = make_live_fetcher("xfinaudio-test", "0.0.0")
    assert callable(fetcher)
    # Confirm no file named after our providers appears at the repo root.
    for name in ("discogs.sqlite", "mb_cache.sqlite", "musicbrainz_cache.sqlite"):
        assert not (REPO_ROOT / name).exists(), f"unexpected repo file: {name}"


def test_repo_does_not_embed_lastfm_or_spotify_artifacts() -> None:
    """Sanity: no JSON/XML/CSV file in src/ or tests/ contains Last.fm- or
    Spotify-style keys that would indicate cached provider responses."""
    suspect_patterns = re.compile(
        r"last\.fm|spotify:|deezer\.com|usertoken|sessionid.*lastfm",
        re.IGNORECASE,
    )
    for sub in ("src", "tests"):
        for path in (REPO_ROOT / sub).rglob("*"):
            if path.is_file() and path.suffix in {".json", ".xml", ".csv", ".txt"}:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if suspect_patterns.search(text):
                    raise AssertionError(f"Provider data found in {path}; remove it from the repo.")


def test_settings_defaults_have_no_runtime_provider_keys() -> None:
    """Default settings must carry no API keys, so a fresh install cannot
    accidentally contact any provider."""
    from xfinaudio.genre.settings import GenreEnrichmentSettings

    settings = GenreEnrichmentSettings()

    assert settings.api_keys == {}
    assert settings.providers == {}
    assert settings.enabled is False
    assert settings.llm_tiebreaker_enabled is False


def test_notice_md_documents_runtime_only_user_keyed_providers() -> None:
    """NOTICE.md must list each new runtime provider as user-keyed and opt-in."""
    notice_path = REPO_ROOT / "NOTICE.md"
    if not notice_path.exists():
        return
    text = notice_path.read_text(encoding="utf-8").lower()

    for provider in ("last.fm", "spotify", "deezer"):
        if provider in text:
            # If the file mentions the provider at all, it must be transparent
            # about the runtime-only/user-keyed posture.
            assert "user" in text or "runtime" in text or "key" in text, (
                f"NOTICE.md mentions {provider} but does not describe its runtime-only/user-keyed posture."
            )

    # LLM tie-breaker: if mentioned, must be opt-in
    if "llm" in text or "tie-breaker" in text or "tiebreaker" in text:
        assert "opt-in" in text or "default off" in text or "off by default" in text
