from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.QtCore import Qt

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from pymmcore_gui._layout import ActivityBar


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
