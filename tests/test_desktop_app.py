def test_desktop_main_activates_window(monkeypatch, tmp_path) -> None:
    from xfinaudio.desktop import app as desktop_app

    class FakeQApplication:
        def __init__(self, argv):
            self.argv = argv

        def setApplicationName(self, name):
            pass

        def setApplicationDisplayName(self, name):
            pass

        def exec(self):
            return 0

    class FakeWindow:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self._state = desktop_app.Qt.WindowState.WindowMinimized

        def showMaximized(self):
            self.calls.append("showMaximized")

        def windowState(self):
            return self._state

        def setWindowState(self, state):
            self.calls.append("setWindowState")
            self._state = state

        def raise_(self):
            self.calls.append("raise")

        def activateWindow(self):
            self.calls.append("activateWindow")

    fake_window = FakeWindow()
    monkeypatch.setattr(desktop_app, "QApplication", FakeQApplication)
    monkeypatch.setattr(desktop_app.MainWindow, "with_defaults", lambda *_args: fake_window)
    monkeypatch.delenv("XFINAUDIO_PACKAGE_SMOKE", raising=False)
    monkeypatch.setenv("XFINAUDIO_DB_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("XFINAUDIO_SETTINGS_PATH", str(tmp_path / "settings.json"))

    assert desktop_app.main() == 0
    assert fake_window.calls == ["showMaximized", "setWindowState", "raise", "activateWindow"]
