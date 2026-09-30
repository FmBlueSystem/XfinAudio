"""Visible, editable confirmation boundary before deterministic Create planning."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.recommendation.prep_copilot import DJSetIntent
from xfinaudio.recommendation.strategies import available_strategies


class CreateIntentPreview(QWidget):
    confirmed = Signal(object)
    edit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._intent: DJSetIntent | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(self.tr("Review the interpreted request before generating local variants")))
        form = QFormLayout()
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0, 600)
        self.duration.setSpecialValueText(self.tr("Not specified"))
        self.duration.setSuffix(self.tr(" min"))
        self.count = QSpinBox()
        self.count.setRange(2, 100)
        self.genre = QLineEdit()
        self.strategy = QComboBox()
        self.strategy.addItems([str(name) for name in available_strategies()])
        self.role = QComboBox()
        self.role.addItems(["", "warmup", "peak_time", "chill"])
        for label, field in (
            ("Duration", self.duration),
            ("Maximum tracks", self.count),
            ("Genre / style", self.genre),
            ("Ordering strategy", self.strategy),
            ("Set role", self.role),
        ):
            field.setAccessibleName(self.tr(label))
            form.addRow(self.tr(label), field)
        layout.addLayout(form)
        self.constraints = QLabel()
        self.constraints.setWordWrap(True)
        self.constraints.setAccessibleName(self.tr("Preserved local constraints"))
        layout.addWidget(self.constraints)
        self.confirm_button = QPushButton(self.tr("Confirm and generate locally"))
        self.edit_button = QPushButton(self.tr("Edit request"))
        actions = QHBoxLayout()
        actions.addWidget(self.confirm_button)
        actions.addWidget(self.edit_button)
        layout.addLayout(actions)
        self.confirm_button.clicked.connect(self._confirm)
        self.edit_button.clicked.connect(self.edit_requested)
        self.hide()

    def show_intent(self, intent: DJSetIntent, constraints: str) -> None:
        self._intent = intent
        self.duration.setValue(intent.target_minutes or 0)
        self.count.setValue(intent.target_track_count)
        self.genre.setText(intent.genre_focus or "")
        self.strategy.setCurrentText(intent.strategy)
        self.role.setCurrentText(intent.slot_role or "")
        self.constraints.setText(constraints)
        self.show()

    def clear(self) -> None:
        self._intent = None
        self.hide()

    def _confirm(self) -> None:
        if self._intent is None:
            return
        data = self._intent.model_dump()
        data.update(
            target_minutes=self.duration.value() or None,
            target_track_count=self.count.value(),
            genre_focus=self.genre.text().strip() or None,
            strategy=self.strategy.currentText(),
            slot_role=self.role.currentText() or None,
        )
        self.confirmed.emit(DJSetIntent.model_validate(data))
