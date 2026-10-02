# Design

Qt's QAbstractItemView keyPressEvent explicitly treats Return/Enter as editing
on Q_OS_MACOS, while other platforms emit activated. Own those two activation
keys in a small list subclass; consume them and emit the existing signal once.
Leave other keys/native activation to Qt. Connect the canonical itemActivated
signal only, avoiding the duplicate itemDoubleClicked route.
Source: https://github.com/qt/qtbase/blob/v6.10.2/src/widgets/itemviews/qabstractitemview.cpp

Review currently lays out an empty QLabel for narrator status. Use a local label
that derives visibility from its text so existing setText callers remain valid.
Keep all layout thresholds and accessible status/control text intact.

No persistence changes, API calls, credentials, audio or Serato writes.
