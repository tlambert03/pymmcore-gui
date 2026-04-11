from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.QtCore import QEvent, QMimeData, QObject, QPoint, Qt, Signal
from pymmcore_gui._qt.QtGui import QDrag, QMouseEvent
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QBoxLayout,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ._dnd import PMM_VIEW_MIME_TYPE, decode_view_id, encode_view_id
from ._drop_indicator import DropIndicator

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import (
        QDragEnterEvent,
        QDragLeaveEvent,
        QDragMoveEvent,
        QDropEvent,
        QIcon,
    )


class ActivityBar(QWidget):
    """Icon strip that toggles views. Supports vertical or horizontal.

    Works at the lowest level of the workbench: it knows only about
    "items" (id + text + icon + active state). A :class:`PaneContainer`
    maps those items 1:1 to views.
    """

    itemToggled = Signal(str)  # item_id, or "" to collapse
    itemDropped = Signal(str, int)  # view_id, target_insertion_index

    def __init__(
        self,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QToolButton] = {}
        self._active: str | None = None
        self._collapsible = True
        self._orientation = orientation

        if orientation == Qt.Orientation.Vertical:
            self._layout: QBoxLayout = QVBoxLayout(self)
        else:
            self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self._layout.addStretch()

        # Drag-source state.
        self._drag_start_pos: QPoint | None = None
        self._drag_candidate_id: str | None = None

        # Drop-target state.
        self._drop_insert_index: int | None = None
        self._drop_indicator = DropIndicator(self, orientation)
        self.setAcceptDrops(True)

    # ---- public API -------------------------------------------------------

    @property
    def orientation(self) -> Qt.Orientation:
        return self._orientation

    @property
    def activeItem(self) -> str | None:
        return self._active

    @property
    def collapsible(self) -> bool:
        return self._collapsible

    @collapsible.setter
    def collapsible(self, value: bool) -> None:
        self._collapsible = value

    @property
    def itemIds(self) -> list[str]:
        return list(self._buttons)

    def addItem(
        self, item_id: str, text: str, *, icon: QIcon | None = None
    ) -> QToolButton:
        """Append an item to the end of the bar."""
        return self.insertItem(len(self._buttons), item_id, text, icon=icon)

    def insertItem(
        self,
        index: int,
        item_id: str,
        text: str,
        *,
        icon: QIcon | None = None,
    ) -> QToolButton:
        """Insert an item at *index*.

        ``index`` is clamped into ``[0, item_count]``. ``index == count``
        is equivalent to :meth:`addItem`.
        """
        if item_id in self._buttons:
            raise ValueError(f"Item {item_id!r} already exists")
        count = len(self._buttons)
        clamped = max(0, min(index, count))

        btn = QToolButton()
        btn.setToolTip(text)
        if icon:
            btn.setIcon(icon)
        else:
            btn.setText(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(False)
        btn.setObjectName(item_id)
        btn.clicked.connect(self._on_clicked)
        # Event filter lets the bar intercept mouse events that would
        # otherwise be eaten by the QToolButton, so we can start drags
        # from button press+move without affecting normal click behavior.
        btn.installEventFilter(self)

        # QBoxLayout ends in a trailing stretch. Item widgets occupy
        # layout indices [0, count); the stretch is at `count`.
        # Insertion at clamped=k places the new widget at layout index k.
        self._layout.insertWidget(clamped, btn)

        # Maintain _buttons insertion order to match visual order.
        if clamped == count:
            self._buttons[item_id] = btn
        else:
            # Rebuild dict with btn inserted at the target position.
            items = list(self._buttons.items())
            items.insert(clamped, (item_id, btn))
            self._buttons = dict(items)
        return btn

    def removeItem(self, item_id: str) -> None:
        """Remove an item from the bar. No-op if not present."""
        btn = self._buttons.pop(item_id, None)
        if btn is None:
            return
        self._layout.removeWidget(btn)
        btn.deleteLater()
        if self._active == item_id:
            self._active = None

    def moveItem(self, old_index: int, new_index: int) -> None:
        """Move the item at *old_index* to *new_index*."""
        count = len(self._buttons)
        if not (0 <= old_index < count):
            raise IndexError(f"old_index out of range: {old_index}")
        new_index = max(0, min(new_index, count - 1))
        if old_index == new_index:
            return

        items = list(self._buttons.items())
        item = items.pop(old_index)
        items.insert(new_index, item)
        self._buttons = dict(items)

        # Re-order the QBoxLayout: take the widget out, insert at new idx.
        _, btn = item
        self._layout.removeWidget(btn)
        self._layout.insertWidget(new_index, btn)

    def setActive(self, item_id: str | None) -> None:
        """Programmatically activate (or deactivate) an item."""
        if item_id:
            self._toggle(item_id)
        elif self._active:
            self._toggle(self._active)

    def deselect(self) -> None:
        """Uncheck the active button without emitting itemToggled."""
        if self._active and self._active in self._buttons:
            self._buttons[self._active].setChecked(False)
        self._active = None

    def activateFirst(self) -> None:
        """Activate the first item if any exist."""
        first = next(iter(self._buttons), None)
        if first:
            self._activate_without_collapse(first)

    def setActiveSilent(self, item_id: str) -> None:
        """Update checked state without emitting itemToggled."""
        if self._active and self._active in self._buttons:
            self._buttons[self._active].setChecked(False)
        self._active = item_id
        self._buttons[item_id].setChecked(True)

    # ---- internals --------------------------------------------------------

    def _activate_without_collapse(self, item_id: str) -> None:
        """Set item as active (checked) without allowing collapse."""
        self.setActiveSilent(item_id)
        self.itemToggled.emit(item_id)

    def _on_clicked(self) -> None:
        item_id = self.sender().objectName()
        self._toggle(item_id)

    def _toggle(self, item_id: str) -> None:
        if self._active == item_id:
            if not self._collapsible:
                self._buttons[item_id].setChecked(True)
                return
            self._buttons[item_id].setChecked(False)
            self._active = None
            self.itemToggled.emit("")
        else:
            if self._active and self._active in self._buttons:
                self._buttons[self._active].setChecked(False)
            self._active = item_id
            self._buttons[item_id].setChecked(True)
            self.itemToggled.emit(item_id)

    # ---- drag source -----------------------------------------------------
    #
    # Mouse events delivered to a QToolButton child are eaten by the
    # button, so overriding ActivityBar.mousePressEvent/mouseMoveEvent
    # would never see clicks on buttons. Instead we install this widget
    # as an event filter on each button (see insertItem) and intercept
    # mouse events before the button handles them. Returning False from
    # eventFilter lets the button still process the event normally, so
    # clicks still toggle views — drag just happens in parallel.

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(obj, QToolButton) or obj not in self._buttons.values():
            return super().eventFilter(obj, event)

        etype = event.type()
        if etype == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_candidate_id = obj.objectName()
                self._drag_start_pos = event.pos()
        elif etype == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            if (
                self._drag_candidate_id is not None
                and self._drag_start_pos is not None
                and (event.buttons() & Qt.MouseButton.LeftButton)
            ):
                delta = (event.pos() - self._drag_start_pos).manhattanLength()
                if delta >= QApplication.startDragDistance():
                    view_id = self._drag_candidate_id
                    self._drag_candidate_id = None
                    self._drag_start_pos = None
                    self._start_drag(view_id)
                    # After ``_start_drag`` (which runs ``QDrag.exec``
                    # modally and may fire a drop-handler that deletes
                    # the source button via ``removeItem``), ``obj`` may
                    # be a dangling C++ wrapper. Return True without
                    # forwarding to ``super().eventFilter`` — the drag
                    # fully consumed this event anyway.
                    return True
        elif etype in (QEvent.Type.MouseButtonRelease, QEvent.Type.Leave):
            # Cancel any pending drag candidate so a stray click past
            # the button doesn't start a drag later.
            self._drag_candidate_id = None
            self._drag_start_pos = None

        return super().eventFilter(obj, event)

    def _start_drag(self, view_id: str) -> None:
        btn = self._buttons.get(view_id)
        if btn is None:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id(view_id))
        drag.setMimeData(mime)
        pixmap = btn.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.DropAction.MoveAction)

    # ---- drop target -----------------------------------------------------

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_insert_index = index
        self._drop_indicator.showAt(self._drop_indicator_position(index))

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_insert_index = index
        self._drop_indicator.showAt(self._drop_indicator_position(index))
        e.acceptProposedAction()

    def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
        self._drop_insert_index = None
        self._drop_indicator.hide()
        super().dragLeaveEvent(e)

    def dropEvent(self, e: QDropEvent) -> None:
        view_id = decode_view_id(e.mimeData())
        if view_id is None:
            e.ignore()
            return
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_insert_index = None
        self._drop_indicator.hide()
        e.acceptProposedAction()
        self.itemDropped.emit(view_id, index)

    def _compute_insert_index(self, pos: QPoint) -> int:
        """Return the insertion index a drop at *pos* would land on.

        Walks the buttons in display order and returns the index of the
        first button whose centerline is past *pos* (along the bar's
        primary axis). Past all items → append at the end.
        """
        if not self._buttons:
            return 0
        vertical = self._orientation == Qt.Orientation.Vertical
        for i, btn in enumerate(self._buttons.values()):
            rect = btn.geometry()
            if vertical:
                midpoint = rect.y() + rect.height() // 2
                if pos.y() < midpoint:
                    return i
            else:
                midpoint = rect.x() + rect.width() // 2
                if pos.x() < midpoint:
                    return i
        return len(self._buttons)

    def _drop_indicator_position(self, index: int) -> int:
        """Return the primary-axis coordinate for a drop indicator at *index*.

        For index=0, the line sits at the top/left edge of the first
        button. For index=count, at the bottom/right edge of the last
        one. Otherwise between the two neighboring buttons.
        """
        count = len(self._buttons)
        vertical = self._orientation == Qt.Orientation.Vertical
        if count == 0:
            margin = self._layout.contentsMargins()
            return margin.top() if vertical else margin.left()

        buttons = list(self._buttons.values())
        clamped = max(0, min(index, count))

        if clamped == 0:
            g = buttons[0].geometry()
            return g.y() if vertical else g.x()
        if clamped == count:
            g = buttons[-1].geometry()
            return (g.y() + g.height()) if vertical else (g.x() + g.width())

        above = buttons[clamped - 1].geometry()
        below = buttons[clamped].geometry()
        if vertical:
            return (above.y() + above.height() + below.y()) // 2
        return (above.x() + above.width() + below.x()) // 2
