"""NavigationBar adapter that matches the ActivityBar interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.Qlementine import NavigationBar  # type: ignore[attr-defined]
from pymmcore_gui._qt.QtCore import Signal
from pymmcore_gui._qt.QtWidgets import QHBoxLayout, QWidget

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import QIcon


class NavigationBarAdapter(QWidget):
    """Wraps Qlementine's NavigationBar with the same interface as ActivityBar."""

    itemToggled = Signal(str)  # item_id, or "" to collapse

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nav = NavigationBar(self)  # pyright: ignore[reportCallIssue]
        self._nav.setFixedHeight(32)
        self._nav.setItemsShouldExpand(False)
        self._item_ids: list[str] = []
        self._active: str | None = None
        self._collapsible = True

        # Smaller text for panel/sidebar context
        font = self._nav.font()
        font.setPointSizeF(font.pointSizeF() * 0.75)
        font.setBold(False)
        self._nav.setFont(font)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._nav)
        layout.addStretch()

        self._nav.currentIndexChanged.connect(self._on_index_changed)  # pyright: ignore[reportAttributeAccessIssue]

    # ---- public API (matches ActivityBar) ---------------------------------

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
        return list(self._item_ids)

    def addItem(self, item_id: str, text: str, *, icon: QIcon | None = None) -> None:
        if icon:
            self._nav.addItem(text, icon)
        else:
            self._nav.addItem(text)
        self._item_ids.append(item_id)

    def removeItem(self, item_id: str) -> None:
        """Remove an item from the bar. No-op if not present."""
        if item_id not in self._item_ids:
            return
        idx = self._item_ids.index(item_id)
        self._nav.removeItem(idx)
        self._item_ids.pop(idx)
        if self._active == item_id:
            self._active = None

    def setActive(self, item_id: str | None) -> None:
        """Programmatically activate (or deactivate) an item."""
        if item_id and item_id in self._item_ids:
            if self._active == item_id and self._collapsible:
                # Toggle off
                self.deselect()
                self.itemToggled.emit("")
            elif self._active != item_id:
                self.setActiveSilent(item_id)
                self.itemToggled.emit(item_id)
        elif not item_id and self._active and self._collapsible:
            self.deselect()
            self.itemToggled.emit("")

    def deselect(self) -> None:
        """Uncheck the active item without emitting itemToggled."""
        self._active = None
        self._nav.blockSignals(True)
        self._nav.setCurrentIndex(-1)
        self._nav.blockSignals(False)

    def activateFirst(self) -> None:
        """Activate the first item if any exist."""
        if self._item_ids:
            self.setActiveSilent(self._item_ids[0])
            self.itemToggled.emit(self._item_ids[0])

    def setActiveSilent(self, item_id: str) -> None:
        """Update selection without emitting itemToggled."""
        if item_id in self._item_ids:
            self._active = item_id
            idx = self._item_ids.index(item_id)
            self._nav.blockSignals(True)
            self._nav.setCurrentIndex(idx)
            self._nav.blockSignals(False)

    # ---- internals --------------------------------------------------------

    def _on_index_changed(self) -> None:
        index = self._nav.currentIndex()
        if 0 <= index < len(self._item_ids):
            item_id = self._item_ids[index]
            self._active = item_id
            self.itemToggled.emit(item_id)
