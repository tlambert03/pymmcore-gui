from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import pytest
from superqt import QIconifyIcon

from pymmcore_gui._layout import (
    ActivityBar,
    ActivityBarPosition,
    PaneContainer,
    PanelAlignment,
    ViewContainerLocation,
    ViewDescriptor,
    WorkbenchWidget,
    splitter_size,
)
from pymmcore_gui._main_window3 import MicroManagerGUI, _make_label
from pymmcore_gui._qt.QtCore import Qt
from pymmcore_gui._qt.QtGui import QIcon
from pymmcore_gui._qt.QtWidgets import QApplication, QSplitter

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytestqt.qtbot import QtBot

    from pymmcore_gui._qt.QtGui import QDropEvent
    from pymmcore_gui._qt.QtWidgets import QLabel

L = ViewContainerLocation


# ---- Fixtures -------------------------------------------------------------


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
def gui(qtbot: QtBot) -> Iterator[MicroManagerGUI]:
    g = MicroManagerGUI()
    qtbot.addWidget(g)
    g.setMode("acquire")
    yield g


def _label() -> QLabel:
    return _make_label("test")


def _test_icon() -> QIcon:
    """Return a small filled QIcon for tests that need a non-null icon.

    Avoids QIconifyIcon's network/cache dependency so tests are
    deterministic and offline-friendly.
    """
    from pymmcore_gui._qt.QtGui import QColor, QPixmap

    pix = QPixmap(16, 16)
    pix.fill(QColor("red"))
    return QIcon(pix)


def _make_workbench() -> WorkbenchWidget:
    """Create a WorkbenchWidget with minimal content for testing."""
    w = WorkbenchWidget()
    w.addView(
        "explorer", "Explorer", _label, icon=_test_icon(), location=L.LEFT_SIDEBAR
    )
    w.setActiveView("explorer")
    w.addView(
        "properties", "Properties", _label, icon=_test_icon(), location=L.RIGHT_SIDEBAR
    )
    w.setActiveView("properties")
    w.addView("terminal", "Terminal", _label, icon=_test_icon(), location=L.PANEL)
    w.setActiveView("terminal")
    return w


# ---- ActivityBar tests ----------------------------------------------------


class TestActivityBar:
    def test_add_panel(self, activity_bar: ActivityBar) -> None:
        btn = activity_bar.addItem("foo", "Foo")
        assert "foo" in activity_bar.itemIds
        assert btn.toolTip() == "Foo"
        assert btn.text() == "Foo"

    def test_default_orientation_is_vertical(self, activity_bar: ActivityBar) -> None:
        assert activity_bar.orientation == Qt.Orientation.Vertical

    def test_horizontal_orientation(self, h_activity_bar: ActivityBar) -> None:
        assert h_activity_bar.orientation == Qt.Orientation.Horizontal
        h_activity_bar.addItem("a", "A")
        h_activity_bar.addItem("b", "B")
        assert len(h_activity_bar.itemIds) == 2

    def test_set_active_emits_signal(
        self, activity_bar: ActivityBar, qtbot: QtBot
    ) -> None:
        activity_bar.addItem("a", "A")
        activity_bar.addItem("b", "B")

        with qtbot.waitSignal(activity_bar.itemToggled) as blocker:
            activity_bar.setActive("a")
        assert blocker.args == ["a"]
        assert activity_bar.activeItem == "a"

    def test_toggle_deactivates_when_collapsible(
        self, activity_bar: ActivityBar, qtbot: QtBot
    ) -> None:
        activity_bar.addItem("x", "X")
        activity_bar.setActive("x")
        assert activity_bar.activeItem == "x"

        with qtbot.waitSignal(activity_bar.itemToggled) as blocker:
            activity_bar.setActive("x")  # toggle off
        assert blocker.args == [""]
        assert activity_bar.activeItem is None

    def test_toggle_blocked_when_not_collapsible(
        self, activity_bar: ActivityBar
    ) -> None:
        activity_bar.addItem("x", "X")
        activity_bar.collapsible = False
        activity_bar.setActive("x")

        activity_bar.setActive("x")  # should NOT toggle off
        assert activity_bar.activeItem == "x"

    def test_deselect(self, activity_bar: ActivityBar) -> None:
        activity_bar.addItem("a", "A")
        activity_bar.setActive("a")
        assert activity_bar.activeItem == "a"

        activity_bar.deselect()
        assert activity_bar.activeItem is None

    def test_activate_first(self, activity_bar: ActivityBar, qtbot: QtBot) -> None:
        activity_bar.addItem("first", "First")
        activity_bar.addItem("second", "Second")

        with qtbot.waitSignal(activity_bar.itemToggled) as blocker:
            activity_bar.activateFirst()
        assert blocker.args == ["first"]
        assert activity_bar.activeItem == "first"

    def test_switching_panels(self, activity_bar: ActivityBar, qtbot: QtBot) -> None:
        activity_bar.addItem("a", "A")
        activity_bar.addItem("b", "B")
        activity_bar.setActive("a")

        with qtbot.waitSignal(activity_bar.itemToggled) as blocker:
            activity_bar.setActive("b")
        assert blocker.args == ["b"]
        assert activity_bar.activeItem == "b"


# ---- PaneContainer tests -------------------------------------------------


