from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pymmcore_gui._layout import ViewContainerLocation

from ._helpers import _descriptor, _make_empty_workbench

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

L = ViewContainerLocation


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
