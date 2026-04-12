"""DnD tests for ItemBar (vertical and horizontal) inside the workbench.

These tests exercise the drop handlers by building a QDropEvent
directly and calling ``dropEvent()`` on it, bypassing Qt's native
drag loop (which is synchronous, modal, and can't be driven from a
test). That's the standard Qt DnD testing pattern — it verifies
drop-side logic in isolation from the platform-dependent drag-start
machinery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._layout import (
    ItemBar,
    ViewContainerLocation,
    ViewDescriptor,
)
from pymmcore_gui._layout._dnd import PMM_VIEW_MIME_TYPE, encode_view_id
from pymmcore_gui._layout._enums import ActivityBarPosition, NavDisplayMode
from pymmcore_gui._qt.QtCore import (
    QEvent,
    QMimeData,
    QPoint,
    QPointF,
    Qt,
)
from pymmcore_gui._qt.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
)

from ._helpers import (
    _dnd_workbench,
    _label,
    _make_drop_event,
    _test_icon,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

L = ViewContainerLocation


# ---- helpers --------------------------------------------------------------


def _drop_pos_for_index(bar: ItemBar, index: int) -> tuple[int, int]:
    """Return a (x, y) tuple inside item *index*'s rect on *bar*.

    Used to drop "above" / "into the front of" the item at that index.
    Drops in the top/left half of an item resolve to insertion *before*
    that item via ItemBar's center-of-rect midpoint test.
    """
    rect = bar.itemRect(index)
    if bar.orientation() == Qt.Orientation.Vertical:
        return (rect.center().x(), rect.y() + 1)
    return (rect.x() + 1, rect.center().y())


def _drop_pos_after_last(bar: ItemBar) -> tuple[int, int]:
    """Return a (x, y) tuple past the last item along the primary axis."""
    if not bar.itemIds():
        return (0, 0)
    last = bar.itemRect(len(bar.itemIds()) - 1)
    if bar.orientation() == Qt.Orientation.Vertical:
        return (last.center().x(), last.y() + last.height() + 10)
    return (last.x() + last.width() + 10, last.center().y())


# ---- vertical bar (sidebar) drops -----------------------------------------


class TestVerticalBarDrop:
    def test_drop_different_container_at_front(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        ab.dropEvent(_make_drop_event("terminal", _drop_pos_for_index(ab, 0)))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds[0] == "terminal"
        assert wb.bottomPanel.viewIds == ["console"]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_drop_different_container_at_middle(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        ab.dropEvent(_make_drop_event("terminal", _drop_pos_for_index(ab, 1)))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds == ["explorer", "terminal", "search", "debug"]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_drop_different_container_at_end(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        ab.dropEvent(_make_drop_event("terminal", _drop_pos_after_last(ab)))
        qtbot.wait(10)

        assert wb.leftSidebar.viewIds[-1] == "terminal"

    def test_reorder_within_same_container(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        # Drop "debug" (index 2) above "search" (index 1)
        ab.dropEvent(_make_drop_event("debug", _drop_pos_for_index(ab, 1)))
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
        # Drop explorer (index 0) on the top of debug (index 2). The
        # drop indicator reports visual gap index 2.
        ab.dropEvent(_make_drop_event("explorer", _drop_pos_for_index(ab, 2)))
        qtbot.wait(10)

        # Explorer must land BETWEEN search and debug, not after.
        assert wb.leftSidebar.viewIds == ["search", "explorer", "debug"]

    def test_drop_unknown_mime_is_ignored(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        before = list(wb.leftSidebar.viewIds)

        mime = QMimeData()
        mime.setText("not a view id")
        evt = QDropEvent(
            QPointF(10, 10),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QEvent.Type.Drop,
        )
        evt._keep_alive = mime
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
        ab.dropEvent(_make_drop_event("pinned", _drop_pos_for_index(ab, 0)))
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
        ab.dropEvent(_make_drop_event("terminal", _drop_pos_for_index(ab, 0)))
        qtbot.wait(10)

        # Console should still be active in the panel.
        assert wb.bottomPanel.activityBar.activeItem() == "console"

    def test_compute_insert_index_vertical(self, qtbot: QtBot) -> None:
        """Unit test of the hit-test math in isolation."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        rect0 = ab.itemRect(0)
        rect_last = ab.itemRect(len(ab.itemIds()) - 1)
        x_center = rect0.center().x()

        # Above all items → index 0
        assert ab._compute_insert_index(QPoint(x_center, -5)) == 0
        # Top of first item (above its midpoint) → index 0
        assert ab._compute_insert_index(QPoint(x_center, rect0.y() + 1)) == 0
        # Bottom half of first → index 1
        assert (
            ab._compute_insert_index(QPoint(x_center, rect0.y() + rect0.height() - 1))
            == 1
        )
        # Past everything → count
        assert ab._compute_insert_index(
            QPoint(x_center, rect_last.y() + rect_last.height() + 100)
        ) == len(ab.itemIds())

    def test_reorder_of_active_view_keeps_stack_in_sync(self, qtbot: QtBot) -> None:
        """Regression guard: reordering the currently-active view via
        drop must not desynchronize the QStackedWidget's currentWidget
        from the bar's activeItem.
        """
        wb = _dnd_workbench(qtbot)
        wb.leftSidebar.activityBar.setActive("explorer")
        assert (
            wb.leftSidebar.stack.currentWidget()
            is wb.leftSidebar._views["explorer"].widget
        )

        wb.registry.reorder_view("explorer", 2)

        assert wb.leftSidebar.activityBar.activeItem() == "explorer"
        assert wb.leftSidebar.viewIds == ["search", "debug", "explorer"]
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

        assert wb.leftSidebar.activityBar.activeItem() == "search"
        assert wb.leftSidebar.stack.currentWidget() is search_widget

    def test_drop_indicator_visibility_lifecycle(self, qtbot: QtBot) -> None:
        """Drop indicator is hidden at rest, visible during drag, hidden on leave."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        indicator = ab._drop_indicator

        assert not indicator.isVisible()

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("terminal"))
        first_rect = ab.itemRect(0)
        enter = QDragEnterEvent(
            first_rect.center(),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        ab.dragEnterEvent(enter)
        qtbot.wait(10)
        assert indicator.isVisible()

        ab.dragLeaveEvent(QDragLeaveEvent())
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_drop_indicator_hidden_after_drop(self, qtbot: QtBot) -> None:
        """After a successful drop, the indicator is hidden."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        indicator = ab._drop_indicator

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("terminal"))
        first_rect = ab.itemRect(0)
        enter = QDragEnterEvent(
            first_rect.center(),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        ab.dragEnterEvent(enter)
        assert indicator.isVisible()

        ab.dropEvent(
            _make_drop_event(
                "terminal", (first_rect.center().x(), first_rect.center().y())
            )
        )
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_drop_indicator_position_at_extremes(self, qtbot: QtBot) -> None:
        """Indicator position at index=0, index=count, and middle."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        count = len(ab.itemIds())
        assert count >= 3

        rect0 = ab.itemRect(0)
        rect1 = ab.itemRect(1)
        rect_last = ab.itemRect(count - 1)

        assert ab._drop_indicator_position(0) == rect0.y()
        assert ab._drop_indicator_position(count) == rect_last.y() + rect_last.height()

        pos_1 = ab._drop_indicator_position(1)
        assert rect0.y() < pos_1
        assert pos_1 < rect1.y() + rect1.height()

    def test_drag_source_records_candidate(self, qtbot: QtBot) -> None:
        """Pressing on an item records a drag candidate; releasing clears it."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        rect1 = ab.itemRect(1)

        assert ab._drag_candidate_index == -1

        qtbot.mousePress(  # type: ignore[no-untyped-call]
            ab,
            Qt.MouseButton.LeftButton,
            pos=rect1.center(),
        )
        qtbot.wait(10)
        assert ab._drag_candidate_index == 1
        assert ab._drag_start_pos is not None

        qtbot.mouseRelease(  # type: ignore[no-untyped-call]
            ab,
            Qt.MouseButton.LeftButton,
            pos=rect1.center(),
        )
        qtbot.wait(10)
        assert ab._drag_candidate_index == -1


# ---- horizontal bar (bottom panel) drops ----------------------------------


class TestHorizontalBarDrop:
    def test_drop_onto_bottom_panel_from_left_sidebar(self, qtbot: QtBot) -> None:
        """Drop a view from the left sidebar onto the bottom panel."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        bar.dropEvent(_make_drop_event("explorer", (0, 10)))
        qtbot.wait(10)

        assert "explorer" in wb.bottomPanel.viewIds
        assert "explorer" not in wb.leftSidebar.viewIds
        assert wb.registry.get_view_location("explorer") == L.PANEL
        assert wb.bottomPanel.viewIds[0] == "explorer"

    def test_drop_onto_bottom_panel_at_end(self, qtbot: QtBot) -> None:
        """Drop past all items → append to the bottom panel."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        bar.dropEvent(_make_drop_event("explorer", (10000, 10)))
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds[-1] == "explorer"

    def test_drop_unknown_mime_is_ignored(self, qtbot: QtBot) -> None:
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        before = list(wb.bottomPanel.viewIds)

        mime = QMimeData()
        mime.setText("not a view id")
        evt = QDropEvent(
            QPointF(0, 10),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QEvent.Type.Drop,
        )
        evt._keep_alive = mime
        bar.dropEvent(evt)
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == before

    def test_drag_source_records_candidate(self, qtbot: QtBot) -> None:
        """The mouse-press handler records a drag candidate via itemAt."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        target_idx = 1  # second item = "console"
        target_rect = bar.itemRect(target_idx)

        assert bar._drag_candidate_index == -1

        qtbot.mousePress(  # type: ignore[no-untyped-call]
            bar, Qt.MouseButton.LeftButton, pos=target_rect.center()
        )
        qtbot.wait(10)
        assert bar._drag_candidate_index == target_idx

        qtbot.mouseRelease(  # type: ignore[no-untyped-call]
            bar, Qt.MouseButton.LeftButton, pos=target_rect.center()
        )
        qtbot.wait(10)
        assert bar._drag_candidate_index == -1

    def test_cross_container_move_clears_source_ghost(self, qtbot: QtBot) -> None:
        """After dragging the active view out of a container, the source
        container's stack must not still show the ghost of a sibling.
        """
        wb = _dnd_workbench(qtbot)
        wb.bottomPanel.activityBar.setActive("terminal")
        terminal_widget = wb.bottomPanel._views["terminal"].widget
        assert wb.bottomPanel.stack.currentWidget() is terminal_widget
        assert wb.bottomPanel.activityBar.activeItem() == "terminal"

        ab = wb.leftSidebar.activityBar
        ab.dropEvent(_make_drop_event("terminal", _drop_pos_for_index(ab, 0)))
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == ["console"]
        assert wb.bottomPanel.activityBar.activeItem() == "console"
        console_widget = wb.bottomPanel._views["console"].widget
        assert wb.bottomPanel.stack.currentWidget() is console_widget

    def test_cross_container_move_empty_source_leaves_no_active(
        self, qtbot: QtBot
    ) -> None:
        """Draining a container must not crash auto-activating siblings."""
        wb = _dnd_workbench(qtbot)
        ab = wb.leftSidebar.activityBar
        drop_pos = _drop_pos_for_index(ab, 0)

        ab.dropEvent(_make_drop_event("terminal", drop_pos))
        qtbot.wait(10)
        ab.dropEvent(_make_drop_event("console", drop_pos))
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == []
        assert wb.bottomPanel.activityBar.activeItem() is None

    def test_drop_on_content_area_appends_to_container(self, qtbot: QtBot) -> None:
        """Dropping on the big content widget under the tab bar should
        count as 'drop into this container, at the end'.
        """
        wb = _dnd_workbench(qtbot)
        stack = wb.bottomPanel.stack
        before = list(wb.bottomPanel.viewIds)

        stack.dropEvent(_make_drop_event("explorer", (50, 50)))
        qtbot.wait(50)

        assert wb.bottomPanel.viewIds == [*before, "explorer"]
        assert wb.registry.get_view_location("explorer") == L.PANEL

    def test_drop_on_sidebar_stack_appends_to_left_sidebar(self, qtbot: QtBot) -> None:
        """Same as test_drop_on_content_area_appends_to_container but
        for the left sidebar's stack widget.
        """
        wb = _dnd_workbench(qtbot)
        stack = wb.leftSidebar.stack
        before = list(wb.leftSidebar.viewIds)

        stack.dropEvent(_make_drop_event("terminal", (80, 80)))
        qtbot.wait(50)

        assert wb.leftSidebar.viewIds == [*before, "terminal"]
        assert wb.registry.get_view_location("terminal") == L.LEFT_SIDEBAR

    def test_drop_indicator_visibility(self, qtbot: QtBot) -> None:
        """Indicator on the horizontal bar shows/hides across drag lifecycle."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        indicator = bar._drop_indicator

        assert not indicator.isVisible()

        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id("explorer"))
        first_rect = bar.itemRect(0)
        enter = QDragEnterEvent(
            first_rect.center(),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        enter._keep_alive = mime
        bar.dragEnterEvent(enter)
        qtbot.wait(10)
        assert indicator.isVisible()

        bar.dragLeaveEvent(QDragLeaveEvent())
        qtbot.wait(10)
        assert not indicator.isVisible()

    def test_reorder_forward_gap_compensates(self, qtbot: QtBot) -> None:
        """Same regression guard as the vertical case, but on the
        horizontal bar path.
        """
        wb = _dnd_workbench(qtbot)
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

        bar = wb.bottomPanel.activityBar
        # Drop terminal (idx 0) on the left half of "output" (idx 2).
        bar.dropEvent(_make_drop_event("terminal", _drop_pos_for_index(bar, 2)))
        qtbot.wait(50)

        assert wb.bottomPanel.viewIds == ["console", "terminal", "output"]

    def test_display_mode_default_is_text_only(self, qtbot: QtBot) -> None:
        """Horizontal bars default to TEXT_ONLY."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        assert isinstance(bar, ItemBar)
        assert bar.displayMode() == NavDisplayMode.TEXT_ONLY
        # Effective rendering: text shown, icon hidden.
        item = bar._items[0]
        assert bar._effective_text(item) == "Terminal"
        assert bar._effective_icon(item).isNull()

    def test_display_mode_switches(self, qtbot: QtBot) -> None:
        """Cycling display mode changes what _effective_text/icon returns."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        assert isinstance(bar, ItemBar)

        bar.setDisplayMode(NavDisplayMode.BOTH)
        item = bar._items[0]
        assert bar._effective_text(item) == "Terminal"
        assert not bar._effective_icon(item).isNull()

        bar.setDisplayMode(NavDisplayMode.ICONS_ONLY)
        assert bar._effective_text(item) == ""
        assert not bar._effective_icon(item).isNull()

        bar.setDisplayMode(NavDisplayMode.TEXT_ONLY)
        assert bar._effective_text(item) == "Terminal"
        assert bar._effective_icon(item).isNull()

        bar.setDisplayMode(NavDisplayMode.BOTH)
        assert bar._effective_text(item) == "Terminal"
        assert not bar._effective_icon(item).isNull()

    def test_display_mode_survives_bar_swap(self, qtbot: QtBot) -> None:
        """Toggling the activity bar position destroys the bar and creates
        a fresh one. The container stores the display mode preference so
        it's reapplied on recreation.
        """
        wb = _dnd_workbench(qtbot)
        panel = wb.bottomPanel
        bar = panel.activityBar
        assert isinstance(bar, ItemBar)

        bar.setDisplayMode(NavDisplayMode.ICONS_ONLY)
        panel._nav_display_mode = NavDisplayMode.ICONS_ONLY

        # Swap to hidden and back to top. The new bar should remember.
        panel.setAbPosition(ActivityBarPosition.HIDDEN)
        panel.arrange()
        panel.setAbPosition(ActivityBarPosition.TOP)
        panel.arrange()

        new_bar = panel.activityBar
        assert isinstance(new_bar, ItemBar)
        assert new_bar.displayMode() == NavDisplayMode.ICONS_ONLY
        if new_bar.itemIds():
            item = new_bar._items[0]
            assert new_bar._effective_text(item) == ""
            assert not new_bar._effective_icon(item).isNull()

    def test_click_to_switch_view_on_horizontal_bar(self, qtbot: QtBot) -> None:
        """Click on a tab item should switch the active view.

        With the hand-rolled ItemBar this exercises pure-Python event
        dispatch (mousePress + mouseRelease on a known item rect).
        """
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        bar.setActive("terminal")
        assert bar.activeItem() == "terminal"

        target_rect = bar.itemRect(1)  # console
        qtbot.mouseClick(  # type: ignore[no-untyped-call]
            bar, Qt.MouseButton.LeftButton, pos=target_rect.center()
        )
        qtbot.wait(10)

        assert bar.activeItem() == "console"

    def test_compute_insert_index_horizontal(self, qtbot: QtBot) -> None:
        """Unit test the horizontal bar's insertion-index logic."""
        wb = _dnd_workbench(qtbot)
        bar = wb.bottomPanel.activityBar
        rect0 = bar.itemRect(0)
        mid_y = rect0.center().y()

        # Before all items
        assert bar._compute_insert_index(QPoint(-5, mid_y)) == 0
        # Past all items → count
        assert bar._compute_insert_index(QPoint(10000, mid_y)) == len(bar.itemIds())
        # Left half of item 0 → insert at 0 (before it)
        assert bar._compute_insert_index(QPoint(rect0.x() + 1, mid_y)) == 0
        # Right half of item 0 → insert at 1 (after it)
        assert (
            bar._compute_insert_index(QPoint(rect0.x() + rect0.width() - 1, mid_y)) == 1
        )
