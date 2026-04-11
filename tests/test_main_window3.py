from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pymmcore_gui._layout import PanelAlignment
from pymmcore_gui._main_window3 import MicroManagerGUI

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytestqt.qtbot import QtBot


@pytest.fixture()
def gui(qtbot: QtBot) -> Iterator[MicroManagerGUI]:
    g = MicroManagerGUI()
    qtbot.addWidget(g)
    g.setMode("acquire")
    yield g


class TestMicroManagerGUI:
    def test_construction(self, gui: MicroManagerGUI) -> None:
        assert gui.windowTitle() == "pyMM"
        assert gui.acquire_mode is not None
        assert gui.configure_mode is not None

    def test_mode_switching(self, gui: MicroManagerGUI) -> None:
        gui._navigation.setCurrentIndex(0)
        assert gui._mode_stack.currentWidget() is gui.configure_mode

        gui._navigation.setCurrentIndex(1)
        assert gui._mode_stack.currentWidget() is gui.acquire_mode

    def test_toggle_left_sidebar(self, gui: MicroManagerGUI) -> None:
        gui.show()
        wb = gui.acquire_mode
        assert not wb.leftSidebar.isCollapsed

        wb.toggleLeftSidebar()
        assert wb.leftSidebar.activityBar.activeItem is None

        wb.toggleLeftSidebar()
        assert wb.leftSidebar.activityBar.activeItem is not None

    def test_toggle_right_sidebar(self, gui: MicroManagerGUI) -> None:
        gui.show()
        wb = gui.acquire_mode
        assert not wb.rightSidebar.isCollapsed

        wb.toggleRightSidebar()
        assert wb.rightSidebar.activityBar.activeItem is None

        wb.toggleRightSidebar()
        assert wb.rightSidebar.activityBar.activeItem is not None

    def test_toggle_panel(self, gui: MicroManagerGUI) -> None:
        gui.show()
        wb = gui.acquire_mode
        assert wb.isPanelVisible

        wb.togglePanel()
        assert not wb.isPanelVisible

        wb.togglePanel()
        assert wb.isPanelVisible

    def test_cycle_panel_alignment(self, gui: MicroManagerGUI) -> None:
        gui.show()
        wb = gui.acquire_mode
        expected_cycle = [
            PanelAlignment.RIGHT,
            PanelAlignment.JUSTIFY,
            PanelAlignment.LEFT,
            PanelAlignment.CENTER,
        ]
        for expected in expected_cycle:
            wb.cyclePanelAlignment()
            assert wb.panelAlignment == expected
