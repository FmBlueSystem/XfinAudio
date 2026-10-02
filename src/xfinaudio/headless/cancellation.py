"""Cooperative job cancellation with removable resource-drain hooks."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from xfinaudio.library.scan_service import ScanCancellationToken

LOGGER = logging.getLogger(__name__)


class _Subscription:
    """Serialize invocation/retirement without holding the token's registry lock."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self._lock = threading.RLock()
        self._callback: Callable[[], None] | None = callback

    def run(self) -> None:
        with self._lock:
            callback, self._callback = self._callback, None
            if callback is not None:
                try:
                    callback()
                except Exception:
                    # A failed hook cannot skip other resource drains or the
                    # server's mandatory worker join and backend shutdown.
                    LOGGER.exception("Cancellation resource hook failed")

    def retire(self) -> None:
        # A snapshotted hook cannot start after retirement; an already-started
        # drain finishes before the owning resource can be retired.
        with self._lock:
            self._callback = None


class JobCancellationToken(ScanCancellationToken):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._callbacks: dict[object, _Subscription] = {}

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        key, subscription = object(), _Subscription(callback)
        with self._lock:
            self._callbacks[key] = subscription
            cancelled = self.is_cancelled
        if cancelled:
            subscription.run()

        def remove() -> None:
            with self._lock:
                self._callbacks.pop(key, None)
            subscription.retire()

        return remove

    def request_cancel(self) -> None:
        """Mark cancellation without drainage, for callers holding publication locks."""
        with self._lock:
            super().cancel()

    def cancel(self) -> None:
        """Request cancellation and drain each non-retired subscription once."""
        with self._lock:
            super().cancel()
            callbacks = tuple(self._callbacks.values())
        for callback in callbacks:
            callback.run()
