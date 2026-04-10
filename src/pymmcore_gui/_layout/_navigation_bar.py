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
        # Cache text + icon per id so we can rebuild the inner qlementine
        # bar on insert/move — its C++ API currently has no insertItem.
        self._item_meta: dict[str, tuple[str, QIcon | None]] = {}
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
        """Append an item to the end of the bar."""
        self.insertItem(len(self._item_ids), item_id, text, icon=icon)

    def insertItem(
        self,
        index: int,
        item_id: str,
        text: str,
        *,
        icon: QIcon | None = None,
    ) -> None:
        """Insert an item at *index*.

        ``index`` is clamped into ``[0, item_count]``. Because qlementine's
        ``AbstractItemListWidget`` has no native ``insertItem``, inserting
        anywhere other than the end triggers a full rebuild of the inner
        ``NavigationBar`` from cached metadata.
        """
        if item_id in self._item_ids:
            raise ValueError(f"Item {item_id!r} already exists")
        count = len(self._item_ids)
        clamped = max(0, min(index, count))

        if clamped == count:
            # Append — no rebuild needed.
            if icon:
                self._nav.addItem(text, icon)
            else:
                self._nav.addItem(text)
            self._item_ids.append(item_id)
            self._item_meta[item_id] = (text, icon)
            return

        new_ids = list(self._item_ids)
        new_ids.insert(clamped, item_id)
        self._item_meta[item_id] = (text, icon)
        self._rebuild_from_order(new_ids)

    def removeItem(self, item_id: str) -> None:
        """Remove an item from the bar. No-op if not present."""
        if item_id not in self._item_ids:
            return
        idx = self._item_ids.index(item_id)
        self._nav.removeItem(idx)
        self._item_ids.pop(idx)
        self._item_meta.pop(item_id, None)
        if self._active == item_id:
            self._active = None

    def moveItem(self, old_index: int, new_index: int) -> None:
        """Move the item at *old_index* to *new_index*."""
        count = len(self._item_ids)
        if not (0 <= old_index < count):
            raise IndexError(f"old_index out of range: {old_index}")
        new_index = max(0, min(new_index, count - 1))
        if old_index == new_index:
            return

        new_ids = list(self._item_ids)
        item = new_ids.pop(old_index)
        new_ids.insert(new_index, item)
        self._rebuild_from_order(new_ids)

    def _rebuild_from_order(self, new_ids: list[str]) -> None:
        """Tear down and rebuild the inner NavigationBar from *new_ids*.

        Used for insert-at-middle and move operations since qlementine's
        ``AbstractItemListWidget`` exposes only append + remove. Active
        selection is preserved by id.
        """
        active = self._active
        self.setUpdatesEnabled(False)
        self._nav.blockSignals(True)
        try:
            while self._nav.itemCount() > 0:
                self._nav.removeItem(0)
            self._item_ids = []
            for iid in new_ids:
                text, icon = self._item_meta[iid]
                if icon:
                    self._nav.addItem(text, icon)
                else:
                    self._nav.addItem(text)
                self._item_ids.append(iid)
            if active and active in self._item_ids:
                self._nav.setCurrentIndex(self._item_ids.index(active))
            else:
                self._active = None
                self._nav.setCurrentIndex(-1)
        finally:
            self._nav.blockSignals(False)
            self.setUpdatesEnabled(True)

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
