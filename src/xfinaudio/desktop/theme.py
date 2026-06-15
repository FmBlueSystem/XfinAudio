"""Visual theme constants for the XfinAudio desktop UI."""

_COMPACT_RESULTS_TABLE_MIN_HEIGHT = 118
_COMPACT_REVIEW_TABLE_MIN_HEIGHT = 100
_COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT = 72
_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT = 92
_COMPACT_TABLE_ROW_HEIGHT = 24

_TRACK_TABLE_COLUMN_WIDTHS = (160, 145, 70, 70, 76, 90, 150, 130, 140, 86, 70, 220)
_RECOMMENDATION_TABLE_COLUMN_WIDTHS = (160, 150, 72, 70, 82, 130, 145, 92, 180, 120, 150)
_REVIEW_TABLE_COLUMN_WIDTHS = (70, 170, 170, 100, 100, 112, 100, 110, 180)
_SERATO_EXPORT_HISTORY_COLUMN_WIDTHS = (86, 110, 70, 260, 260, 260)
_DJ_READINESS_TABLE_COLUMN_WIDTHS = (180, 112, 520)

_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}
_READINESS_STATUS_TOOLTIPS = {
    "ready": "Ready: no action needed",
    "needs_review": "Needs Review: inspect before export",
    "blocked": "Blocked: fix before export",
}
_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}

_DJ_VISUAL_STYLESHEET = """
QMainWindow {
    background: #0b0f14;
}
QWidget {
    background: #0b0f14;
    color: #edf5ff;
    font-size: 13px;
}
QLabel {
    color: #d7e4f2;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #ffb000;
    padding: 6px 8px;
    border: 1px solid #2d3744;
    border-radius: 8px;
    background: #111923;
}
QLabel#guidanceLabel {
    color: #9fb3c8;
}
QPushButton {
    background: #1c2733;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton:hover {
    background: #253445;
    border-color: #00d4ff;
}
QPushButton:disabled {
    background: #141a21;
    color: #66717d;
    border-color: #202832;
}
QPushButton#primaryAction {
    background: #00d4ff;
    color: #061018;
    border-color: #00d4ff;
}
QPushButton#seratoExportButton {
    background: #ffb000;
    color: #121212;
    border-color: #ffcf5c;
}
QPushButton#primaryAction:disabled,
QPushButton#seratoExportButton:disabled {
    background: #141a21;
    color: #66717d;
    border-color: #202832;
}
QComboBox {
    background: #17212c;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit {
    background: #111923;
    color: #edf5ff;
    border: 1px solid #344456;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit:focus {
    border-color: #00d4ff;
}
QWidget#workflowSidebarPanel {
    background: #111923;
    border: 1px solid #263544;
    border-radius: 8px;
}
QListWidget#workflowSidebar {
    background: #111923;
    color: #edf5ff;
    border: 0;
    font-size: 13px;
    outline: 0;
}
QListWidget#workflowSidebar::item {
    padding: 8px;
    border-radius: 6px;
}
QListWidget#workflowSidebar::item:selected {
    background: #005b86;
    color: #edf5ff;
}
QListWidget#workflowSidebar::item:disabled {
    color: #66717d;
}
QTableWidget {
    background: #101820;
    alternate-background-color: #14202a;
    color: #edf5ff;
    gridline-color: #1e2d3a;
    border: 1px solid #263544;
    border-radius: 8px;
    selection-background-color: #005b86;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #005b86;
    color: #ffffff;
}
QTableWidget::item:selected:active {
    background-color: #0078b4;
    color: #ffffff;
}
QHeaderView::section {
    background: #151e28;
    color: #5caeb8;
    border: 0;
    border-right: 1px solid #2a3847;
    padding: 6px 8px;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #182635;
    border: 0;
}
QToolTip {
    background: #1a2633;
    color: #edf5ff;
    border: 1px solid #00d4ff;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
