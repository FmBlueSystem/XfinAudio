# Design: Keyboard Shortcuts

## Decision question

How do we add keyboard shortcuts without conflicts and with clear documentation?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. QShortcut in MainWindow | Simple; global shortcuts | May conflict with screen-specific shortcuts | **Selected** |
| B. Override keyPressEvent | Fine-grained control | Complex; hard to maintain | Rejected |
| C. QAction with shortcuts | Reusable; menu integration | More boilerplate | Rejected for this phase |

## Architecture impact

- `main_window.py`: Add QShortcut objects for each shortcut
- Connect shortcuts to existing slots where possible
- Add tooltips to buttons showing the shortcut

## Affected files

- `src/xfinaudio/desktop/main_window.py`
- `tests/test_main_window.py`