class TestPaneContainer:
    def test_add_panel_adds_to_stack(self, container: PaneContainer) -> None:
        assert container.stack.count() == 2
        assert "alpha" in container.activityBar.itemIds
        assert "beta" in container.activityBar.itemIds

    def test_panel_toggled_forwarded(
        self, container: PaneContainer, qtbot: QtBot
    ) -> None:
        with qtbot.waitSignal(container.viewToggled) as blocker:
            container.activityBar.setActive("alpha")
        assert blocker.args == ["alpha"]

    def test_toggle_collapse_and_restore(self, container: PaneContainer) -> None:
        container.activityBar.setActive("alpha")
        assert container.activityBar.activeItem == "alpha"

        container.collapse()
        assert container.activityBar.activeItem is None

    def test_toggle_method(self, container: PaneContainer) -> None:
        container.activityBar.setActive("alpha")
        container.splitterWidget.show()
        container.toggle()  # should collapse
        assert container.activityBar.activeItem is None

    def test_ab_position_default(self, container: PaneContainer) -> None:
        assert container.resolvedAbPosition == "side"
        assert container.isAbExternal is True

    def test_ab_position_top(self, container: PaneContainer) -> None:
        container.setAbPosition(ActivityBarPosition.TOP)
        assert container.resolvedAbPosition == "top"
        assert container.isAbExternal is False
        assert container.splitterWidget is container._combined

    def test_ab_position_hidden(self, container: PaneContainer) -> None:
        container.setAbPosition(ActivityBarPosition.HIDDEN)
        container.arrange()
        assert not container.activityBar.isVisible()

    def test_ab_position_changed_signal(
        self, container: PaneContainer, qtbot: QtBot
    ) -> None:
        container.setAbPosition(ActivityBarPosition.BOTTOM)
        container._ab_position = ActivityBarPosition.DEFAULT  # reset
        with qtbot.waitSignal(container.abPositionChanged) as blocker:
            container.abPositionChanged.emit(ActivityBarPosition.BOTTOM)
        assert blocker.args == [ActivityBarPosition.BOTTOM]

    def test_restore_from_drag(self, container: PaneContainer) -> None:
        container.deselect()
        assert container.activityBar.activeItem is None

        container.restoreFromDrag()
        assert container.activityBar.activeItem == "alpha"

    def test_arrange_side(self, container: PaneContainer) -> None:
        container.setAbPosition(ActivityBarPosition.DEFAULT)
        container.arrange()
        assert container.activityBar.collapsible is True
        assert container.activityBar.isVisible()

    def test_arrange_top(self, container: PaneContainer) -> None:
        container.setAbPosition(ActivityBarPosition.TOP)
        container.arrange()
        assert container.activityBar.collapsible is False
        assert container.activityBar.parent() is container._combined

    def test_top_position_uses_navigation_bar(self, qtbot: QtBot) -> None:
        from pymmcore_gui._layout import NavigationBarAdapter

        c = PaneContainer(default_ab_position="top")
        qtbot.addWidget(c)
        c.addView("a", "A", _label())
        c.addView("b", "B", _label())
        # top position → horizontal → NavigationBarAdapter
        assert isinstance(c.activityBar, NavigationBarAdapter)
        assert len(c.activityBar.itemIds) == 2

    def test_side_position_uses_activity_bar(self, container: PaneContainer) -> None:
        # Default is "side" → vertical → ActivityBar
        assert isinstance(container.activityBar, ActivityBar)


# ---- WorkbenchWidget tests ------------------------------------------------


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


# ---- MicroManagerGUI tests ------------------------------------------------


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


# ---- Splitter size stability tests ----------------------------------------

TOLERANCE = 4  # pixels — accounts for integer rounding and handle widths


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


def _sidebar_sizes(wb: WorkbenchWidget) -> tuple[int, int, int]:
    """Return (left_width, editor_width, right_width) from actual geometry."""
    left = wb.leftSidebar.splitterWidget
    right = wb.rightSidebar.splitterWidget
    editor = wb.centralWidget
    return left.width(), editor.width(), right.width()


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


# ---- DnD Phase A: ActivityBar drag source + drop target ------------------
#
# These tests exercise the Phase A drop handler by building a QDropEvent
# directly and calling ActivityBar.dropEvent() on it, bypassing Qt's native
# drag loop (which is synchronous and modal and can't be driven from a test).
# That's the standard Qt DnD testing pattern — it verifies drop-side logic
# in isolation from the platform-dependent drag-start machinery.


def _make_drop_event(view_id: str, pos: tuple[int, int]) -> QDropEvent:
    """Build a QDropEvent carrying *view_id* at local position *pos*.

    Note: ``QDropEvent`` does not take ownership of its ``QMimeData``,
    so we attach it to the event object as an attribute to keep the
    Python reference alive until the caller is done with the event.
    Otherwise the C++ QMimeData is destroyed when this function returns
    and the subsequent ``e.mimeData()`` access segfaults.
    """
    from pymmcore_gui._layout._dnd import PMM_VIEW_MIME_TYPE, encode_view_id
    from pymmcore_gui._qt.QtCore import QEvent, QMimeData, QPointF
    from pymmcore_gui._qt.QtCore import Qt as _Qt
    from pymmcore_gui._qt.QtGui import QDropEvent

    mime = QMimeData()
    mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id(view_id))
    evt = QDropEvent(
        QPointF(*pos),
        _Qt.DropAction.MoveAction,
        mime,
        _Qt.MouseButton.LeftButton,
        _Qt.KeyboardModifier.NoModifier,
        QEvent.Type.Drop,
    )
    evt._keep_alive = mime
    return evt


def _dnd_workbench(qtbot: QtBot) -> WorkbenchWidget:
    """Isolated WorkbenchWidget with exactly three left-sidebar views and
    two panel views. Built directly (not via MicroManagerGUI) so the test
    environment is stable under changes to the real placeholder view set.
    Shown via ``w.show()`` so the activity bar has real button geometries.
    """
    w = WorkbenchWidget(central=_label())
    qtbot.addWidget(w)
    for vid in ("explorer", "search", "debug"):
        w.registerView(
            ViewDescriptor(
                id=vid,
                name=vid.title(),
                factory=_label,
                icon=_test_icon(),
                default_location=L.LEFT_SIDEBAR,
            )
        )
    for vid in ("terminal", "console"):
        w.registerView(
            ViewDescriptor(
                id=vid,
                name=vid.title(),
                factory=_label,
                icon=_test_icon(),
                default_location=L.PANEL,
            )
        )
    w.show()
    qtbot.waitExposed(w)
    return w


