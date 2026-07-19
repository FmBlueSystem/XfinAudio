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

    macos_calls = []

    assert desktop_app.main(macos_configurator=lambda name, icon: macos_calls.append((name, icon))) == 0
    assert fake_window.calls == ["showMaximized", "setWindowState", "raise", "activateWindow"]
    assert macos_calls[0][0] == "XfinAudio"


def test_package_smoke_exits_without_creating_main_window(monkeypatch, tmp_path) -> None:
    from xfinaudio.desktop import app as desktop_app

    class FakeQApplication:
        def __init__(self, argv):
            self.argv = argv

        def setApplicationName(self, name):
            pass

        def setApplicationDisplayName(self, name):
            pass

    def fail_if_window_is_created(*_args):
        raise AssertionError("package smoke must not create MainWindow")

    monkeypatch.setattr(desktop_app, "QApplication", FakeQApplication)
    monkeypatch.setattr(desktop_app.MainWindow, "with_defaults", fail_if_window_is_created)
    monkeypatch.setenv("XFINAUDIO_PACKAGE_SMOKE", "1")
    monkeypatch.setenv("XFINAUDIO_DB_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("XFINAUDIO_SETTINGS_PATH", str(tmp_path / "settings.json"))

    macos_calls = []
    assert desktop_app.main(macos_configurator=lambda name, icon: macos_calls.append((name, icon))) == 0
    assert macos_calls == []


def test_main_resolves_default_macos_configurator_at_call_time(monkeypatch, tmp_path) -> None:
    from xfinaudio.desktop import app as desktop_app

    calls = []

    class FakeQApplication:
        def __init__(self, _argv):
            pass

        def setApplicationName(self, _name):
            pass

        def setApplicationDisplayName(self, _name):
            pass

        def exec(self):
            return 0

    class FakeWindow:
        def showMaximized(self):
            pass

        def windowState(self):
            return desktop_app.Qt.WindowState.WindowActive

        def setWindowState(self, _state):
            pass

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    monkeypatch.setattr(desktop_app, "_configure_macos_app", lambda name, icon: calls.append((name, icon)))
    monkeypatch.setattr(desktop_app, "QApplication", FakeQApplication)
    monkeypatch.setattr(desktop_app.MainWindow, "with_defaults", lambda *_args: FakeWindow())
    monkeypatch.delenv("XFINAUDIO_PACKAGE_SMOKE", raising=False)
    monkeypatch.setenv("XFINAUDIO_DB_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("XFINAUDIO_SETTINGS_PATH", str(tmp_path / "settings.json"))

    assert desktop_app.main() == 0
    assert calls and calls[0][0] == "XfinAudio"
