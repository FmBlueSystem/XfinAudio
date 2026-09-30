"""Public guidance for optional AI, data sharing and secure configuration."""

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_ai_setup_has_spanish_guidance_without_secret_command_examples() -> None:
    text = (DOCS / "ai-settings.md").read_text(encoding="utf-8")
    for fragment in (
        "## Configuración segura en español",
        "NAN_API_KEY",
        "~/.xfinaudio/apiIA.env",
        "owner-only access",
        "no cifra",
        "Probar conexión",
        "cuota",
        "no envía la biblioteca",
    ):
        assert fragment in text
    assert "export NAN_API_KEY=" not in text
    assert "NAN_API_KEY=<" not in text


def test_ai_workflows_disclose_distinct_contexts_and_local_authority() -> None:
    text = (DOCS / "ai-workflows.md").read_text(encoding="utf-8")
    for fragment in (
        "## Data sent by each action",
        "request text and sanitized genre vocabulary",
        "titles only when explicitly selected",
        "titles, artists, BPM, key and energy",
        "200 saved sets",
        "## Privacidad y control en español",
        "no es detección automática de reproducción",
        "direct deterministic Serato",
    ):
        assert fragment in text
