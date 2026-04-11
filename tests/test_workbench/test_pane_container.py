from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._layout import (
    ActivityBar,
    ActivityBarPosition,
    NavigationBarAdapter,
    PaneContainer,
)

from ._helpers import _label

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


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
