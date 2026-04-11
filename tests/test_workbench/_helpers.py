"""Shared helpers for the workbench test suite.

Plain module-level functions (not pytest fixtures) used by multiple
test files in this directory. Fixtures that *wrap* these live in
``conftest.py`` beside this file so pytest can auto-discover them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._layout import (
    ViewContainerLocation,
    ViewDescriptor,
    WorkbenchWidget,
)
from pymmcore_gui._layout._dnd import PMM_VIEW_MIME_TYPE, encode_view_id
from pymmcore_gui._qt.QtCore import QEvent, QMimeData, QPointF, Qt
from pymmcore_gui._qt.QtGui import QColor, QDropEvent, QIcon, QPixmap
from pymmcore_gui._qt.QtWidgets import QLabel

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


L = ViewContainerLocation


def _label() -> QLabel:
    """Return a fresh test QLabel."""
    return QLabel("test")


def _test_icon() -> QIcon:
    """Return a small filled QIcon for tests that need a non-null icon.

    Avoids QIconifyIcon's network/cache dependency so tests stay
    deterministic and offline-friendly.
    """
    pix = QPixmap(16, 16)
    pix.fill(QColor("red"))
    return QIcon(pix)


def _descriptor(
    view_id: str,
    *,
    location: ViewContainerLocation = L.LEFT_SIDEBAR,
    can_move: bool = True,
) -> ViewDescriptor:
    """Return a minimal ViewDescriptor suitable for registry tests."""
    return ViewDescriptor(
        id=view_id,
        name=view_id.title(),
        factory=_label,
        icon=_test_icon(),
        default_location=location,
        can_move=can_move,
    )


def _make_workbench() -> WorkbenchWidget:
    """Create a WorkbenchWidget with minimal content for testing."""
    w = WorkbenchWidget()
    w.addView(
        "explorer", "Explorer", _label, icon=_test_icon(), location=L.LEFT_SIDEBAR
    )
    w.setActiveView("explorer")
    w.addView(
        "properties",
        "Properties",
        _label,
        icon=_test_icon(),
        location=L.RIGHT_SIDEBAR,
    )
    w.setActiveView("properties")
    w.addView("terminal", "Terminal", _label, icon=_test_icon(), location=L.PANEL)
    w.setActiveView("terminal")
    return w


def _make_empty_workbench(qtbot: QtBot) -> WorkbenchWidget:
    """Create an empty WorkbenchWidget registered with qtbot for cleanup."""
    w = WorkbenchWidget()
    qtbot.addWidget(w)
    return w


def _dnd_workbench(qtbot: QtBot) -> WorkbenchWidget:
    """Isolated WorkbenchWidget with exactly three left-sidebar views and
    two panel views.

    Built directly (not via MicroManagerGUI) so the test environment
    is stable under changes to the real placeholder view set. Shown
    via ``w.show()`` so the activity bar has real button geometries.
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


def _sidebar_sizes(wb: WorkbenchWidget) -> tuple[int, int, int]:
    """Return (left_width, editor_width, right_width) from actual geometry."""
    left = wb.leftSidebar.splitterWidget
    right = wb.rightSidebar.splitterWidget
    editor = wb.centralWidget
    return left.width(), editor.width(), right.width()


def _make_drop_event(view_id: str, pos: tuple[int, int]) -> QDropEvent:
    """Build a QDropEvent carrying *view_id* at local position *pos*.

    Note: ``QDropEvent`` does not take ownership of its ``QMimeData``,
    so we attach it to the event object as an attribute to keep the
    Python reference alive until the caller is done with the event.
    Otherwise the C++ QMimeData is destroyed when this function
    returns and the subsequent ``e.mimeData()`` access segfaults.
    """
    mime = QMimeData()
    mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id(view_id))
    evt = QDropEvent(
        QPointF(*pos),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QEvent.Type.Drop,
    )
    evt._keep_alive = mime
    return evt
