from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pymmcore_gui._layout._enums import NavDisplayMode
from pymmcore_gui._layout._item_bar import ItemBar
from pymmcore_gui._qt.QtCore import QPoint, Qt

from ._helpers import _test_icon

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


# ---- fixtures parametrized over both orientations -------------------------


@pytest.fixture(params=[Qt.Orientation.Vertical, Qt.Orientation.Horizontal])
def bar(request: pytest.FixtureRequest, qtbot: QtBot) -> ItemBar:
    b = ItemBar(orientation=request.param)
    qtbot.addWidget(b)
    return b


@pytest.fixture()
def vbar(qtbot: QtBot) -> ItemBar:
    b = ItemBar(orientation=Qt.Orientation.Vertical)
    qtbot.addWidget(b)
    return b


@pytest.fixture()
def hbar(qtbot: QtBot) -> ItemBar:
    b = ItemBar(orientation=Qt.Orientation.Horizontal)
    qtbot.addWidget(b)
    return b


# ---- construction & properties --------------------------------------------


def test_default_orientation_is_vertical(qtbot: QtBot) -> None:
    b = ItemBar()
    qtbot.addWidget(b)
    assert b.orientation() == Qt.Orientation.Vertical


def test_default_display_mode_is_orientation_aware(qtbot: QtBot) -> None:
    v = ItemBar(Qt.Orientation.Vertical)
    h = ItemBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(v)
    qtbot.addWidget(h)
    assert v.displayMode() == NavDisplayMode.ICONS_ONLY
    assert h.displayMode() == NavDisplayMode.TEXT_ONLY


def test_initial_state_empty(bar: ItemBar) -> None:
    assert bar.itemIds() == []
    assert bar.activeItem() is None
    assert bar.isCollapsible() is True


# ---- item management ------------------------------------------------------


