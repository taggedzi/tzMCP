from unittest.mock import Mock

from tzMCP import gui


def test_main_creates_and_runs_application(monkeypatch):
    app = Mock()
    monkeypatch.setattr(gui, "MainApp", lambda: app)

    gui.main()

    app.run.assert_called_once_with()
