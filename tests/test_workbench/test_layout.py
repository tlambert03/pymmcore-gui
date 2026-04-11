from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest
from superqt import QIconifyIcon

from pymmcore_gui._layout import (
    PaneContainer,
    PanelAlignment,
    ViewContainerLocation,
    WorkbenchWidget,
    splitter_size,
)
from pymmcore_gui._qt.QtWidgets import QApplication, QSplitter

from ._helpers import _label, _sidebar_sizes, _test_icon

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

L = ViewContainerLocation
TOLERANCE = 4  # pixels — accounts for integer rounding and handle widths


class TestWorkbenchWidget:
    def test_initial_state(self, workbench: WorkbenchWidget) -> None:
        assert workbench.panelAlignment == PanelAlignment.CENTER
        assert workbench.leftSidebar.activityBar.activeItem == "explorer"
        assert workbench.rightSidebar.activityBar.activeItem == "properties"
        assert workbench.bottomPanel.activityBar.activeItem == "terminal"
        assert workbench._root_splitter is not None

    @pytest.mark.parametrize("alignment", list(PanelAlignment))
    def test_set_panel_alignment_rebuilds(
        self, workbench: WorkbenchWidget, alignment: PanelAlignment
    ) -> None:
        workbench.setPanelAlignment(alignment)
        assert workbench.panelAlignment == alignment
        assert workbench._root_splitter is not None

    def test_set_same_alignment_is_noop(self, workbench: WorkbenchWidget) -> None:
        old_splitter = workbench._root_splitter
        workbench.setPanelAlignment(PanelAlignment.CENTER)
        assert workbench._root_splitter is old_splitter

    def test_sidebar_toggle_emits_visibility_changed(
        self, workbench: WorkbenchWidget, qtbot: QtBot
    ) -> None:
        with qtbot.waitSignal(workbench.visibilityChanged):
            workbench.leftSidebar.activityBar.setActive("explorer")

    def test_toggle_panel(self, workbench: WorkbenchWidget, qtbot: QtBot) -> None:
        assert workbench.isPanelVisible
        with qtbot.waitSignal(workbench.visibilityChanged):
            workbench.togglePanel()
        assert not workbench.isPanelVisible

        with qtbot.waitSignal(workbench.visibilityChanged):
            workbench.togglePanel()
        assert workbench.isPanelVisible

    def test_sidebar_collapse_and_restore(self, workbench: WorkbenchWidget) -> None:
        left = workbench.leftSidebar
        left.collapse()
        assert left.activityBar.activeItem is None

        left.toggle()
        assert left.activityBar.activeItem is not None

    def test_alignment_switch_preserves_leaf_widgets(
        self, workbench: WorkbenchWidget
    ) -> None:
        """Leaf widgets must survive splitter tree rebuilds."""
        editor = workbench.centralWidget
        left_stack = workbench.leftSidebar.stack
        right_stack = workbench.rightSidebar.stack
        panel_stack = workbench.bottomPanel.stack

        for alignment in PanelAlignment:
            workbench.setPanelAlignment(alignment)
            assert editor.parent() is not None
            assert left_stack.parent() is not None
            assert right_stack.parent() is not None
            assert panel_stack.parent() is not None

    def test_toggle_actions_exist(self, workbench: WorkbenchWidget) -> None:
        assert workbench.toggleLeftSidebarAction is not None
        assert workbench.togglePanelAction is not None
        assert workbench.toggleRightSidebarAction is not None

    def test_action_icons_update(self, workbench: WorkbenchWidget) -> None:
        """setActionIcons + toggle cycle should not crash."""
        workbench.setActionIcons(
            workbench.toggleLeftSidebarAction,
            QIconifyIcon("codicon:layout-sidebar-left"),
            QIconifyIcon("codicon:layout-sidebar-left-off"),
        )
        workbench.toggleLeftSidebar()
        workbench.toggleLeftSidebar()

    def test_add_view_routes_to_correct_container(self, qtbot: QtBot) -> None:
        w = WorkbenchWidget()
        qtbot.addWidget(w)
        w.addView("a", "A", _label, icon=_test_icon(), location=L.LEFT_SIDEBAR)
        w.addView("b", "B", _label, icon=_test_icon(), location=L.RIGHT_SIDEBAR)
        w.addView("c", "C", _label, icon=_test_icon(), location=L.PANEL)
        assert "a" in w.leftSidebar.activityBar.itemIds
        assert "b" in w.rightSidebar.activityBar.itemIds
        assert "c" in w.bottomPanel.activityBar.itemIds

    def test_bottom_panel_uses_navigation_bar(self, workbench: WorkbenchWidget) -> None:
        from pymmcore_gui._layout import NavigationBarAdapter

        assert isinstance(workbench.bottomPanel, PaneContainer)
        assert isinstance(workbench.bottomPanel.activityBar, NavigationBarAdapter)

    def test_state_buttons(self, workbench: WorkbenchWidget) -> None:
        """stateButtons() returns a widget with 4 auto-raise buttons."""
        from pymmcore_gui._qt.QtWidgets import QToolButton

        w = workbench.stateButtons()
        buttons = w.findChildren(QToolButton)
        assert len(buttons) == 4
        assert all(b.autoRaise() for b in buttons)

    def test_state_buttons_creates_independent_instances(
        self, workbench: WorkbenchWidget
    ) -> None:
        w1 = workbench.stateButtons()
        w2 = workbench.stateButtons()
        assert w1 is not w2

    def test_cycle_panel_alignment(self, workbench: WorkbenchWidget) -> None:
        expected = [
            PanelAlignment.RIGHT,
            PanelAlignment.JUSTIFY,
            PanelAlignment.LEFT,
            PanelAlignment.CENTER,
        ]
        for align in expected:
            workbench.cyclePanelAlignment()
            assert workbench.panelAlignment == align


