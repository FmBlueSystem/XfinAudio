"""Genre provider protocol, registry, and module-level enable helpers.

Mirrors the strategy-registry pattern from ``xfinaudio.recommendation.strategies``
so the genre package feels familiar to maintainers and stays symmetric with
existing extension seams.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from xfinaudio.genre.models import GenreCandidate
from xfinaudio.genre.settings import GenreEnrichmentSettings


@runtime_checkable
class GenreProvider(Protocol):
    """A pluggable source of genre candidates for a track.

    Implementations MUST be safe to call without a network when the underlying
    data source is cached locally, and SHOULD resolve raw labels through the
    canonical taxonomy before returning candidates. Implementations MAY raise
    on transient failures; the enrichment service isolates provider failures
    (see spec Scenario 2.3).
    """

    name: str

    def fetch(self, track: object) -> list[GenreCandidate]:
        """Return zero or more :class:`GenreCandidate` votes for ``track``."""
        ...


class GenreProviderRegistry:
    """In-process registry for :class:`GenreProvider` instances."""

    def __init__(self, providers: Iterable[GenreProvider] = ()) -> None:
        self._providers: dict[str, GenreProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: GenreProvider) -> None:
        """Register a provider by its ``name``; duplicates raise ``ValueError``."""
        if provider.name in self._providers:
            raise ValueError(f"Duplicate genre provider: {provider.name}")
        self._providers[provider.name] = provider

    def available(self) -> list[str]:
        """Return registered provider names in registration order."""
        return list(self._providers)

    def get(self, name: str) -> GenreProvider:
        """Return the registered provider for ``name`` or raise ``ValueError``."""
        try:
            return self._providers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown genre provider: {name}") from exc


_DEFAULT_REGISTRY: GenreProviderRegistry | None = None


def _default_registry() -> GenreProviderRegistry:
    """Return a process-wide registry, lazily constructed."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = GenreProviderRegistry()
    return _DEFAULT_REGISTRY


def register_provider(provider: GenreProvider, registry: GenreProviderRegistry | None = None) -> None:
    """Register a provider into the default (or supplied) registry."""
    target = registry if registry is not None else _default_registry()
    target.register(provider)


def enabled_providers(
    providers: Iterable[GenreProvider],
    settings: GenreEnrichmentSettings,
) -> list[GenreProvider]:
    """Return only the providers explicitly enabled in ``settings``.

    Unknown provider names in ``settings`` are silently ignored (they may
    reference providers that are not installed/imported on this system).
    """
    enabled: list[GenreProvider] = []
    for provider in providers:
        flag = settings.providers.get(provider.name, False)
        if flag:
            enabled.append(provider)
    return enabled


__all__ = [
    "GenreProvider",
    "GenreProviderRegistry",
    "enabled_providers",
    "register_provider",
]