def test_add_items(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    assert bar.itemIds() == ["a", "b"]


def test_add_duplicate_raises(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    with pytest.raises(ValueError, match="already exists"):
        bar.addItem("a", "A again")


def test_insert_item_at_index(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("c", "C")
    bar.insertItem(1, "b", "B")
    assert bar.itemIds() == ["a", "b", "c"]


def test_insert_item_clamps_negative(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.insertItem(-5, "first", "First")
    assert bar.itemIds() == ["first", "a"]


def test_insert_item_clamps_oversize(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.insertItem(99, "last", "Last")
    assert bar.itemIds() == ["a", "last"]


def test_remove_item(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.removeItem("a")
    assert bar.itemIds() == ["b"]


def test_remove_nonexistent_is_noop(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.removeItem("nope")
    assert bar.itemIds() == ["a"]


def test_remove_active_clears_active(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.setActive("a")
    bar.removeItem("a")
    assert bar.activeItem() is None


def test_move_item(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.addItem("c", "C")
    bar.moveItem(0, 2)
    assert bar.itemIds() == ["b", "c", "a"]


def test_move_item_no_change(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.moveItem(0, 0)
    assert bar.itemIds() == ["a", "b"]


def test_move_item_clamps_target(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.moveItem(0, 99)
    assert bar.itemIds() == ["b", "a"]


def test_move_invalid_source_raises(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    with pytest.raises(IndexError):
        bar.moveItem(5, 0)


def test_set_item_text_and_icon(bar: ItemBar) -> None:
    bar.addItem("a", "Original")
    bar.setItemText("a", "Updated")
    bar.setItemIcon("a", _test_icon())
    # Internal record should reflect the change.
    assert bar._items[0].text == "Updated"
    assert bar._items[0].icon is not None


# ---- selection ------------------------------------------------------------


def test_set_active_emits_signal(bar: ItemBar, qtbot: QtBot) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    with qtbot.waitSignal(bar.itemToggled) as blocker:
        bar.setActive("a")
    assert blocker.args == ["a"]
    assert bar.activeItem() == "a"


def test_set_active_silent_no_signal(bar: ItemBar, qtbot: QtBot) -> None:
    bar.addItem("a", "A")
    with qtbot.assertNotEmitted(bar.itemToggled, wait=50):
        bar.setActiveSilent("a")
    assert bar.activeItem() == "a"


def test_toggle_off_when_collapsible(bar: ItemBar, qtbot: QtBot) -> None:
    bar.addItem("a", "A")
    bar.setActive("a")
    with qtbot.waitSignal(bar.itemToggled) as blocker:
        bar.setActive("a")
    assert blocker.args == [""]
    assert bar.activeItem() is None


def test_toggle_blocked_when_not_collapsible(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.setActive("a")
    bar.setCollapsible(False)
    bar.setActive("a")
    assert bar.activeItem() == "a"


def test_switching_items(bar: ItemBar, qtbot: QtBot) -> None:
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.setActive("a")
    with qtbot.waitSignal(bar.itemToggled) as blocker:
        bar.setActive("b")
    assert blocker.args == ["b"]
    assert bar.activeItem() == "b"


def test_deselect(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    bar.setActive("a")
    bar.deselect()
    assert bar.activeItem() is None


def test_activate_first(bar: ItemBar, qtbot: QtBot) -> None:
    bar.addItem("first", "First")
    bar.addItem("second", "Second")
    with qtbot.waitSignal(bar.itemToggled) as blocker:
        bar.activateFirst()
    assert blocker.args == ["first"]
    assert bar.activeItem() == "first"


def test_activate_first_empty_is_noop(bar: ItemBar) -> None:
    bar.activateFirst()
    assert bar.activeItem() is None


# ---- display mode ---------------------------------------------------------


def test_set_display_mode(hbar: ItemBar) -> None:
    hbar.addItem("a", "A", icon=_test_icon())
    hbar.setDisplayMode(NavDisplayMode.ICONS_ONLY)
    mode1 = hbar.displayMode()
    assert mode1 == NavDisplayMode.ICONS_ONLY
    hbar.setDisplayMode(NavDisplayMode.BOTH)
    mode2 = hbar.displayMode()
    assert mode2 == NavDisplayMode.BOTH


def test_display_mode_no_op_when_unchanged(hbar: ItemBar) -> None:
    hbar.addItem("a", "A")
    initial = hbar.displayMode()
    hbar.setDisplayMode(initial)
    assert hbar.displayMode() == initial


# ---- hit testing ----------------------------------------------------------


def test_item_at_pos_returns_index(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(bar)
    bar.addItem("a", "Aaaaa")
    bar.addItem("b", "Bbbbb")
    bar.resize(400, 32)
    bar.show()
    qtbot.waitExposed(bar)
    # Hit a point inside the first item's rect.
    rect_a = bar.itemRect(0)
    assert rect_a.isValid()
    pt = QPoint(rect_a.x() + rect_a.width() // 2, rect_a.height() // 2)
    assert bar.itemAt(pt) == 0


def test_item_at_pos_returns_neg1_when_outside(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(bar)
    bar.addItem("a", "Aaa")
    bar.resize(400, 32)
    bar.show()
    qtbot.waitExposed(bar)
    far_right = QPoint(bar.width() - 1, bar.height() // 2)
    # Past the only item's rect.
    last_rect = bar.itemRect(0)
    if far_right.x() > last_rect.x() + last_rect.width():
        assert bar.itemAt(far_right) == -1


def test_item_rect_out_of_range_is_empty(bar: ItemBar) -> None:
    bar.addItem("a", "A")
    assert bar.itemRect(99).isEmpty()
    assert bar.itemRect(-1).isEmpty()


# ---- paint smoke ----------------------------------------------------------


def test_paint_does_not_crash_empty(bar: ItemBar, qtbot: QtBot) -> None:
    bar.resize(200, 200)
    bar.show()
    qtbot.waitExposed(bar)
    bar.repaint()


def test_paint_does_not_crash_with_items(bar: ItemBar, qtbot: QtBot) -> None:
    for i in range(5):
        bar.addItem(f"item{i}", f"Item {i}", icon=_test_icon())
    bar.setActive("item2")
    bar.resize(300, 300)
    bar.show()
    qtbot.waitExposed(bar)
    bar.repaint()


# ---- layout & resize ------------------------------------------------------


def test_horizontal_layout_assigns_rects_in_order(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(bar)
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.addItem("c", "C")
    bar.resize(600, 32)
    bar.show()
    qtbot.waitExposed(bar)
    rects = [bar.itemRect(i) for i in range(3)]
    # Each rect's x is past the previous one's right edge.
    assert rects[0].x() < rects[1].x() < rects[2].x()
    # All share the same y.
    assert rects[0].y() == rects[1].y() == rects[2].y()


def test_vertical_layout_assigns_rects_in_order(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Vertical)
    qtbot.addWidget(bar)
    bar.addItem("a", "A")
    bar.addItem("b", "B")
    bar.addItem("c", "C")
    bar.resize(48, 400)
    bar.show()
    qtbot.waitExposed(bar)
    rects = [bar.itemRect(i) for i in range(3)]
    assert rects[0].y() < rects[1].y() < rects[2].y()
    assert rects[0].x() == rects[1].x() == rects[2].x()


def test_resize_recomputes_layout(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Vertical)
    qtbot.addWidget(bar)
    bar.addItem("a", "A")
    bar.resize(48, 100)
    bar.show()
    qtbot.waitExposed(bar)
    w_before = bar.itemRect(0).width()
    bar.resize(96, 100)
    # Vertical layout: width tracks the widget width.
    assert bar.itemRect(0).width() != w_before


# ---- selection animation --------------------------------------------------


def test_set_active_starts_indicator_animation(qtbot: QtBot) -> None:
    bar = ItemBar(Qt.Orientation.Horizontal)
    qtbot.addWidget(bar)
    bar.addItem("a", "Aaaa")
    bar.addItem("b", "Bbbb")
    bar.resize(400, 32)
    bar.show()
    qtbot.waitExposed(bar)
    bar.setActive("a")
    bar.setActive("b")
    # Animation should have valid endpoints (start = a's indicator, end = b's).
    assert bar._indicator_anim.startValue() is not None
    assert bar._indicator_anim.endValue() is not None
