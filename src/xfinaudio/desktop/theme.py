"""Visual theme constants for the XfinAudio desktop UI."""

_COMPACT_RESULTS_TABLE_MIN_HEIGHT = 118
_COMPACT_REVIEW_TABLE_MIN_HEIGHT = 100
_COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT = 72
_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT = 92
_COMPACT_TABLE_ROW_HEIGHT = 24

_TRACK_TABLE_COLUMN_WIDTHS = (160, 145, 70, 70, 76, 76, 90, 150, 130, 140, 86, 70, 220)
_RECOMMENDATION_TABLE_COLUMN_WIDTHS = (160, 150, 72, 70, 82, 130, 145, 92, 180, 120, 150)
# Order, From, To, then seven five-character score columns, then Warnings.
# Must stay the same length as review_screen._TRANSITION_COLUMNS: the widths are
# applied positionally, so a short tuple shifts every column and starves the
# last ones. Guarded by tests/test_review_screen.py.
_REVIEW_TABLE_COLUMN_WIDTHS = (56, 210, 210, 62, 62, 68, 62, 68, 62, 68, 240)
_SERATO_EXPORT_HISTORY_COLUMN_WIDTHS = (86, 110, 70, 260, 260, 260)
_DJ_READINESS_TABLE_COLUMN_WIDTHS = (180, 112, 520)

_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}
_READINESS_STATUS_TOOLTIPS = {
    "ready": "Ready: no action needed",
    "needs_review": "Needs Review: inspect before export",
    "blocked": "Blocked: fix before export",
}
_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}

# Spectrum palette (v1.8.3 renewal). Key tokens, kept literal inside the
# stylesheet because Qt style sheets are plain strings:
#   surfaces   #080c12 window, #0f1721 panel, #151f2b elevated
#   text       #eaf4ff primary, #cfe0f0 secondary, #93aac4 muted
#   accent     #2ce8f5 signal cyan (focus/hover), #3ef0d2 -> #00c2e6 primary sweep
#   highlight  #463ac4 selection, #5a4be0 active selection
#   warm       #ffb000 status/Serato (unchanged identity anchor)
# Contrast ratios for every text/background pair are pinned by
# tests/test_theme_dark_mode.py.
_DJ_VISUAL_STYLESHEET = """
QMainWindow {
    background: #080c12;
}
QWidget {
    background: #080c12;
    color: #eaf4ff;
    font-size: 13px;
}
QLabel {
    color: #cfe0f0;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #ffb000;
    padding: 6px 8px;
    border: 1px solid #2a3646;
    border-radius: 8px;
    background: #0f1721;
}
QLabel#guidanceLabel {
    color: #93aac4;
}
QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #24354a, stop: 1 #1a2534);
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2d4159, stop: 1 #223145);
    border-color: #2ce8f5;
}
QPushButton:focus {
    outline: 2px solid #2ce8f5;
    border: 1px solid #2ce8f5;
}
QPushButton:disabled {
    background: #12181f;
    color: #6b7683;
    border-color: #1e2732;
}
QPushButton#primaryAction {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #3ef0d2, stop: 1 #00c2e6);
    color: #04121a;
    border-color: #2ce8f5;
    padding: 8px 18px;
    font-size: 14px;
}
QPushButton#secondaryAction {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #151f2b, stop: 1 #0f1721);
    color: #cfe0f0;
    border: 1px solid #2a3646;
    padding: 3px 8px;
    font-weight: 600;
}
QPushButton#primaryAction:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #6ff7de, stop: 1 #22d6f7);
    border-color: #6ff7de;
}
QPushButton#secondaryAction:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #1b2939, stop: 1 #151f2b);
    border-color: #2ce8f5;
}
QFrame#sectionDivider {
    background: #1c2b3b;
    border: 0;
    max-height: 1px;
}
QPushButton#seratoExportButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffd36a, stop: 1 #ffb000);
    color: #121212;
    border-color: #ffcf5c;
    padding: 8px 18px;
    font-size: 14px;
}
QPushButton#seratoExportButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffe08a, stop: 1 #ffc13d);
    border-color: #ffe08a;
}
QPushButton#primaryAction:disabled,
QPushButton#seratoExportButton:disabled {
    background: #12181f;
    color: #6b7683;
    border-color: #1e2732;
}
QComboBox {
    background: #151f2b;
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 8px;
}
QComboBox:hover {
    border-color: #2ce8f5;
}
QComboBox:focus {
    outline: 2px solid #2ce8f5;
    border: 1px solid #2ce8f5;
}
QLineEdit {
    background: #0f1721;
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit:hover {
    border-color: #46617f;
}
QLineEdit:focus {
    outline: 2px solid #2ce8f5;
    border: 1px solid #2ce8f5;
}
QWidget#workflowSidebarPanel {
    background: #0f1721;
    border: 1px solid #243444;
    border-radius: 8px;
}
QListWidget#workflowSidebar {
    background: #0f1721;
    color: #eaf4ff;
    border: 0;
    font-size: 13px;
    outline: 0;
}
QListWidget#workflowSidebar::item {
    padding: 8px;
    border-radius: 6px;
}
QListWidget#workflowSidebar::item:hover {
    background: #151f2b;
}
QListWidget#workflowSidebar::item:selected {
    background: #463ac4;
    color: #eaf4ff;
}
QListWidget#workflowSidebar::item:disabled {
    color: #6b7683;
}
QTableWidget {
    background: #0e161e;
    alternate-background-color: #121d27;
    color: #eaf4ff;
    gridline-color: #1c2b3b;
    border: 1px solid #243444;
    border-radius: 8px;
    selection-background-color: #463ac4;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #463ac4;
    color: #ffffff;
}
QTableWidget::item:selected:active {
    background-color: #5a4be0;
    color: #ffffff;
}
QHeaderView::section {
    background: #131c26;
    color: #63d3d8;
    border: 0;
    border-right: 1px solid #283746;
    padding: 6px 8px;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #16222f;
    border: 0;
}
QToolTip {
    background: #182430;
    color: #eaf4ff;
    border: 1px solid #2ce8f5;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
