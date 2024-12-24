import sys
from unittest.mock import Mock

from PyQt6.QtWidgets import QApplication
from pytest import MonkeyPatch

from pymmcore_gui import _app


def test_main_app(monkeypatch: MonkeyPatch) -> None:
    mock_exec = Mock()
    monkeypatch.setattr(QApplication, "exec", mock_exec)
    monkeypatch.setattr(sys, "argv", ["mmgui"])
    _app.main()
    mock_exec.assert_called_once()
    assert isinstance(QApplication.instance(), _app.MMQApplication)
    assert sys.excepthook == _app.ndv_excepthook
    for wdg in QApplication.topLevelWidgets():
        wdg.close()
        wdg.deleteLater()