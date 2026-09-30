"""Synthetic, explicitly requested connection probes with safe UI statuses."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from xfinaudio.ai import nan_client
from xfinaudio.config.settings import AiSettings

PROBE_MESSAGE = "Reply with OK. XfinAudio connection test."


@dataclass(frozen=True)
class ConnectionStatus:
    state: str
    message: str


def endpoint_label() -> str:
    """Show the actual recipient host, never URL credentials, paths or queries."""
    try:
        endpoint = urlsplit(nan_client._resolve_endpoint())
        return endpoint.netloc
    except nan_client.NanConfigError:
        return "Invalid HTTPS endpoint"


def configuration_status(settings: AiSettings) -> ConnectionStatus:
    """Check configuration presence, without reading a credential file or sending."""
    if not settings.enabled:
        return ConnectionStatus("disabled", "AI disabled. Offline tools remain available.")
    try:
        nan_client._resolve_endpoint()
        key_present = bool(os.environ.get(nan_client.API_KEY_ENV, "").strip())
        file_present = nan_client._resolve_env_file_path(settings.env_file).is_file()
    except (nan_client.NanConfigError, OSError, ValueError):
        return _invalid_configuration()
    if not key_present and not file_present:
        return ConnectionStatus(
            "missing_key", "Credential not found. Configure NAN_API_KEY outside the app or choose an existing env file."
        )
    return ConnectionStatus("untested", "Configuration found, not tested. No data has been sent by this dialog.")


def run_connection_test(settings: AiSettings, *, transport: nan_client.Transport | None = None) -> ConnectionStatus:
    """Send only the disclosed synthetic text after an explicit user test action."""
    status = configuration_status(settings)
    if status.state != "untested":
        return status
    try:
        response = nan_client.chat(
            PROBE_MESSAGE, enabled=settings.enabled, env_file=settings.env_file, timeout=10.0, transport=transport
        )
    except nan_client.NanConfigError:
        return _invalid_configuration()
    except nan_client.NanRequestError as exc:
        # Never surface raw provider responses, paths or transport exceptions.
        if "HTTP status 401" in str(exc) or "HTTP status 403" in str(exc):
            return ConnectionStatus(
                "authentication_failed",
                "Authentication rejected. Check your provider credential outside the app, then retry.",
            )
        if "JSON" in str(exc) or "message.content" in str(exc):
            return _invalid_response()
        return ConnectionStatus(
            "unavailable", "Connection unavailable. Check network or provider, then retry. Offline tools still work."
        )
    except Exception:
        return _invalid_configuration()
    if not response.strip():
        return _invalid_response()
    return ConnectionStatus("connected", "Connection successful. No library content was sent.")


def _invalid_configuration() -> ConnectionStatus:
    return ConnectionStatus(
        "invalid_configuration",
        "Invalid configuration. Check the HTTPS endpoint and NAN_API_KEY outside the app, then retry.",
    )


def _invalid_response() -> ConnectionStatus:
    return ConnectionStatus(
        "invalid_response", "The provider returned an invalid response. Check the endpoint, then retry."
    )
