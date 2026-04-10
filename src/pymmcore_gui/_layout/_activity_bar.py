from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.QtCore import Qt, Signal
from pymmcore_gui._qt.QtWidgets import (
    QBoxLayout,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import QIcon


class ActivityBar(QWidget):
    """Icon strip that toggles views. Supports vertical or horizontal.

    Works at the lowest level of the workbench: it knows only about
    "items" (id + text + icon + active state). A :class:`PaneContainer`
    maps those items 1:1 to views.
    """

    itemToggled = Signal(str)  # item_id, or "" to collapse

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
