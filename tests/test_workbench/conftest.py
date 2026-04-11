"""Pytest fixtures for workbench tests.

Plain helper functions live in ``_helpers.py`` next to this file.

These fixtures build the generic layout primitives (``ActivityBar``,
``PaneContainer``, ``WorkbenchWidget``) directly, without any
dependency on ``MicroManagerGUI`` or the app's placeholder view set.
This keeps the workbench test suite a self-contained exercise of the
layout pattern itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pymmcore_gui._layout import ActivityBar, PaneContainer, WorkbenchWidget
from pymmcore_gui._qt.QtCore import Qt
from pymmcore_gui._qt.QtWidgets import QApplication

from ._helpers import _label, _make_workbench

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture()
def activity_bar(qtbot: QtBot) -> ActivityBar:
    ab = ActivityBar()
    qtbot.addWidget(ab)
    return ab


@pytest.fixture()
def h_activity_bar(qtbot: QtBot) -> ActivityBar:
    ab = ActivityBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(ab)
    return ab


@pytest.fixture()
def container(qtbot: QtBot) -> PaneContainer:
    c = PaneContainer()
    qtbot.addWidget(c)
    c.addView("alpha", "Alpha", _label())
    c.addView("beta", "Beta", _label())
    return c


@pytest.fixture()
def workbench(qtbot: QtBot) -> WorkbenchWidget:
    w = _make_workbench()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    return w


@pytest.fixture()
def shown_workbench(qtbot: QtBot) -> WorkbenchWidget:
    """WorkbenchWidget shown and laid out so splitter sizes are meaningful."""
    w = _make_workbench()
    qtbot.addWidget(w)
    w.resize(1200, 800)
    w.show()
    qtbot.waitExposed(w)

    QApplication.processEvents()
    w._save_sizes()
    return w
