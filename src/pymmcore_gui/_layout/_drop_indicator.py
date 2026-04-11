"""Thin colored line widget used during DnD to mark where a drop will land.

Parent-owned by a tab-strip widget (``ActivityBar`` or the inner
``_DraggableNavigationBar``). Transparent to mouse events so it never
steals drag hit-testing from the bar itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.QtCore import Qt
from pymmcore_gui._qt.QtGui import QColor, QPainter, QPalette
from pymmcore_gui._qt.QtWidgets import QWidget

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import QPaintEvent


class DropIndicator(QWidget):
    """A 3px colored line painted along the bar's cross-axis at a given position.

    The direction of the line is set at construction via *orientation* —
    a vertical-orientation bar gets a *horizontal* line spanning the bar's
    full width, and vice versa. Call :meth:`showAt` to position and show
    the indicator; the widget is hidden initially.
    """

    THICKNESS = 3

    def __init__(
        self,
        parent: QWidget,
        orientation: Qt.Orientation,
    ) -> None:
        super().__init__(parent)
        self._orientation = orientation
        # Mouse events must fall through to the parent bar so drag
        # hit-testing keeps working while the indicator is visible.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def showAt(self, position: int) -> None:
        """Show the indicator at *position* along the bar's primary axis.

        For a vertical bar, *position* is a **y** coordinate; the line
        is horizontal, spanning the bar's full width. For a horizontal
        bar, *position* is an **x** coordinate; the line is vertical,
        spanning the bar's full height.
        """
        parent = self.parentWidget()
        if parent is None:
            return
        half = self.THICKNESS // 2
        if self._orientation == Qt.Orientation.Vertical:
            self.setGeometry(0, position - half, parent.width(), self.THICKNESS)
        else:
            self.setGeometry(position - half, 0, self.THICKNESS, parent.height())
        self.raise_()
        self.show()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        color = self.palette().color(QPalette.ColorRole.Highlight)
        if not color.isValid():
            color = QColor("#007ACC")  # VS Code blue fallback
        painter.fillRect(self.rect(), color)
