"""Visual theme constants for the XfinAudio desktop UI."""

from xfinaudio.desktop.library_columns import ordered_widths

_COMPACT_RESULTS_TABLE_MIN_HEIGHT = 118
_COMPACT_REVIEW_TABLE_MIN_HEIGHT = 100
_COMPACT_EMPTY_RECOMMENDATION_SECTION_MAX_HEIGHT = 72
_COMPACT_EXPORT_HISTORY_TABLE_MAX_HEIGHT = 92
_COMPACT_TABLE_ROW_HEIGHT = 24

_TRACK_TABLE_COLUMN_WIDTHS = ordered_widths()
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

# Aurora palette (v2.0.1 renewal, "v2 celebration"). Key tokens, kept literal
# inside the stylesheet because Qt style sheets are plain strings:
#   surfaces   #000000 window (user-provided swatch), #101b28 panel, #162434 elevated
#   text       #eaf4ff primary, #d2e4f5 secondary, #98b0cb muted
#   accent     #3df2dd signal mint (focus/hover), #46f3c5 -> #00c8f0 primary sweep
#   highlight  #5240d8 selection, #6a55f0 active selection
#   warm       #ffb000 status/Serato (unchanged identity anchor)
# Contrast ratios for every text/background pair are pinned by
# tests/test_theme_dark_mode.py.
_DJ_VISUAL_STYLESHEET = """
QMainWindow {
    background: #000000;
}
QWidget {
    background: #000000;
    color: #eaf4ff;
    font-size: 13px;
}
QLabel {
    color: #d2e4f5;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #ffb000;
    padding: 6px 8px;
    border: 1px solid #2a3646;
    border-radius: 8px;
    background: #101b28;
}
QLabel#guidanceLabel {
    color: #98b0cb;
}
QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #263a52, stop: 1 #1b2738);
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 10px;
    font-weight: 700;
}
QPushButton:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2f465f, stop: 1 #233349);
    border-color: #3df2dd;
}
QPushButton:focus {
    outline: 2px solid #3df2dd;
    border: 1px solid #3df2dd;
}
QPushButton:disabled {
    background: #131923;
    color: #6b7683;
    border-color: #1e2732;
}
QPushButton#primaryAction {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #46f3c5, stop: 1 #00c8f0);
    color: #04121a;
    border-color: #3df2dd;
    padding: 8px 18px;
    font-size: 14px;
}
QPushButton#secondaryAction {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #162434, stop: 1 #101b28);
    color: #d2e4f5;
    border: 1px solid #2a3646;
    padding: 3px 8px;
    font-weight: 600;
}
QPushButton#primaryAction:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #7df7d8, stop: 1 #35dcf8);
    border-color: #7df7d8;
}
QPushButton#secondaryAction:hover {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #1c2c3e, stop: 1 #162434);
    border-color: #3df2dd;
}
QFrame#sectionDivider {
    background: #1e2f42;
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
    background: #131923;
    color: #6b7683;
    border-color: #1e2732;
}
QComboBox {
    background: #162434;
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 8px;
}
QComboBox:hover {
    border-color: #3df2dd;
}
QComboBox:focus {
    outline: 2px solid #3df2dd;
    border: 1px solid #3df2dd;
}
QLineEdit {
    background: #101b28;
    color: #eaf4ff;
    border: 1px solid #32425a;
    border-radius: 8px;
    padding: 5px 8px;
}
QLineEdit:hover {
    border-color: #46617f;
}
QLineEdit:focus {
    outline: 2px solid #3df2dd;
    border: 1px solid #3df2dd;
}
QWidget#workflowSidebarPanel {
    background: #101b28;
    border: 1px solid #243444;
    border-radius: 8px;
}
QListWidget#workflowSidebar {
    background: #101b28;
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
    background: #162434;
}
QListWidget#workflowSidebar::item:selected {
    background: #5240d8;
    color: #eaf4ff;
}
QListWidget#workflowSidebar::item:disabled {
    color: #6b7683;
}
QTableWidget {
    background: #0f1a24;
    alternate-background-color: #13202c;
    color: #eaf4ff;
    gridline-color: #1e2f42;
    border: 1px solid #243444;
    border-radius: 8px;
    selection-background-color: #5240d8;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #5240d8;
    color: #ffffff;
}
QTableWidget::item:selected:active {
    background-color: #6a55f0;
    color: #ffffff;
}
QHeaderView::section {
    background: #142130;
    color: #6fe0e0;
    border: 0;
    border-right: 1px solid #283746;
    padding: 6px 8px;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #17242f;
    border: 0;
}
QToolTip {
    background: #1a2a38;
    color: #eaf4ff;
    border: 1px solid #3df2dd;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
