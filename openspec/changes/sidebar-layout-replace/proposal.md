# Proposal: Replace Tab Sidebar with Proper Navigation

## Intent

The QTabWidget with West-positioned tabs renders the tab bar on top of the content, causing text and tables to be cut off behind the sidebar. Replace the tab widget with a proper sidebar + stacked widget layout that gives full control over sizing and avoids the macOS Qt rendering bug.

## Scope

- Replace `QTabWidget` with a custom sidebar: `QListWidget` (or styled `QToolBar`) for navigation + `QStackedWidget` for content.
- Add explicit width and styling to the sidebar so the content area is properly bounded.
- Keep the existing navigation signals and accessibility.
- Add a "settings" or "exit" button at the bottom of the sidebar.

## Success criteria

1. Content widgets are no longer cut off by the sidebar.
2. The sidebar shows the 7 navigation items with clear labels and active-state highlighting.
3. All existing tests pass.
4. All verification commands pass.
