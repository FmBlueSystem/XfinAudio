"""Provider-free optional-assistance command shapes for the local dispatcher."""

from types import MappingProxyType

# Trusted per-surface budgets match the original interpreter/narrator policies.
AI_REQUEST_TIMEOUT_SECONDS = MappingProxyType(
    {"library": 30, "prep": 60, "review": 120, "saved": 30, "editor": 30, "metadata": 30, "live": 30, "connection": 10}
)

AI_FIELDS = {
    "ai.status": set(),
    "ai.settings.update": {"revision", "enabled"},
    "ai.credential.set": {"revision", "path"},
    "ai.prepare": {"surface", "request", "context"},
    "ai.confirmation": {"previewId"},
    "ai.run": {"previewId", "confirmed"},
    "ai.apply": {"resultId"},
}
