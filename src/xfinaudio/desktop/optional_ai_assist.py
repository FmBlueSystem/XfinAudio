"""Explicit opt-in AI controls and stale-safe, GUI-thread delivery."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import cast

from PySide6.QtCore import QObject, Qt, QThread, Slot
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from xfinaudio.ai.nan_client import NanConfigError, is_ai_enabled
from xfinaudio.desktop._workers import BackgroundWorker, WorkerRegistry

Prepared = tuple[Callable[[], object], Callable[[object], None]]


class OptionalAssistPanel(QWidget):
    """Consent is session-only and unchecked until the user chooses it."""

    def __init__(self, disclosure: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.consent = QCheckBox(self.tr("Allow this AI request"))
        self.ask_button = QPushButton(self.tr("Ask AI"))
        self.cancel_button = QPushButton(self.tr("Cancel AI"))
        self.configure_button = QPushButton(self.tr("Configure AI"))
        self.cancel_button.setEnabled(False)
        self.configure_button.setToolTip(self.tr("Open AI provider and key-file settings"))
        for widget in (self.consent, self.ask_button, self.cancel_button, self.configure_button):
            widget.setAccessibleName(widget.text())
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        self.disclosure = QLabel(disclosure)
        self.status = QLabel(self.tr("Optional AI is off until you consent and click Ask AI."))
        for label in (self.disclosure, self.status):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            layout.addWidget(label)
        self.consent.setToolTip(disclosure)
        self.ask_button.setToolTip(self.tr("Send only the disclosed inputs to configured Nan AI"))
        self.cancel_button.setToolTip(self.tr("Ignore the response; a request already sent cannot be recalled"))


class OptionalAssistController(QObject):
    """Create snapshots on the GUI thread; retain superseded workers until exit."""

    def __init__(
        self,
        panel: OptionalAssistPanel,
        request: QLineEdit,
        *,
        prepare: Callable[[str], Prepared],
        context: Callable[[], object],
        configure: Callable[[], None],
        enabled: Callable[[], bool] = is_ai_enabled,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel, self.request = panel, request
        self._prepare, self._context, self._enabled = prepare, context, enabled
        self._registry = WorkerRegistry(self)
        self._token = 0
        self._snapshot: object = None
        self._apply: Callable[[object], None] | None = None
        self._thread: QThread | None = None
        self.busy = False
        panel.ask_button.clicked.connect(self.ask)
        panel.cancel_button.clicked.connect(self.cancel)
        panel.configure_button.clicked.connect(configure)
        request.textChanged.connect(self._invalidate)
        panel.consent.toggled.connect(self._invalidate)

    def _invalidate(self, *_args: object) -> None:
        if self.busy:
            self.cancel()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.panel.ask_button.setEnabled(not busy)
        self.panel.cancel_button.setEnabled(busy)

    def ask(self) -> None:
        if self.busy:
            return
        if not self.panel.consent.isChecked():
            self.panel.status.setText(self.tr("Review the disclosure and allow this AI request first."))
            return
        if not self._enabled():
            self.panel.status.setText(self.tr("AI is disabled. Choose Configure AI, enable it, then retry."))
            return
        text = self.request.text().strip()
        if not text:
            self.panel.status.setText(self.tr("Describe your request before asking AI."))
            return
        try:
            self._snapshot = (text, self._context())
            operation, self._apply = self._prepare(text)
        except ValueError:
            self.panel.status.setText(self.tr("No valid current evidence. Refresh or open a set, then retry."))
            return
        self._token += 1
        token = self._token
        thread = QThread(self)

        def invoke() -> tuple[int, bool, object]:
            try:
                return token, True, operation()
            except Exception as error:
                return token, False, error

        worker = BackgroundWorker(invoke)
        self._registry.retain(thread, worker)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._receive, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        worker.failed.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._set_busy(True)
        self.panel.status.setText(self.tr("Asking AI… You can cancel and keep working locally."))
        thread.start()

    def cancel(self) -> None:
        self._token += 1
        self._apply = None
        self._set_busy(False)
        # All older threads remain owned and retained; MainWindow drains them.
        if self._thread is not None:
            with suppress(RuntimeError):
                self._thread.requestInterruption()
        self.panel.status.setText(self.tr("AI canceled. Already-sent data cannot be recalled. You can retry."))

    @Slot(object)
    def _receive(self, delivery: object) -> None:
        token, success, value = cast(tuple[int, bool, object], delivery)
        if token != self._token or not self.busy:
            return
        if (
            self._snapshot != (self.request.text().strip(), self._context())
            or not self.panel.consent.isChecked()
            or not self._enabled()
        ):
            self.cancel()
            self.panel.status.setText(self.tr("Context changed. Ask AI again for the current view."))
            return
        self._set_busy(False)
        if success:
            try:
                cast(Callable[[object], None], self._apply)(value)
            except (ValueError, TypeError):
                self.panel.status.setText(
                    self.tr("AI response could not be validated. Simplify the request and retry.")
                )
                return
            self.panel.status.setText(self.tr("AI interpretation ready. Review the local evidence before applying."))
        elif isinstance(value, NanConfigError):
            self.panel.status.setText(
                self.tr("Choose Configure AI to check enablement and key-file settings, then retry.")
            )
        else:
            self.panel.status.setText(self.tr("AI unavailable or response invalid. Check configuration, then retry."))
