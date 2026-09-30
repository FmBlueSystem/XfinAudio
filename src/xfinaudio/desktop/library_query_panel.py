"""Editable offline search interpretation; existing quick filters stay independent."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from xfinaudio.desktop.library_query import LibraryQuery, parse_library_query


class LibraryQueryPanel(QWidget):
    filters_changed = Signal()

    def __init__(self, genres: Callable[[], list[str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._genres = genres
        self.query = LibraryQuery()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.request_input = QLineEdit()
        self.request_input.setPlaceholderText(self.tr("Describe filters: House, BPM 120-128, key 8A, energy 4-7"))
        self.request_input.setAccessibleName(self.tr("Describe Library filters"))
        self.interpret_button = QPushButton(self.tr("Interpret locally"))
        row.addWidget(self.request_input, 1)
        row.addWidget(self.interpret_button)
        layout.addLayout(row)
        grid = QGridLayout()
        self.fields: dict[str, QLineEdit] = {}
        for column, (name, label) in enumerate(
            (
                ("text", "Title / artist"),
                ("genre", "Genre"),
                ("bpm_min", "BPM min"),
                ("bpm_max", "BPM max"),
                ("key", "Key"),
                ("energy_min", "Energy min"),
                ("energy_max", "Energy max"),
            )
        ):
            field = QLineEdit()
            field.setAccessibleName(self.tr(label))
            field.setMinimumWidth(40)
            self.fields[name] = field
            grid.addWidget(QLabel(self.tr(label)), 0, column)
            grid.addWidget(field, 1, column)
            field.returnPressed.connect(self.apply_fields)
        layout.addLayout(grid)
        actions = QHBoxLayout()
        self.apply_button = QPushButton(self.tr("Apply edited filters"))
        self.clear_button = QPushButton(self.tr("Clear described filters"))
        self.status = QLabel(self.tr("Local metadata only. Unknown BPM, key and energy are never guessed."))
        self.status.setWordWrap(True)
        actions.addWidget(self.apply_button)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.status, 1)
        layout.addLayout(actions)
        self.interpret_button.clicked.connect(self.interpret)
        self.request_input.returnPressed.connect(self.interpret)
        self.apply_button.clicked.connect(self.apply_fields)
        self.clear_button.clicked.connect(self.clear)

    def interpret(self) -> None:
        try:
            query = parse_library_query(self.request_input.text(), self._genres())
        except ValueError as error:
            self.status.setText(str(error))
            return
        self._show_query(query)
        self._apply(query)

    def _show_query(self, query: LibraryQuery) -> None:
        for name, field in self.fields.items():
            value = getattr(query, name)
            text = f"{value:g}" if isinstance(value, (int, float)) else str(value or "")
            field.setText(text)

    def apply_fields(self) -> None:
        values: dict[str, object] = {name: field.text().strip() or None for name, field in self.fields.items()}
        values["text"] = values["text"] or ""
        if values["key"]:
            values["key"] = str(values["key"]).upper()
        try:
            query = LibraryQuery.model_validate(values)
        except ValueError:
            self.status.setText(
                self.tr(
                    "Check filters: minimum ≤ maximum, BPM 1-400, key 1A-12B, energy 1-10. Previous filters remain applied."
                )
            )
            return
        self._apply(query)

    def _apply(self, query: LibraryQuery) -> None:
        self.query = query
        self.status.setText(self.tr("Filters applied locally. Edit any field or clear them."))
        self.filters_changed.emit()

    def clear(self) -> None:
        self.request_input.clear()
        self._show_query(LibraryQuery())
        self._apply(LibraryQuery())