class TestActivityBarDrop:
    def test_drop_different_container_at_front(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        first_rect = next(iter(ab._buttons.values())).geometry()
        drop_pos = (first_rect.center().x(), first_rect.y() + 1)

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds[0] == "terminal"
        assert wb.bottomPanel.viewIds == ["console"]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_drop_different_container_at_middle(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        btns = list(ab._buttons.values())
        # Drop just above the second button's midpoint → insert at index 1
        second_rect = btns[1].geometry()
        drop_pos = (second_rect.center().x(), second_rect.y() + 1)

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds == [
            "explorer",
            "terminal",
            "search",
            "debug",
        ]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_drop_different_container_at_end(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        last_rect = list(ab._buttons.values())[-1].geometry()
        drop_pos = (
            last_rect.center().x(),
            last_rect.y() + last_rect.height() + 10,
        )

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds[-1] == "terminal"

    def test_reorder_within_same_container(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        # Drop "debug" (currently at index 2) above "search" (index 1)
        btns = list(ab._buttons.values())
        search_rect = btns[1].geometry()
        drop_pos = (search_rect.center().x(), search_rect.y() + 1)

        ab.dropEvent(_make_drop_event("debug", drop_pos))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds == ["explorer", "debug", "search"]

    def test_reorder_forward_gap_compensates(self, qtbot: QtBot) -> None:
        """Regression guard: dragging an item to a gap *after* its
        current position must land it in that gap, not past it.

        Bug was: dropping explorer (index 0) between search (1) and
        debug (2) landed it at the END ([search, debug, explorer])
        because the registry interprets the drop index against the
        post-remove list, but the drop handler was computing it
        against the pre-move visual. The drop handler now compensates
        by subtracting 1 when the moved item was before the target.
        """
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        # Start: [explorer, search, debug]
        # Drop explorer (index 0) between search (index 1) and debug
        # (index 2). The drop indicator reports visual gap index 2.
        btns = list(ab._buttons.values())
        debug_rect = btns[2].geometry()
        drop_pos = (debug_rect.center().x(), debug_rect.y() + 1)

        ab.dropEvent(_make_drop_event("explorer", drop_pos))
        qtbot.wait(10)

        # Explorer must land BETWEEN search and debug, not after.
        assert wb.leftSidebar.viewIds == ["search", "explorer", "debug"]

    def test_drop_unknown_mime_is_ignored(self, qtbot: QtBot) -> None:
        from pymmcore_gui._qt.QtCore import QEvent, QMimeData, QPointF
        from pymmcore_gui._qt.QtCore import Qt as _Qt
        from pymmcore_gui._qt.QtGui import QDropEvent

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        before = list(wb.leftSidebar.viewIds)

        mime = QMimeData()
        mime.setText("not a view id")
        evt = QDropEvent(
            QPointF(10, 10),
            _Qt.DropAction.MoveAction,
            mime,
            _Qt.MouseButton.LeftButton,
            _Qt.KeyboardModifier.NoModifier,
            QEvent.Type.Drop,
        )
        ab.dropEvent(evt)
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds == before

    def test_drop_unknown_view_id_is_ignored(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        before_left = list(wb.leftSidebar.viewIds)
        before_panel = list(wb.bottomPanel.viewIds)

        ab.dropEvent(_make_drop_event("does-not-exist", (10, 10)))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds == before_left
        assert wb.bottomPanel.viewIds == before_panel

    def test_drop_of_pinned_view_is_ignored(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        wb.registerView(
            ViewDescriptor(
                id="pinned",
                name="Pinned",
                factory=_label,
                icon=_test_icon(),
                default_location=L.PANEL,
                can_move=False,
            )
        )
        ab = wb.leftSidebar.activityBar
        first_rect = next(iter(ab._buttons.values())).geometry()
        drop_pos = (first_rect.center().x(), first_rect.y() + 1)

        ab.dropEvent(_make_drop_event("pinned", drop_pos))
        qtbot.wait(10)

        # Pinned view stays in its original container.
        assert "pinned" not in wb.leftSidebar.viewIds
        assert "pinned" in wb.bottomPanel.viewIds
        assert wb.registry.get_view_location("pinned") == L.PANEL

    def test_drop_preserves_active_view_in_source(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        # Activate console in the bottom panel, then drag terminal out.
        wb.bottomPanel.activityBar.setActive("console")
        ab = wb.leftSidebar.activityBar
        first_rect = next(iter(ab._buttons.values())).geometry()
        drop_pos = (first_rect.center().x(), first_rect.y() + 1)

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)

        # Console should still be active in the panel.
        assert wb.bottomPanel.activityBar.activeItem == "console"

    def test_compute_insert_index_vertical(self, qtbot: QtBot) -> None:
        """Unit test of the hit-test math in isolation."""
        from pymmcore_gui._qt.QtCore import QPoint

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        btns = list(ab._buttons.values())
        x_center = btns[0].geometry().center().x()

        # Above all items → index 0
        assert ab._compute_insert_index(QPoint(x_center, -5)) == 0
        # Top of first item (above its midpoint) → index 0
        first_top = btns[0].geometry().y() + 1
        assert ab._compute_insert_index(QPoint(x_center, first_top)) == 0
        # Bottom half of first → index 1
        first_bottom = btns[0].geometry().y() + btns[0].geometry().height() - 1
        assert ab._compute_insert_index(QPoint(x_center, first_bottom)) == 1
        # Past everything → count
        past = btns[-1].geometry().y() + btns[-1].geometry().height() + 100
        assert ab._compute_insert_index(QPoint(x_center, past)) == len(btns)

    def test_reorder_of_active_view_keeps_stack_in_sync(self, qtbot: QtBot) -> None:
        """Regression guard: reordering the currently-active view via
        drop must not desynchronize the QStackedWidget's currentWidget
        from the ActivityBar's activeItem.

        Root cause: ``QStackedWidget.removeWidget(w)`` picks a new
        currentWidget if *w* was the current one. ``PaneContainer.
        reorderView`` must restore it after re-inserting.
        """
        wb = _dnd_workbench(qtbot)
        wb.leftSidebar.activityBar.setActive("explorer")
        assert (
            wb.leftSidebar.stack.currentWidget()
            is wb.leftSidebar._views["explorer"].widget
        )

        # Reorder explorer to the end via the registry (same path DnD uses)
        wb.registry.reorder_view("explorer", 2)

        assert wb.leftSidebar.activityBar.activeItem == "explorer"
        assert wb.leftSidebar.viewIds == ["search", "debug", "explorer"]
        # The crucial assertion: stack and bar must still agree.
        assert (
            wb.leftSidebar.stack.currentWidget()
            is wb.leftSidebar._views["explorer"].widget
        )

    def test_reorder_of_non_active_view_does_not_touch_current(
        self, qtbot: QtBot
    ) -> None:
        """Reordering a view that *isn't* the current one must not
        change what the stack is showing."""
        wb = _dnd_workbench(qtbot)
        wb.leftSidebar.activityBar.setActive("search")
        search_widget = wb.leftSidebar._views["search"].widget
        assert wb.leftSidebar.stack.currentWidget() is search_widget

        wb.registry.reorder_view("explorer", 2)

        # search is still the current view — its widget identity is
        # stable across the reorder.
        assert wb.leftSidebar.activityBar.activeItem == "search"
        assert wb.leftSidebar.stack.currentWidget() is search_widget

    def test_drop_indicator_visibility_lifecycle(self, qtbot: QtBot) -> None:
        """Drop indicator should be hidden at rest, visible while a
        drag is over the bar, and hidden again on leave."""
        from pymmcore_gui._layout._dnd import (
            PMM_VIEW_MIME_TYPE,
            encode_view_id,
        )
        from pymmcore_gui._qt.QtCore import QMimeData
        from pymmcore_gui._qt.QtGui import QDragEnterEvent, QDragLeaveEvent

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        indicator = ab._drop_indicator

        assert not indicator.isVisible()

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("terminal"))
        first_btn_center = next(iter(ab._buttons.values())).geometry().center()
        enter = QDragEnterEvent(
            first_btn_center,
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        ab.dragEnterEvent(enter)
        qtbot.wait(10)
        assert indicator.isVisible()

        leave = QDragLeaveEvent()
        ab.dragLeaveEvent(leave)
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_drop_indicator_hidden_after_drop(self, qtbot: QtBot) -> None:
        """After a successful drop, the indicator is hidden."""
        from pymmcore_gui._layout._dnd import (
            PMM_VIEW_MIME_TYPE,
            encode_view_id,
        )
        from pymmcore_gui._qt.QtCore import QMimeData
        from pymmcore_gui._qt.QtGui import QDragEnterEvent

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        indicator = ab._drop_indicator

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("terminal"))
        pos = next(iter(ab._buttons.values())).geometry().center()
        enter = QDragEnterEvent(
            pos,
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        ab.dragEnterEvent(enter)
        assert indicator.isVisible()

        ab.dropEvent(_make_drop_event("terminal", (pos.x(), pos.y())))
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_drop_indicator_position_at_extremes(self, qtbot: QtBot) -> None:
        """Indicator position at index=0, index=count, and middle."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        btns = list(ab._buttons.values())
        assert len(btns) >= 3

        pos_0 = ab._drop_indicator_position(0)
        assert pos_0 == btns[0].geometry().y()

        pos_end = ab._drop_indicator_position(len(btns))
        last = btns[-1].geometry()
        assert pos_end == last.y() + last.height()

        pos_1 = ab._drop_indicator_position(1)
        assert btns[0].geometry().y() < pos_1
        assert pos_1 < btns[1].geometry().y() + btns[1].geometry().height()

    def test_drag_source_eventfilter_survives_button_deletion(
        self, qtbot: QtBot
    ) -> None:
        """Regression guard: during a cross-container drag from the
        left ActivityBar, the drop fires the signal chain → registry
        move → source container's ``removeView`` → ``ActivityBar.
        removeItem(view_id)`` → ``btn.deleteLater()``. When
        ``_start_drag``'s ``drag.exec`` returns, ``eventFilter`` must
        not then access or forward the now-deleted button to
        ``super().eventFilter``.

        Simulated by monkey-patching ``_start_drag`` to remove the
        pressed button (same net effect as the real drag-drop flow).
        """
        from pymmcore_gui._qt.QtCore import QEvent, QPointF
        from pymmcore_gui._qt.QtGui import QMouseEvent

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        btn = next(iter(ab._buttons.values()))
        view_id = btn.objectName()

        def fake_start_drag(vid: str) -> None:
            # Mimic the real drop chain: remove the item while the
            # event filter is mid-execution, then return.
            ab.removeItem(vid)

        ab._start_drag = fake_start_drag  # type: ignore[method-assign]

        # Simulate a press on the button followed by a move past the
        # drag threshold. The move's event filter will call _start_drag,
        # which deletes the button. The event filter must not crash.
        press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(5, 5),
            QPointF(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        ab.eventFilter(btn, press)

        drag_distance = QApplication.startDragDistance() + 5
        move = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(5 + drag_distance, 5 + drag_distance),
            QPointF(5 + drag_distance, 5 + drag_distance),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        result = ab.eventFilter(btn, move)
        qtbot.wait(10)

        # The move should have been consumed (return True) and the
        # button must have been removed without raising.
        assert result is True
        assert view_id not in ab.itemIds

    def test_drag_source_eventfilter_fires_on_button_press(self, qtbot: QtBot) -> None:
        """Regression guard for the Qt event-dispatch gotcha: mouse events
        delivered to a QToolButton child are eaten by the button and never
        propagate to the parent ActivityBar's mousePressEvent. The fix is
        an event filter installed on each button; this test verifies it
        captures the press and records a drag candidate.
        """

        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        btns = list(ab._buttons.values())

        assert ab._drag_candidate_id is None

        qtbot.mousePress(btns[1], Qt.MouseButton.LeftButton)  # type: ignore[no-untyped-call]
        qtbot.wait(10)
        assert ab._drag_candidate_id == btns[1].objectName()
        assert ab._drag_start_pos is not None

        # Releasing without moving clears the candidate.
        qtbot.mouseRelease(btns[1], Qt.MouseButton.LeftButton)  # type: ignore[no-untyped-call]
        qtbot.wait(10)
        assert ab._drag_candidate_id is None


# ---- DnD Phase B: NavigationBarAdapter drag source + drop target ---------


class TestNavigationBarDrop:
    def test_drop_onto_bottom_panel_from_left_sidebar(self, qtbot: QtBot) -> None:
        """Drop a view from the left sidebar onto the bottom panel via
        the NavigationBarAdapter's Phase B drop handler."""
        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav  # inner _DraggableNavigationBar

        # Drop explorer at the very front of the panel bar
        nav.dropEvent(_make_drop_event("explorer", (0, 10)))
        qtbot.wait(10)

        assert "explorer" in wb.bottomPanel.viewIds
        assert "explorer" not in wb.leftSidebar.viewIds
        assert wb.registry.get_view_location("explorer") == L.PANEL
        assert wb.bottomPanel.viewIds[0] == "explorer"

    def test_drop_onto_bottom_panel_at_end(self, qtbot: QtBot) -> None:
        """Drop past all items → append to the bottom panel."""
        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav
        nav.dropEvent(_make_drop_event("explorer", (10000, 10)))
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds[-1] == "explorer"

    def test_drop_unknown_mime_on_navigation_bar_is_ignored(self, qtbot: QtBot) -> None:
        from pymmcore_gui._qt.QtCore import QEvent, QMimeData, QPointF
        from pymmcore_gui._qt.QtCore import Qt as _Qt
        from pymmcore_gui._qt.QtGui import QDropEvent

        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav
        before = list(wb.bottomPanel.viewIds)

        mime = QMimeData()
        mime.setText("not a view id")
        evt = QDropEvent(
            QPointF(0, 10),
            _Qt.DropAction.MoveAction,
            mime,
            _Qt.MouseButton.LeftButton,
            _Qt.KeyboardModifier.NoModifier,
            QEvent.Type.Drop,
        )
        evt._keep_alive = mime
        nav.dropEvent(evt)
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == before

    def test_navigation_bar_drag_source_records_candidate(self, qtbot: QtBot) -> None:
        """The mouse-press override on _DraggableNavigationBar records
        a drag candidate based on itemAtPos."""
        from pymmcore_gui._qt.QtCore import QPoint

        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav

        # Find a point well inside the second item's rect via the
        # itemAtPos scan — more robust than hardcoding pixels.
        mid_y = nav.height() // 2
        target_idx = 1  # second item = "console"
        target_pos = None
        for x in range(nav.width()):
            if nav.itemAtPos(QPoint(x, mid_y)) == target_idx:
                target_pos = QPoint(x + 2, mid_y)
                break
        assert target_pos is not None, "could not locate item 1 on the bar"

        assert nav._drag_candidate_index == -1

        qtbot.mousePress(nav, Qt.MouseButton.LeftButton, pos=target_pos)  # type: ignore[no-untyped-call]
        qtbot.wait(10)
        assert nav._drag_candidate_index == target_idx

        qtbot.mouseRelease(nav, Qt.MouseButton.LeftButton, pos=target_pos)  # type: ignore[no-untyped-call]
        qtbot.wait(10)
        assert nav._drag_candidate_index == -1

    def test_cross_container_move_clears_source_ghost(self, qtbot: QtBot) -> None:
        """Issue 1 regression: after dragging the active view out of a
        container, the source container's stack must not still show
        the ghost of a sibling widget.
        """
        wb = _dnd_workbench(qtbot)
        # Activate "terminal" in the bottom panel — it becomes current.
        wb.bottomPanel.activityBar.setActive("terminal")
        terminal_widget = wb.bottomPanel._views["terminal"].widget
        assert wb.bottomPanel.stack.currentWidget() is terminal_widget
        assert wb.bottomPanel.activityBar.activeItem == "terminal"

        # Drop terminal onto the left sidebar → moves it out of the panel.
        ab = wb.leftSidebar.activityBar
        first_rect = next(iter(ab._buttons.values())).geometry()
        drop_pos = (first_rect.center().x(), first_rect.y() + 1)
        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)

        # Panel should now contain only "console", and crucially:
        #   activeItem == "console" (not None)
        #   stack.currentWidget() == console's widget
        assert wb.bottomPanel.viewIds == ["console"]
        assert wb.bottomPanel.activityBar.activeItem == "console"
        console_widget = wb.bottomPanel._views["console"].widget
        assert wb.bottomPanel.stack.currentWidget() is console_widget

    def test_cross_container_move_empty_source_leaves_no_active(
        self, qtbot: QtBot
    ) -> None:
        """Draining a container must not crash trying to auto-activate
        a non-existent sibling."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        first_rect = next(iter(ab._buttons.values())).geometry()
        drop_pos = (first_rect.center().x(), first_rect.y() + 1)

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)
        ab.dropEvent(_make_drop_event("console", drop_pos))
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == []
        assert wb.bottomPanel.activityBar.activeItem is None

    def test_drop_on_content_area_appends_to_container(self, qtbot: QtBot) -> None:
        """Dropping on the big content widget under the tab bar
        should count as "drop into this container, at the end".
        Fixes the 'drop hitbox too small' complaint.
        """
        wb = _dnd_workbench(qtbot)
        stack = wb.bottomPanel.stack
        before = list(wb.bottomPanel.viewIds)

        stack.dropEvent(_make_drop_event("explorer", (50, 50)))
        qtbot.wait(50)  # let QTimer.singleShot(0, ...) fire

        assert wb.bottomPanel.viewIds == [*before, "explorer"]
        assert wb.registry.get_view_location("explorer") == L.PANEL

    def test_drop_on_sidebar_stack_appends_to_left_sidebar(self, qtbot: QtBot) -> None:
        """Same as test_drop_on_content_area_appends_to_container
        but for the ActivityBar/side position — the left sidebar's
        stack widget should also accept drops.
        """
        wb = _dnd_workbench(qtbot)
        stack = wb.leftSidebar.stack
        before = list(wb.leftSidebar.viewIds)

        stack.dropEvent(_make_drop_event("terminal", (80, 80)))
        qtbot.wait(50)

        assert wb.leftSidebar.viewIds == [*before, "terminal"]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_nav_drop_indicator_visibility(self, qtbot: QtBot) -> None:
        """Indicator on the inner nav bar shows/hides across the drag
        lifecycle; at rest it's hidden."""
        from pymmcore_gui._layout._dnd import (
            PMM_VIEW_MIME_TYPE,
            encode_view_id,
        )
        from pymmcore_gui._qt.QtCore import QMimeData
        from pymmcore_gui._qt.QtGui import QDragEnterEvent, QDragLeaveEvent

        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav
        indicator = nav._drop_indicator

        assert not indicator.isVisible()

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("explorer"))
        # Drop cursor roughly in the middle of the first item
        first_rect = nav.itemRect(0)
        enter = QDragEnterEvent(
            first_rect.center(),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        nav.dragEnterEvent(enter)
        qtbot.wait(10)
        assert indicator.isVisible()

        nav.dragLeaveEvent(QDragLeaveEvent())
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_nav_drop_indicator_stretch_area_at_end(self, qtbot: QtBot) -> None:
        """Drag entering the adapter's stretch area (outside the inner
        nav) should show the indicator on the inner nav at the very
        right edge — the position where an append would land."""
        from pymmcore_gui._layout import NavigationBarAdapter
        from pymmcore_gui._layout._dnd import (
            PMM_VIEW_MIME_TYPE,
            encode_view_id,
        )
        from pymmcore_gui._qt.QtCore import QMimeData, QPoint
        from pymmcore_gui._qt.QtGui import QDragEnterEvent

        wb = _dnd_workbench(qtbot)
        adapter = wb.bottomPanel.activityBar
        assert isinstance(adapter, NavigationBarAdapter)
        nav = adapter._nav
        indicator = nav._drop_indicator

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("explorer"))
        # A position in the adapter (stretch area) — doesn't have to
        # match the inner nav's geometry; the adapter's handler always
        # passes itemCount() to showDropIndicatorAt.
        enter = QDragEnterEvent(
            QPoint(nav.width() + 20, 10),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        adapter.dragEnterEvent(enter)
        qtbot.wait(10)

        assert indicator.isVisible()
        # The indicator was positioned at the end-of-items x coordinate
        end_x = nav._drop_indicator_x(nav.itemCount())
        half = indicator.THICKNESS // 2
        assert indicator.geometry().x() == end_x - half

    def test_nav_reorder_forward_gap_compensates(self, qtbot: QtBot) -> None:
        """Same bug as test_reorder_forward_gap_compensates but on
        the horizontal NavigationBar path. The drop handler's
        pre-move → post-move index conversion must also work when
        the target container's bar is a NavigationBarAdapter.
        """

        wb = _dnd_workbench(qtbot)
        # Add a third panel view so we have [terminal, console, output]
        # and can drop terminal between console and output.
        wb.registerView(
            ViewDescriptor(
                id="output",
                name="Output",
                factory=_label,
                icon=_test_icon(),
                default_location=L.PANEL,
            )
        )
        qtbot.wait(10)
        assert wb.bottomPanel.viewIds == ["terminal", "console", "output"]

        nav = wb.bottomPanel.activityBar._nav
        # Find a point inside the "output" item (index 2) that's in
        # its left half — the drop indicator will report gap index 2.
        output_rect = nav.itemRect(2)
        drop_x = output_rect.x() + 2  # just inside, left half
        drop_pos = (drop_x, nav.height() // 2)

        nav.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(50)

        # Terminal should land between console and output, not after.
        assert wb.bottomPanel.viewIds == ["console", "terminal", "output"]

    def test_drop_on_nav_adapter_stretch_area_appends(self, qtbot: QtBot) -> None:
        """Regression for the dead zone to the right of the last tab.

        The inner ``_DraggableNavigationBar`` only covers the width
        of its items; the empty stretch region inside the
        ``NavigationBarAdapter`` is a separate area. Drops there
        must still work (append to end).
        """
        from pymmcore_gui._layout import NavigationBarAdapter

        wb = _dnd_workbench(qtbot)
        adapter = wb.bottomPanel.activityBar
        assert isinstance(adapter, NavigationBarAdapter)
        before = list(wb.bottomPanel.viewIds)

        # Fire the drop on the *adapter* itself (not its inner bar).
        # In a live GUI, Qt dispatches to the adapter when the cursor
        # is in the stretch region because the inner bar isn't under
        # the cursor there.
        adapter.dropEvent(_make_drop_event("explorer", (0, 0)))
        qtbot.wait(50)

        assert wb.bottomPanel.viewIds == [*before, "explorer"]
        assert wb.registry.get_view_location("explorer") == L.PANEL

    def test_nav_display_mode_default_is_text_only(self, qtbot: QtBot) -> None:
        """Horizontal (top/bottom) nav bars default to TEXT_ONLY —
        labels are the primary affordance in a tab strip."""
        from pymmcore_gui._layout import NavigationBarAdapter
        from pymmcore_gui._layout._enums import NavDisplayMode

        wb = _dnd_workbench(qtbot)
        nav_adapter = wb.bottomPanel.activityBar
        assert isinstance(nav_adapter, NavigationBarAdapter)
        assert nav_adapter.displayMode == NavDisplayMode.TEXT_ONLY
        inner = nav_adapter._nav
        assert inner.getItemText(0) == "Terminal"
        assert inner.getItemIcon(0).isNull()

    def test_nav_display_mode_switches(self, qtbot: QtBot) -> None:
        """Cycling display mode rewrites every slot's text/icon.

        Uses the cached metadata as the source of truth so the change
        is reversible across all three modes.
        """
        from pymmcore_gui._layout import NavigationBarAdapter
        from pymmcore_gui._layout._enums import NavDisplayMode

        wb = _dnd_workbench(qtbot)
        nav_adapter = wb.bottomPanel.activityBar
        assert isinstance(nav_adapter, NavigationBarAdapter)
        inner = nav_adapter._nav

        # Start from BOTH explicitly so the test is independent of
        # whatever default PaneContainer chooses.
        nav_adapter.setDisplayMode(NavDisplayMode.BOTH)
        assert inner.getItemText(0) == "Terminal"
        assert not inner.getItemIcon(0).isNull()

        # Icons only: text cleared, icon preserved
        nav_adapter.setDisplayMode(NavDisplayMode.ICONS_ONLY)
        assert inner.getItemText(0) == ""
        assert not inner.getItemIcon(0).isNull()

        # Text only: text preserved, icon cleared
        nav_adapter.setDisplayMode(NavDisplayMode.TEXT_ONLY)
        assert inner.getItemText(0) == "Terminal"
        assert inner.getItemIcon(0).isNull()

        # Flip back to both: cache is the source of truth, fully reversible
        nav_adapter.setDisplayMode(NavDisplayMode.BOTH)
        assert inner.getItemText(0) == "Terminal"
        assert not inner.getItemIcon(0).isNull()

    def test_nav_display_mode_survives_bar_swap(self, qtbot: QtBot) -> None:
        """Toggling the activity bar position destroys the nav
        adapter and creates a fresh one. The container stores the
        display mode preference so it's reapplied on recreation.
        """
        from pymmcore_gui._layout import NavigationBarAdapter
        from pymmcore_gui._layout._enums import (
            ActivityBarPosition,
            NavDisplayMode,
        )

        wb = _dnd_workbench(qtbot)
        panel = wb.bottomPanel
        nav_adapter = panel.activityBar
        assert isinstance(nav_adapter, NavigationBarAdapter)

        nav_adapter.setDisplayMode(NavDisplayMode.ICONS_ONLY)
        panel._nav_display_mode = NavDisplayMode.ICONS_ONLY

        # Swap to side (which uses vertical ActivityBar, not a nav bar)
        # and back to top. The new NavigationBarAdapter should apply
        # the remembered display mode.
        panel.setAbPosition(ActivityBarPosition.HIDDEN)
        panel.arrange()
        panel.setAbPosition(ActivityBarPosition.TOP)
        panel.arrange()

        new_adapter = panel.activityBar
        assert isinstance(new_adapter, NavigationBarAdapter)
        assert new_adapter.displayMode == NavDisplayMode.ICONS_ONLY
        inner = new_adapter._nav
        if inner.itemCount() > 0:
            assert inner.getItemText(0) == ""
            assert not inner.getItemIcon(0).isNull()

    def test_click_to_switch_view_on_nav_bar(self, qtbot: QtBot) -> None:
        """Regression guard for the click-to-switch bug.

        When ``_DraggableNavigationBar`` overrides ``mousePressEvent``
        and ``mouseReleaseEvent`` and calls ``super()``, those super
        calls must dispatch through to qlementine's C++ implementations
        in ``AbstractItemListWidget`` — not silently walk the Python
        MRO up to ``QWidget``'s no-op defaults. The dispatch only
        works if those virtuals are declared in
        ``AbstractItemListWidget.sip``.
        """
        from pymmcore_gui._qt.QtCore import QPoint

        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav

        assert wb.bottomPanel.activityBar.activeItem == "terminal"

        # Find a point inside the "console" item (index 1)
        mid_y = nav.height() // 2
        target_pos = None
        for x in range(nav.width()):
            if nav.itemAtPos(QPoint(x, mid_y)) == 1:
                target_pos = QPoint(x + 5, mid_y)
                break
        assert target_pos is not None

        qtbot.mouseClick(nav, Qt.MouseButton.LeftButton, pos=target_pos)  # type: ignore[no-untyped-call]
        qtbot.wait(10)

        assert wb.bottomPanel.activityBar.activeItem == "console"
        assert nav.currentIndex() == 1

    def test_compute_insert_index_on_nav_bar(self, qtbot: QtBot) -> None:
        """Unit test the NavigationBar insertion-index logic."""
        from pymmcore_gui._qt.QtCore import QPoint

        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav

        # Before all items
        assert nav._compute_insert_index(QPoint(-5, nav.height() // 2)) == 0
        # Past all items → count
        past = nav._compute_insert_index(QPoint(10000, nav.height() // 2))
        assert past == nav.itemCount()

        # Find first item's left and right edges
        mid_y = nav.height() // 2
        left_x = None
        for x in range(nav.width()):
            if nav.itemAtPos(QPoint(x, mid_y)) == 0:
                left_x = x
                break
        assert left_x is not None
        right_x = nav.width() - 1
        for x in range(left_x, nav.width()):
            if nav.itemAtPos(QPoint(x, mid_y)) != 0:
                right_x = x - 1
                break
        mid_x = (left_x + right_x) // 2

        # Left half of item 0 → insert at 0 (before it)
        assert nav._compute_insert_index(QPoint(mid_x - 1, mid_y)) == 0
        # Right half of item 0 → insert at 1 (after it)
        assert nav._compute_insert_index(QPoint(mid_x + 1, mid_y)) == 1


# ---- ViewRegistry / reorder / indexed move --------------------------------


def _make_empty_workbench(qtbot: QtBot) -> WorkbenchWidget:
    w = WorkbenchWidget()
    qtbot.addWidget(w)
    return w


def _descriptor(
    view_id: str,
    *,
    location: ViewContainerLocation = L.LEFT_SIDEBAR,
    can_move: bool = True,
) -> ViewDescriptor:
    return ViewDescriptor(
        id=view_id,
        name=view_id.title(),
        factory=_label,
        icon=_test_icon(),
        default_location=location,
        can_move=can_move,
    )


class TestRegistryMoveAndReorder:
    def test_indexed_move_insert_at_front(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        w.registerView(_descriptor("a", location=L.LEFT_SIDEBAR))
        w.registerView(_descriptor("b", location=L.LEFT_SIDEBAR))
        w.registerView(_descriptor("t", location=L.PANEL))

        w.registry.move_view_to_location("t", L.LEFT_SIDEBAR, index=0)

        # Registry and container must agree on the new order.
        assert w.registry.get_views_in_location(L.LEFT_SIDEBAR) == ["t", "a", "b"]
        assert w.leftSidebar.viewIds == ["t", "a", "b"]
        assert w.leftSidebar.activityBar.itemIds == ["t", "a", "b"]
        assert w.registry.get_views_in_location(L.PANEL) == []
        assert w.bottomPanel.viewIds == []

    def test_indexed_move_insert_in_middle(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        for vid in ("a", "b", "c"):
            w.registerView(_descriptor(vid, location=L.LEFT_SIDEBAR))
        w.registerView(_descriptor("t", location=L.PANEL))

        w.registry.move_view_to_location("t", L.LEFT_SIDEBAR, index=1)

        assert w.registry.get_views_in_location(L.LEFT_SIDEBAR) == [
            "a",
            "t",
            "b",
            "c",
        ]
        assert w.leftSidebar.viewIds == ["a", "t", "b", "c"]
        assert w.leftSidebar.activityBar.itemIds == ["a", "t", "b", "c"]

    def test_indexed_move_append_when_index_none(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        w.registerView(_descriptor("a", location=L.LEFT_SIDEBAR))
        w.registerView(_descriptor("t", location=L.PANEL))

        w.registry.move_view_to_location("t", L.LEFT_SIDEBAR)

        assert w.leftSidebar.viewIds == ["a", "t"]

    def test_reorder_within_left_sidebar(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        for vid in ("a", "b", "c"):
            w.registerView(_descriptor(vid, location=L.LEFT_SIDEBAR))

        # c -> front
        w.registry.reorder_view("c", 0)

        assert w.registry.get_views_in_location(L.LEFT_SIDEBAR) == ["c", "a", "b"]
        assert w.leftSidebar.viewIds == ["c", "a", "b"]
        assert w.leftSidebar.activityBar.itemIds == ["c", "a", "b"]

    def test_reorder_within_bottom_panel(self, qtbot: QtBot) -> None:
        """Bottom panel uses NavigationBarAdapter, which goes through
        the rebuild path — exercise it explicitly."""
        w = _make_empty_workbench(qtbot)
        for vid in ("x", "y", "z"):
            w.registerView(_descriptor(vid, location=L.PANEL))

        w.registry.reorder_view("z", 0)

        assert w.registry.get_views_in_location(L.PANEL) == ["z", "x", "y"]
        assert w.bottomPanel.viewIds == ["z", "x", "y"]
        assert w.bottomPanel.activityBar.itemIds == ["z", "x", "y"]

    def test_reorder_preserves_active_view(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        for vid in ("a", "b", "c"):
            w.registerView(_descriptor(vid, location=L.LEFT_SIDEBAR))
        w.setActiveView("b")
        assert w.leftSidebar.activityBar.activeItem == "b"

        w.registry.reorder_view("b", 0)

        # "b" is still the active view even though it moved to index 0.
        assert w.leftSidebar.activityBar.activeItem == "b"
        assert w.leftSidebar.viewIds == ["b", "a", "c"]

    def test_cross_container_move_activates_moved_view_in_target(
        self, qtbot: QtBot
    ) -> None:
        """VS Code parity: when a view is dropped into a different
        container, it becomes the active view in that container.
        The previously-active view of the destination is unchecked.
        """
        w = _make_empty_workbench(qtbot)
        for vid in ("a", "b"):
            w.registerView(_descriptor(vid, location=L.LEFT_SIDEBAR))
        w.registerView(_descriptor("t", location=L.PANEL))
        w.setActiveView("a")
        w.setActiveView("t")

        w.registry.move_view_to_location("t", L.LEFT_SIDEBAR)

        # "t" arrived in LEFT_SIDEBAR and should now be the active
        # view there (replacing "a").
        assert w.leftSidebar.activityBar.activeItem == "t"

    def test_within_container_reorder_preserves_active_view(self, qtbot: QtBot) -> None:
        """Contrast to the cross-container auto-activate behavior:
        a reorder *within* the same container must not steal focus.
        Dragging a tab to reorder it keeps the current tab active.
        """
        w = _make_empty_workbench(qtbot)
        for vid in ("a", "b", "c"):
            w.registerView(_descriptor(vid, location=L.LEFT_SIDEBAR))
        w.setActiveView("b")

        w.registry.reorder_view("c", 0)

        # "b" was active and should still be active after the reorder.
        assert w.leftSidebar.activityBar.activeItem == "b"

    def test_move_respects_can_move_false(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)
        w.registerView(_descriptor("pinned", location=L.PANEL, can_move=False))

        with pytest.raises(PermissionError):
            w.registry.move_view_to_location("pinned", L.LEFT_SIDEBAR)

        # State must be unchanged.
        assert w.registry.get_view_location("pinned") == L.PANEL
        assert w.bottomPanel.viewIds == ["pinned"]
        assert w.leftSidebar.viewIds == []

    def test_reorder_pinned_view_also_raises(self, qtbot: QtBot) -> None:
        """reorder_view is implemented via move_view_to_location so
        can_move enforcement inherits automatically."""
        w = _make_empty_workbench(qtbot)
        w.registerView(_descriptor("pinned", location=L.PANEL, can_move=False))
        w.registerView(_descriptor("other", location=L.PANEL))

        with pytest.raises(PermissionError):
            w.registry.reorder_view("pinned", 1)

    def test_registry_move_unknown_view_raises(self, qtbot: QtBot) -> None:
        w = _make_empty_workbench(qtbot)

        with pytest.raises(KeyError):
            w.registry.move_view_to_location("nope", L.LEFT_SIDEBAR)
