"""Explicit optional assistance with immutable disclosures and fresh local Apply."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from xfinaudio.ai.nan_client import DEFAULT_ENDPOINT, Transport
from xfinaudio.config.settings import AiSettings
from xfinaudio.headless.ai_context import AssistContext, build_context
from xfinaudio.headless.ai_execution import apply_context, execute_context
from xfinaudio.headless.ai_protocol import AI_FIELDS
from xfinaudio.headless.ai_transport import CredentialBinding, bind_credential, provider_request
from xfinaudio.headless.common import BackendError
from xfinaudio.library.scan_service import ScanCancellationToken

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend


@dataclass(frozen=True)
class _Reference:
    surface: str
    selector: dict[str, Any]
    request: str
    revision: str
    settings_revision: str
    settings: AiSettings
    binding: CredentialBinding | None


@dataclass(frozen=True)
class _Pending:
    id: str
    reference: _Reference
    context: AssistContext
    disclosure: tuple[str, ...]
    epoch: int


@dataclass(frozen=True)
class _Completed:
    reference: _Reference
    context: AssistContext
    answer: dict[str, Any]


def _identity(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except (ValueError, AttributeError):
        raise BackendError("invalid_params", "Invalid assistance identity") from None


class OptionalAI:
    def __init__(self, backend: HeadlessBackend, transport: Transport | None = None) -> None:
        self.backend, self.transport = backend, transport
        self.preview: _Pending | None = None
        self.results: dict[str, _Completed] = {}
        self._epoch = 0

    def invalidate(self) -> None:
        """Discard pending consent and cached proposals after explicit context changes."""
        self.preview = None
        self.results.clear()
        self._epoch += 1

    def execute(
        self, method: str, params: dict[str, Any], token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        if method not in AI_FIELDS:
            raise BackendError("unknown_method", "Unknown optional assistance command")
        previous_results = dict(self.results) if method == "ai.prepare" else {}
        if method == "ai.prepare":
            # New or malformed input immediately revokes older consent/results and
            # prevents an already-running request from publishing into this scope.
            self.invalidate()
        if not isinstance(params, dict) or set(params) != AI_FIELDS[method]:
            raise BackendError("invalid_params", "Missing or unexpected optional assistance fields")
        try:
            if method == "ai.status":
                return {**self.backend.preferences.get_ai(), "recipient": DEFAULT_ENDPOINT}
            if method == "ai.settings.update":
                result = self.backend.preferences.update_ai(params)
                self.invalidate()
                return {**result, "recipient": DEFAULT_ENDPOINT}
            if method == "ai.credential.set":
                path = params["path"]
                if path is not None:
                    if not isinstance(path, str) or not path or len(path) > 4096 or "\x00" in path:
                        raise BackendError("invalid_params", "Choose a bounded credential file path")
                    path = bind_credential(Path(path)).path
                result = self.backend.preferences.set_ai_credential({"revision": params["revision"], "path": path})
                self.invalidate()
                return {**result, "recipient": DEFAULT_ENDPOINT}
            if method == "ai.prepare":
                preview = self._prepare(params)
                assert self.preview is not None
                # Identical normalized requests may retain the bounded history for the
                # original surfaces. An improvement request is request-scoped: each
                # prepare allocates a fresh token snapshot, so an earlier improvement
                # result must never be revived even when the reference matches.
                if "candidates" not in self.preview.context.data:
                    self.results.update(
                        (result_id, completed)
                        for result_id, completed in previous_results.items()
                        if completed.reference == self.preview.reference
                    )
                return preview
            if method == "ai.confirmation":
                pending = self._pending(params["previewId"])
                self._fresh(pending.reference)
                return self._public_preview(pending)
            if method == "ai.run":
                return self._run(params, token, emit)
            result_id = _identity(params["resultId"])
            completed = self.results.get(result_id)
            if completed is None:
                raise BackendError("stale_ai", "Request a current assistance result before applying")
            # Freshness re-checks the stable revision only. Apply keeps the prepare-time
            # context, so the request-scoped improvement token snapshot survives the
            # recomputation that `_fresh` performs.
            self._fresh(completed.reference)
            return apply_context(self.backend, completed.context, copy.deepcopy(completed.answer))
        except BackendError:
            raise
        except Exception:
            raise BackendError("ai_unavailable", "Optional assistance could not complete safely") from None

    def _settings(self) -> tuple[dict[str, Any], AiSettings]:
        public = self.backend.preferences.get_ai()
        settings = self.backend.preferences.ai_settings()
        if self.backend.preferences.revision != public["revision"]:
            self._stale()
        return public, settings

    def _prepare(self, params: dict[str, Any]) -> dict[str, Any]:
        if (
            not isinstance(params["surface"], str)
            or not isinstance(params["request"], str)
            or not isinstance(params["context"], dict)
        ):
            raise BackendError("invalid_params", "Choose a supported assistance surface and context")
        context = build_context(self.backend, params["surface"], copy.deepcopy(params["context"]), params["request"])
        public, settings = self._settings()
        binding = bind_credential(settings.env_file) if settings.env_file is not None else None
        reference = _Reference(
            context.surface,
            copy.deepcopy(context.selector),
            context.request,
            context.revision,
            public["revision"],
            settings,
            binding,
        )
        disclosure = context.disclosure
        if public["credentialLabel"] is not None:
            disclosure = (*disclosure, f"Credencial seleccionada: {public['credentialLabel']}")
        self.preview = _Pending(str(uuid4()), reference, context, disclosure, self._epoch)
        return self._public_preview(self.preview)

    @staticmethod
    def _public_preview(pending: _Pending) -> dict[str, Any]:
        return {
            "previewId": pending.id,
            "surface": pending.context.surface,
            "recipient": DEFAULT_ENDPOINT,
            "disclosure": list(pending.disclosure),
            "requestPreview": pending.context.request,
        }

    def _pending(self, preview_id: Any) -> _Pending:
        if self.preview is None or self.preview.id != _identity(preview_id):
            raise BackendError("stale_ai", "Prepare a current request before confirming")
        return self.preview

    def _stale(self) -> None:
        self.invalidate()
        raise BackendError("stale_ai", "The assistance context or configuration changed; prepare it again")

    def _fresh(self, reference: _Reference) -> AssistContext:
        public, settings = self._settings()
        if public["revision"] != reference.settings_revision or settings != reference.settings:
            self._stale()
        try:
            if reference.binding is not None and bind_credential(reference.binding.path) != reference.binding:
                self._stale()
            context = build_context(
                self.backend, reference.surface, copy.deepcopy(reference.selector), reference.request
            )
        except Exception:
            self._stale()
        if context.revision != reference.revision:
            self._stale()
        return context

    @staticmethod
    def _answer(context: AssistContext, transport: Transport) -> dict[str, Any]:
        try:
            answer = execute_context(context, transport)
            expected = {"surface", "kind", "title", "text", "proposal", "canApply"}
            if (
                not isinstance(answer, dict)
                or set(answer) != expected
                or answer["surface"] != context.surface
                or any(not isinstance(answer[field], str) for field in ("kind", "title", "text"))
                or type(answer["canApply"]) is not bool
                or not (answer["proposal"] is None or isinstance(answer["proposal"], dict))
                or answer["canApply"] != (answer["proposal"] is not None)
                or len(json.dumps(answer, allow_nan=False).encode("utf-8")) > 64 * 1024
            ):
                raise ValueError
            return answer
        except (ValueError, TypeError, KeyError):
            raise BackendError("invalid_ai_response", "The AI response was invalid; no changes were applied") from None

    def _run(
        self, params: dict[str, Any], token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        if params["confirmed"] is not True:
            raise BackendError("confirmation_required", "Confirm this disclosed request before sending")
        pending = self._pending(params["previewId"])
        self.preview = None
        cancelled = {"cancelled": True, "result": None}
        if token.is_cancelled:
            return cancelled
        self._fresh(pending.reference)
        emit({"phase": "ai", "processedCount": 0, "totalCount": 1})
        if token.is_cancelled:
            return cancelled
        answer = provider_request(
            pending.reference.settings,
            pending.reference.binding,
            lambda send: self._answer(pending.context, send),
            transport=self.transport,
            surface=pending.context.surface,
        )
        if token.is_cancelled:
            return cancelled
        if pending.epoch != self._epoch:
            self._stale()
        self._fresh(pending.reference)
        if token.is_cancelled:
            return cancelled
        result_id = str(uuid4())
        self.results[result_id] = _Completed(pending.reference, pending.context, copy.deepcopy(answer))
        while len(self.results) > 16:
            self.results.pop(next(iter(self.results)))
        return {"cancelled": False, "result": {"resultId": result_id, **copy.deepcopy(answer)}}