# ---- Splitter size stability tests ----------------------------------------


def test_switching_views_in_panel_does_not_resize(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Switching between views within the same container must not resize it."""
    wb = shown_workbench

    # Add a second view to the panel
    wb.addView("console", "Console", _label, icon=_test_icon(), location=L.PANEL)

    panel_w = wb.bottomPanel.splitterWidget
    h0 = splitter_size(panel_w)
    assert h0 > 0

    # Switch to the new view
    wb.bottomPanel.activityBar.setActive("console")
    h1 = splitter_size(panel_w)

    # Switch back
    wb.bottomPanel.activityBar.setActive("terminal")
    h2 = splitter_size(panel_w)

    assert h1 == h0, f"panel grew on first switch: {h0} -> {h1}"
    assert h2 == h0, f"panel grew on second switch: {h0} -> {h2}"


def test_alignment_cycle_no_drift(shown_workbench: WorkbenchWidget) -> None:
    """Cycling through all alignments and back should preserve sizes."""
    wb = shown_workbench
    left0, _, right0 = _sidebar_sizes(wb)

    alignments = list(PanelAlignment)
    for _ in range(3):
        for alignment in alignments:
            wb.setPanelAlignment(alignment)
            QApplication.processEvents()

    wb.setPanelAlignment(PanelAlignment.CENTER)
    QApplication.processEvents()
    left_after, _, right_after = _sidebar_sizes(wb)

    assert abs(left_after - left0) <= TOLERANCE, (
        f"left sidebar drifted: {left0} -> {left_after}"
    )
    assert abs(right_after - right0) <= TOLERANCE, (
        f"right sidebar drifted: {right0} -> {right_after}"
    )


def test_sidebar_toggle_preserves_other_sidebar(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Toggling one sidebar should not change the other sidebar's size."""
    wb = shown_workbench
    _, _, right0 = _sidebar_sizes(wb)

    for _ in range(5):
        wb.toggleLeftSidebar()
        wb.toggleLeftSidebar()

    _, _, right_after = _sidebar_sizes(wb)
    assert abs(right_after - right0) <= TOLERANCE, (
        f"right sidebar changed when toggling left: {right0} -> {right_after}"
    )


@pytest.mark.skipif(
    bool(sys.platform == "darwin" and os.getenv("CI")),
    reason="flaky on CI macOS runners",
)
def test_sidebar_toggle_restores_own_size(
    shown_workbench: WorkbenchWidget,
) -> None:
    """A sidebar should return to its original size after toggle cycle."""
    wb = shown_workbench
    left0, _, _ = _sidebar_sizes(wb)

    wb.toggleLeftSidebar()  # collapse
    wb.toggleLeftSidebar()  # restore

    left_after, _, _ = _sidebar_sizes(wb)
    assert abs(left_after - left0) <= TOLERANCE, (
        f"left sidebar size changed after toggle cycle: {left0} -> {left_after}"
    )


def test_panel_toggle_preserves_sidebar_sizes(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Toggling the bottom panel should not affect sidebar widths."""
    wb = shown_workbench
    left0, _, right0 = _sidebar_sizes(wb)

    for _ in range(5):
        wb.togglePanel()
        wb.togglePanel()

    left_after, _, right_after = _sidebar_sizes(wb)
    assert abs(left_after - left0) <= TOLERANCE, (
        f"left sidebar changed when toggling panel: {left0} -> {left_after}"
    )
    assert abs(right_after - right0) <= TOLERANCE, (
        f"right sidebar changed when toggling panel: {right0} -> {right_after}"
    )


def test_alignment_change_preserves_collapsed_state(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Changing panel alignment should not resurrect a collapsed sidebar."""
    wb = shown_workbench

    wb.toggleRightSidebar()
    QApplication.processEvents()
    assert wb.rightSidebar.isCollapsed

    wb.setPanelAlignment(PanelAlignment.RIGHT)
    QApplication.processEvents()

    right_w = wb.rightSidebar.splitterWidget
    assert splitter_size(right_w) == 0, (
        "collapsed right sidebar reappeared after alignment change"
    )

    wb.setPanelAlignment(PanelAlignment.CENTER)
    QApplication.processEvents()
    wb.toggleLeftSidebar()
    QApplication.processEvents()
    assert wb.leftSidebar.isCollapsed

    wb.setPanelAlignment(PanelAlignment.JUSTIFY)
    QApplication.processEvents()

    left_w = wb.leftSidebar.splitterWidget
    assert splitter_size(left_w) == 0, (
        "collapsed left sidebar reappeared after alignment change"
    )


def test_rapid_alignment_cycling_with_collapses(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Rapid alignment changes with collapsed parts must not corrupt state."""
    wb = shown_workbench

    wb.toggleRightSidebar()
    wb.togglePanel()
    QApplication.processEvents()

    for _ in range(3):
        for align in PanelAlignment:
            wb.setPanelAlignment(align)

    QApplication.processEvents()

    assert wb.rightSidebar.isCollapsed
    assert not wb.isPanelVisible
    assert not wb.leftSidebar.isCollapsed
    assert wb.leftSidebar.activityBar.activeItem is not None


def test_collapse_all_then_change_alignment(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Collapsing everything then changing alignment must not crash."""
    wb = shown_workbench

    wb.toggleLeftSidebar()
    wb.toggleRightSidebar()
    wb.togglePanel()
    QApplication.processEvents()

    for align in PanelAlignment:
        wb.setPanelAlignment(align)
        QApplication.processEvents()
        assert wb.leftSidebar.isCollapsed
        assert wb.rightSidebar.isCollapsed
        assert not wb.isPanelVisible


def test_drag_restore_does_not_disturb_other_sidebar(
    shown_workbench: WorkbenchWidget,
) -> None:
    """Drag-to-zero then drag-back should not shift other sidebar."""
    wb = shown_workbench
    left0, _, _ = _sidebar_sizes(wb)
    right_widget = wb.rightSidebar.splitterWidget
    parent = right_widget.parentWidget()
    assert parent is not None

    assert isinstance(parent, QSplitter)
    idx = parent.indexOf(right_widget)

    # Simulate drag to zero
    sizes = parent.sizes()
    freed = sizes[idx]
    editor_idx = wb._editor_index_in(parent)
    sizes[editor_idx] += freed
    sizes[idx] = 0
    parent.setSizes(sizes)
    wb._on_splitter_moved()

    assert wb.rightSidebar.activityBar.activeItem is None

    # Simulate drag back
    sizes = parent.sizes()
    restore_px = 150
    sizes[editor_idx] -= restore_px
    sizes[idx] = restore_px
    parent.setSizes(sizes)
    wb._on_splitter_moved()

    left_after, _, _ = _sidebar_sizes(wb)
    assert abs(left_after - left0) <= TOLERANCE, (
        f"left sidebar shifted during right drag-restore: {left0} -> {left_after}"
    )
