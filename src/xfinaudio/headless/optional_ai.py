"""Explicit optional assistance with immutable disclosures and fresh local Apply."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from xfinaudio.ai.list_chat import ACTION_TYPES, MAX_ACTIONS, VARIANTS
from xfinaudio.ai.nan_client import DEFAULT_ENDPOINT, Transport, request_context
from xfinaudio.config.settings import AiSettings
from xfinaudio.headless.ai_actions import apply_action, propose_actions, public_actions
from xfinaudio.headless.ai_context import AssistContext, build_context
from xfinaudio.headless.ai_execution import apply_context, execute_context
from xfinaudio.headless.ai_protocol import AI_FIELDS
from xfinaudio.headless.ai_transport import (
    MAX_REQUEST_BYTES,
    CredentialBinding,
    bind_credential,
    provider_request,
)
from xfinaudio.headless.chat_log import ChatLog, chat_log_enabled
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


# The exact body a confirmed request would carry may be inspected, never re-sent. It is
# bounded by the same outbound cap the transport enforces, so the preview can never claim
# more than one sendable request would.
MAX_PAYLOAD_PREVIEW_BYTES = MAX_REQUEST_BYTES
# The preview builds a real request object and aborts before the transport transfers it. The
# discardable header filler is never a credential: no key provider, binding, or file is read.
_UNUSED_PREVIEW_KEY = "preview-only-no-credential-is-read"


class _PayloadPreviewed(Exception):
    """Private abort raised once one provider body has been built and captured."""


def _serialized_body(context: AssistContext) -> bytes:
    """Build the exact provider body for ``context`` with no network, key, or credential access.

    The surface builders run unchanged through the ordinary execution path with a capture
    transport, so the preview is the provider's real body rather than a re-derived copy. The
    captured request object is discarded: only its JSON body leaves this function, never the
    authorization header.
    """
    captured: list[bytes] = []

    def capture(request: Any, *, timeout: float) -> Any:
        data = getattr(request, "data", None)
        if not isinstance(data, bytes):
            raise BackendError("ai_unavailable", "The retained request could not be previewed")
        captured.append(data)
        raise _PayloadPreviewed

    try:
        with request_context(enabled=True, key_provider=lambda: _UNUSED_PREVIEW_KEY):
            execute_context(context, capture)
    except _PayloadPreviewed:
        pass
    except BackendError:
        raise
    except Exception:
        raise BackendError("ai_unavailable", "The retained request could not be previewed") from None
    if not captured:
        raise BackendError("ai_unavailable", "The retained request could not be previewed")
    return captured[0]


def _parsed_chat_answer(answer: dict[str, Any]) -> bool:
    """The chat answer may also carry the proposals the parser kept, and nothing else."""
    actions = answer["actions"]
    if not isinstance(actions, list) or type(answer["droppedActions"]) is not int or answer["droppedActions"] < 0:
        return False
    if not isinstance(answer["rawText"], str):
        return False
    dropped = answer["droppedItems"]
    if not isinstance(dropped, list) or answer["droppedActions"] < len(dropped):
        return False
    for item in dropped:
        if not isinstance(item, dict) or set(item) != {"raw", "reason"} or not isinstance(item["reason"], str):
            return False
    if len(actions) > MAX_ACTIONS:
        return False
    for item in actions:
        if not isinstance(item, dict) or item.get("type") not in ACTION_TYPES:
            return False
        if not isinstance(item["reason"], str):
            return False
        kind = item["type"]
        if kind in ("replace", "move"):
            expected = {"type", "position", "reason"} if kind == "replace" else {"type", "position", "to", "reason"}
            if (
                set(item) != expected
                or type(item["position"]) is not int
                or ("to" in item and type(item["to"]) is not int)
            ):
                return False
        elif kind == "extend":
            if set(item) != {"type", "to", "reason"} or type(item["to"]) is not int:
                return False
        elif set(item) != {"type", "variant", "reason"} or item["variant"] not in VARIANTS:
            return False
    return True


def _identity(value: Any) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except (ValueError, AttributeError):
        raise BackendError("invalid_params", "Invalid assistance identity") from None


def _published(answer: dict[str, Any]) -> dict[str, Any]:
    """The part of one answer the DJ receives; the log diagnostics stay out of the ceiling."""
    return {key: value for key, value in answer.items() if key not in _DIAGNOSTIC_FIELDS}


#: The fields one chat turn carries for the opt-in log only; never published to the DJ.
_DIAGNOSTIC_FIELDS = ("actions", "droppedActions", "droppedItems", "rawText")


class OptionalAI:
    def __init__(self, backend: HeadlessBackend, transport: Transport | None = None) -> None:
        self.backend, self.transport = backend, transport
        self.preview: _Pending | None = None
        self.results: dict[str, _Completed] = {}
        # Off unless the DJ started the core with XFINAUDIO_CHAT_LOG=1.
        self.chat_log = ChatLog(backend.data_dir)
        self._epoch = 0

    def _log(self, event: str, **fields: Any) -> None:
        """Write one diagnostic line when the DJ opted in; a failure never fails the turn."""
        self.chat_log.write(event, **fields)

    def invalidate(self) -> None:
        """Discard pending consent and cached proposals after explicit context changes."""
        self.preview = None
        self.results.clear()
        self._epoch += 1

    def execute(
        self, method: str, params: dict[str, Any], token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        # One assistance command reads the library sources once, plus the one refresh its
        # own review guards ask for, exactly like the core command that carries it.
        with self.backend.review_actions.snapshot_scope():
            return self._execute(method, params, token, emit)

    def _execute(
        self, method: str, params: dict[str, Any], token: ScanCancellationToken, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        if method not in AI_FIELDS:
            raise BackendError("unknown_method", "Unknown optional assistance command")
        previous_results = dict(self.results) if method == "ai.prepare" else {}
        if method == "ai.prepare":
            # New or malformed input immediately revokes older consent/results and
            # prevents an already-running request from publishing into this scope.
            self.invalidate()
        # Fail-closed shapes: no unknown keys, and every required key present.
        # Only autoAuthorize (ai.settings.update) is optional, so older callers
        # that only send revision/enabled keep working.
        required = AI_FIELDS[method] - {"autoAuthorize"}
        if not isinstance(params, dict) or not set(params) <= AI_FIELDS[method] or not required <= set(params):
            raise BackendError("invalid_params", "Missing or unexpected optional assistance fields")
        try:
            if method == "ai.status":
                return {**self.backend.preferences.get_ai(), "recipient": DEFAULT_ENDPOINT}
            if method == "ai.settings.update":
                previous_revision = self.backend.preferences.revision
                result = self.backend.preferences.update_ai(params)
                self._configuration_changed(previous_revision)
                return {**result, "recipient": DEFAULT_ENDPOINT}
            if method == "ai.credential.set":
                path = params["path"]
                if path is not None:
                    if not isinstance(path, str) or not path or len(path) > 4096 or "\x00" in path:
                        raise BackendError("invalid_params", "Choose a bounded credential file path")
                    path = bind_credential(Path(path)).path
                previous_revision = self.backend.preferences.revision
                result = self.backend.preferences.set_ai_credential({"revision": params["revision"], "path": path})
                self._configuration_changed(previous_revision)
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
            if method == "ai.payload":
                return self.inspect_payload(params)
            if method in ("ai.chat.history", "ai.chat.reset"):
                return self._conversation(method)
            if method == "ai.chat.apply":
                action_id = params["actionId"]
                if not isinstance(action_id, str) or not 0 < len(action_id) <= 64:
                    raise BackendError("invalid_params", "Apply a change by its identity")
                shown = self._shown_action(action_id) if chat_log_enabled() else None
                try:
                    result = apply_action(self.backend, action_id)
                except BackendError as error:
                    self._log("apply_failed", actionId=action_id, errorCode=error.code)
                    raise
                if chat_log_enabled():
                    self._log(
                        "apply",
                        action=shown,
                        order=[
                            {"position": position, "title": track["title"]}
                            for position, track in enumerate(result["review"]["tracks"], start=1)
                        ],
                    )
                return result
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

    def inspect_payload(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return the exact retained request body for the current preview, without sending it.

        Read-only and side-effect free: it re-validates freshness through the same path as
        ``ai.confirmation``, then serializes the retained pending context. It never reads a
        credential, never opens a socket, and never publishes a result, so the bounded
        pending state survives the inspection unchanged. ``bytes`` is the exact outbound
        length; ``body`` is truncated to the transport cap and flagged when it exceeds it.
        """
        pending = self._pending(params["previewId"])
        self._fresh(pending.reference)
        body = _serialized_body(pending.context)
        truncated = len(body) > MAX_PAYLOAD_PREVIEW_BYTES
        text = body[:MAX_PAYLOAD_PREVIEW_BYTES].decode("utf-8", errors="ignore") if truncated else body.decode("utf-8")
        return {
            "previewId": pending.id,
            "surface": pending.context.surface,
            "recipient": DEFAULT_ENDPOINT,
            "request": pending.context.request,
            "body": text,
            "bytes": len(body),
            "truncated": truncated,
        }

    @staticmethod
    def _public_preview(pending: _Pending) -> dict[str, Any]:
        preview = {
            "previewId": pending.id,
            "surface": pending.context.surface,
            "recipient": DEFAULT_ENDPOINT,
            "disclosure": list(pending.disclosure),
            "requestPreview": pending.context.request,
        }
        # Consent for a conversation is asked once: only the first turn is a first turn.
        if pending.context.surface == "chat":
            preview["firstTurn"] = bool(pending.context.data["firstTurn"])
        return preview

    def _configuration_changed(self, previous_revision: str) -> None:
        """End pending consent and, on a real configuration change, the conversation.

        Consent is asked once per conversation, so a changed provider configuration
        (settings or credential) starts a new conversation and discloses it again.
        """
        self.invalidate()
        if self.backend.preferences.revision != previous_revision:
            self.backend.ai_conversation.reset()

    def _conversation(self, method: str) -> dict[str, Any]:
        """Return or clear the single in-memory conversation and its pending changes."""
        store = self.backend.ai_conversation
        if method == "ai.chat.reset":
            snapshot = store.reset()
            self._log("reset")
            return {"conversation": snapshot}
        return {"conversation": store.snapshot(), "actions": public_actions(self.backend, store.actions())}

    def _shown_action(self, action_id: str) -> dict[str, Any] | None:
        """The pending change exactly as the DJ sees it now, for the diagnostic log."""
        action = self.backend.ai_conversation.action(action_id)
        if action is None:
            return None
        return next((item for item in public_actions(self.backend, (action,)) if item["actionId"] == action.id), None)

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
            if context.surface == "chat":
                expected |= {"actions", "droppedActions", "droppedItems", "rawText"}
            if (
                not isinstance(answer, dict)
                or set(answer) != expected
                or answer["surface"] != context.surface
                or any(not isinstance(answer[field], str) for field in ("kind", "title", "text"))
                or type(answer["canApply"]) is not bool
                or not (answer["proposal"] is None or isinstance(answer["proposal"], dict))
                or answer["canApply"] != (answer["proposal"] is not None)
                # The diagnostics of the opt-in log are not part of what this ceiling bounds.
                or len(json.dumps(_published(answer), allow_nan=False).encode("utf-8")) > 64 * 1024
            ):
                raise ValueError
            if context.surface == "chat" and not _parsed_chat_answer(answer):
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
        try:
            answer = provider_request(
                pending.reference.settings,
                pending.reference.binding,
                lambda send: self._answer(pending.context, send),
                transport=self.transport,
                surface=pending.context.surface,
            )
        except BackendError as error:
            self._log("turn_failed", message=pending.context.request, errorCode=error.code)
            raise
        if token.is_cancelled:
            return cancelled
        if pending.epoch != self._epoch:
            self._stale()
        context = self._fresh(pending.reference)
        if token.is_cancelled:
            return cancelled
        # A successful chat turn is the only writer of the in-memory conversation and of
        # the changes the assistant proposed; a failed, refused or cancelled turn never
        # reaches this point.
        published = _published(answer)
        memory: dict[str, Any] = {}
        if context.surface == "chat":
            store = self.backend.ai_conversation
            changed = store.list_changed(context.data["listFingerprint"])
            actions, dropped_items = propose_actions(self.backend, context.selector["reviewId"], answer["actions"])
            store.record_actions(actions)
            shown = public_actions(self.backend, actions)
            memory = {
                "conversation": store.record(context.data["listFingerprint"], context.request, answer["text"]),
                "listChanged": changed,
                "actions": shown,
                "droppedActions": answer["droppedActions"] + len(dropped_items),
            }
            self._log(
                "turn",
                message=context.request,
                rawText=answer["rawText"],
                reply=answer["text"],
                actions=shown,
                droppedActions=memory["droppedActions"],
                droppedItems=[
                    *answer["droppedItems"],
                    *({"raw": item, "reason": reason} for item, reason in dropped_items),
                ],
                listChanged=changed,
                trackCount=context.data["trackCount"],
            )
        result_id = str(uuid4())
        self.results[result_id] = _Completed(pending.reference, pending.context, copy.deepcopy(published))
        while len(self.results) > 16:
            self.results.pop(next(iter(self.results)))
        return {"cancelled": False, "result": {"resultId": result_id, **copy.deepcopy(published), **memory}}
