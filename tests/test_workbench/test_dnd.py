"""DnD tests for ActivityBar and NavigationBarAdapter.

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
    NavigationBarAdapter,
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
    QMouseEvent,
)
from pymmcore_gui._qt.QtWidgets import QApplication

from ._helpers import (
    _dnd_workbench,
    _label,
    _make_drop_event,
    _test_icon,
)

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

L = ViewContainerLocation


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
        wb = _dnd_workbench(qtbot)
        nav = wb.bottomPanel.activityBar._nav
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
        nav.dropEvent(evt)
        qtbot.wait(10)

        assert wb.bottomPanel.viewIds == before

    def test_navigation_bar_drag_source_records_candidate(self, qtbot: QtBot) -> None:
        """The mouse-press override on _DraggableNavigationBar records
        a drag candidate based on itemAtPos."""
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
        qtbot.wait(50)

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
        wb = _dnd_workbench(qtbot)
        panel = wb.bottomPanel
        nav_adapter = panel.activityBar
        assert isinstance(nav_adapter, NavigationBarAdapter)

        nav_adapter.setDisplayMode(NavDisplayMode.ICONS_ONLY)
        panel._nav_display_mode = NavDisplayMode.ICONS_ONLY

        # Swap to hidden and back to top. The new NavigationBarAdapter
        # should apply the remembered display mode.
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
