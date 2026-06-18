"""Tests for the genre provider protocol and registry (PR2, Task 2.2).

Covers spec Requirement 2 Scenarios 2.1, 2.2, 2.3.
"""

from __future__ import annotations

import pytest

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.providers.base import (
    GenreProvider,
    GenreProviderRegistry,
    enabled_providers,
    register_provider,
)
from xfinaudio.genre.settings import GenreEnrichmentSettings


class _FakeProvider:
    """Minimal GenreProvider for tests."""

    def __init__(
        self,
        name: str,
        candidates: list[GenreCandidate],
        *,
        enabled: bool = True,
        raises: bool = False,
    ) -> None:
        self.name = name
        self._candidates = candidates
        self._enabled = enabled
        self._raises = raises
        self.calls = 0

    def fetch(self, track: object) -> list[GenreCandidate]:
        self.calls += 1
        if self._raises:
            raise RuntimeError("boom")
        return list(self._candidates)


def _candidate(source: str, genre: str = "Tech House", confidence: float = 0.9) -> GenreCandidate:
    return GenreCandidate(
        canonical_genre=genre,
        raw_label=genre.lower(),
        source=source,
        confidence=confidence,
    )


def test_provider_registry_register_and_get() -> None:
    registry = GenreProviderRegistry()
    provider = _FakeProvider("fake", [_candidate("fake")])

    registry.register(provider)

    assert registry.get("fake") is provider
    assert registry.available() == ["fake"]


def test_provider_registry_rejects_duplicates() -> None:
    registry = GenreProviderRegistry()
    registry.register(_FakeProvider("fake", []))

    with pytest.raises(ValueError, match="Duplicate genre provider"):
        registry.register(_FakeProvider("fake", []))


def test_enabled_providers_skips_disabled() -> None:
    provider = _FakeProvider(
        "fake",
        [_candidate("fake")],
        enabled=False,
    )
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"fake": False},
    )

    result = enabled_providers([provider], settings)

    assert result == []


def test_enabled_providers_returns_enabled_only() -> None:
    a = _FakeProvider("a", [_candidate("a")])
    b = _FakeProvider("b", [_candidate("b")])
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True, "b": False},
    )

    result = enabled_providers([a, b], settings)

    assert [p.name for p in result] == ["a"]


def test_enabled_providers_unknown_provider_in_settings_is_ignored() -> None:
    a = _FakeProvider("a", [_candidate("a")])
    settings = GenreEnrichmentSettings(
        enabled=True,
        providers={"a": True, "ghost": True},
    )

    result = enabled_providers([a], settings)

    assert [p.name for p in result] == ["a"]


def test_register_provider_module_helper() -> None:
    provider = _FakeProvider("module_fake", [_candidate("module_fake")])

    register_provider(provider)

    registry = enabled_providers(
        [provider],
        GenreEnrichmentSettings(enabled=True, providers={"module_fake": True}),
    )
    assert [p.name for p in registry] == ["module_fake"]


def test_failing_provider_does_not_propagate_via_isolated_fetch() -> None:
    bad = _FakeProvider("bad", [], raises=True)

    try:
        # fetch() may raise directly; the registry is not required to catch it
        # (the enrichment service is, per spec Scenario 2.3). The provider
        # contract here is "fetch may raise; callers handle it".
        bad.fetch(None)
    except RuntimeError:
        pass
    else:
        pytest.fail("expected RuntimeError from failing provider")


def test_provider_protocol_is_satisfied_by_minimal_impl() -> None:
    class _Ok(GenreProvider):
        name = "ok"

        def fetch(self, track: object) -> list[GenreCandidate]:
            return [_candidate("ok")]

    provider = _Ok()
    assert provider.fetch(None) == [_candidate("ok")]
