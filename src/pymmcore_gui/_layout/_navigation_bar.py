"""NavigationBar adapter that matches the ActivityBar interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pymmcore_gui._qt.Qlementine import NavigationBar  # type: ignore[attr-defined]
from pymmcore_gui._qt.QtCore import QMimeData, QPoint, QRect, Qt, Signal
from pymmcore_gui._qt.QtGui import QDrag, QIcon, QMouseEvent
from pymmcore_gui._qt.QtWidgets import QApplication, QHBoxLayout, QWidget

from ._dnd import PMM_VIEW_MIME_TYPE, decode_view_id, encode_view_id
from ._enums import NavDisplayMode

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import (
        QDragEnterEvent,
        QDragLeaveEvent,
        QDragMoveEvent,
        QDropEvent,
    )


class _DraggableNavigationBar(NavigationBar):
    """Private ``NavigationBar`` subclass that adds DnD mouse handling.

    Drag source: ``mousePressEvent``/``mouseMoveEvent`` detect a
    press-and-drag past the drag threshold on a specific item and emit
    :attr:`dragRequested` with that item's index. The enclosing
    :class:`NavigationBarAdapter` is responsible for looking up the
    view id for that index and creating the actual ``QDrag``.

    Drop target: ``dragEnter/Move/Leave/dropEvent`` accept drops
    carrying a ``PMM_VIEW_MIME_TYPE`` payload, compute the target
    insertion index using ``itemAtPos`` (exposed via our sip patch),
    and emit :attr:`viewDropped`.
    """

    dragRequested = Signal(int)
    viewDropped = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)  # pyright: ignore[reportCallIssue]
        self._drag_start_pos: QPoint | None = None
        self._drag_candidate_index: int = -1
        self.setAcceptDrops(True)

    # ---- drag source ------------------------------------------------------

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super().mousePressEvent(e)
        if e.button() != Qt.MouseButton.LeftButton:
            return
        idx = self.itemAtPos(e.pos())
        if idx < 0:
            self._drag_candidate_index = -1
            self._drag_start_pos = None
            return
        self._drag_candidate_index = idx
        self._drag_start_pos = e.pos()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        super().mouseMoveEvent(e)
        if not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_candidate_index < 0 or self._drag_start_pos is None:
            return
        delta = (e.pos() - self._drag_start_pos).manhattanLength()
        if delta < QApplication.startDragDistance():
            return
        idx = self._drag_candidate_index
        self._drag_candidate_index = -1
        self._drag_start_pos = None
        # Clear qlementine's internal pressed state so the item doesn't
        # look "stuck" after the drag completes.
        self.setPressedIndex(-1)
        self.dragRequested.emit(idx)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        super().mouseReleaseEvent(e)
        self._drag_candidate_index = -1
        self._drag_start_pos = None

    # ---- drop target ------------------------------------------------------

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()

    def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
        super().dragLeaveEvent(e)

    def dropEvent(self, e: QDropEvent) -> None:
        view_id = decode_view_id(e.mimeData())
        if view_id is None:
            e.ignore()
            return
        idx = self._compute_insert_index(e.position().toPoint())
        e.acceptProposedAction()
        self.viewDropped.emit(view_id, idx)

    def itemRect(self, index: int) -> QRect:
        """Return the bounding rect of item *index* in widget coordinates.

        Built on top of the sip-exposed ``itemAtPos`` — qlementine's
        C++ has no public ``itemRectAt``, so we scan horizontal pixel
        rows at the widget's vertical midline to find where that item's
        painted region starts and ends. Returns an empty ``QRect`` if
        the item isn't visible or the index is out of range.
        """
        if not (0 <= index < self.itemCount()):
            return QRect()
        mid_y = self.height() // 2
        left: int | None = None
        for x in range(self.width()):
            if int(self.itemAtPos(QPoint(x, mid_y))) == index:
                left = x
                break
        if left is None:
            return QRect()
        right = left
        for x in range(left + 1, self.width()):
            if int(self.itemAtPos(QPoint(x, mid_y))) == index:
                right = x
            else:
                if right > left:
                    break
        return QRect(left, 0, right - left + 1, self.height())

    def _compute_insert_index(self, pos: QPoint) -> int:
        """Return the insertion index for a drop at *pos*.

        Uses ``itemRect`` to find the hit item's horizontal midpoint
        so we can distinguish "drop before this item" from "drop
        after". If the cursor is outside any item but still inside
        the bar, we fall back to the nearest item to the left (if any)
        or the very beginning.
        """
        count = self.itemCount()
        if count == 0:
            return 0

        hit = int(self.itemAtPos(pos))

        if hit >= 0:
            rect = self.itemRect(hit)
            if rect.isEmpty():
                return hit
            midpoint = rect.x() + rect.width() // 2
            return hit if pos.x() < midpoint else hit + 1

        # Not on any item — look leftward for the nearest item and
        # insert after it. Otherwise we're before all items.
        mid_y = self.height() // 2
        for x in range(min(pos.x(), self.width() - 1), -1, -1):
            idx = int(self.itemAtPos(QPoint(x, mid_y)))
            if idx >= 0:
                return idx + 1
        return 0


class NavigationBarAdapter(QWidget):
    """Wraps Qlementine's NavigationBar with the same interface as ActivityBar."""

    itemToggled = Signal(str)  # item_id, or "" to collapse
    itemDropped = Signal(str, int)  # (view_id, target_insert_index)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._nav = _DraggableNavigationBar(self)
        self._nav.setFixedHeight(32)
        self._nav.setItemsShouldExpand(False)
        self._item_ids: list[str] = []
        # Cache text + icon per id so we can rebuild the inner qlementine
        # bar on insert/move — its C++ API currently has no insertItem.
        self._item_meta: dict[str, tuple[str, QIcon | None]] = {}
        self._active: str | None = None
        self._collapsible = True
        self._display_mode: NavDisplayMode = NavDisplayMode.BOTH

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

        # Accept drops on the whole adapter widget (not just the inner
        # bar) so drops that land in the stretch area after the last
        # tab also work — otherwise the user has a dead zone to the
        # right of the last tab. Drops there append to the end of the
        # bar; drops *on* the inner nav still go through its precise
        # insertion-index computation.
        self.setAcceptDrops(True)

        self._nav.currentIndexChanged.connect(self._on_index_changed)  # pyright: ignore[reportAttributeAccessIssue]
        self._nav.dragRequested.connect(self._on_drag_requested)
        self._nav.viewDropped.connect(self.itemDropped)

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

    @property
    def displayMode(self) -> NavDisplayMode:
        return self._display_mode

    def setDisplayMode(self, mode: NavDisplayMode) -> None:
        """Set how items are rendered: text only, icons only, or both.

        Rewrites every slot's text/icon via in-place setters; the
        cached metadata in ``self._item_meta`` is the source of truth
        and is never lost, so flipping between modes is reversible.
        """
        if mode == self._display_mode:
            return
        self._display_mode = mode
        self._apply_display_mode()

    def _effective_text_icon(self, iid: str) -> tuple[str, QIcon]:
        """Return the (text, icon) to push to qlementine for *iid*.

        Honors the current display mode — ``QIcon()`` (empty) for
        ``TEXT_ONLY`` and ``""`` (empty string) for ``ICONS_ONLY``.
        """
        text, icon = self._item_meta[iid]
        real_icon = icon if icon is not None else QIcon()
        if self._display_mode == NavDisplayMode.TEXT_ONLY:
            return text, QIcon()
        if self._display_mode == NavDisplayMode.ICONS_ONLY:
            return "", real_icon
        return text, real_icon

    def _apply_display_mode(self) -> None:
        """Push the current display mode's (text, icon) to every slot."""
        self._nav.blockSignals(True)
        try:
            for i, iid in enumerate(self._item_ids):
                text, icon = self._effective_text_icon(iid)
                self._nav.setItemText(i, text)
                self._nav.setItemIcon(i, icon)
        finally:
            self._nav.blockSignals(False)
        self._nav.updateGeometry()
        self._nav.update()

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
        ``AbstractItemListWidget`` has no native ``insertItem``, we always
        append the new item first (a safe op), then use in-place
        ``setItemText``/``setItemIcon`` calls to shuffle existing slots
        into the requested order.
        """
        if item_id in self._item_ids:
            raise ValueError(f"Item {item_id!r} already exists")
        count = len(self._item_ids)
        clamped = max(0, min(index, count))

        # Record the real (text, icon) in the cache first — _effective_text_icon
        # reads from it.
        self._item_meta[item_id] = (text, icon)

        # Append to qlementine's bar (a clean op that doesn't disturb
        # existing items or animations). Push the mode-adjusted values
        # so the new item respects the current display mode.
        display_text, display_icon = self._effective_text_icon(item_id)
        self._nav.addItem(display_text, display_icon)

        if clamped == count:
            # Append — already in the right position.
            self._item_ids.append(item_id)
            return

        # Need to shuffle the new item from the end to `clamped`.
        new_ids = list(self._item_ids)
        new_ids.insert(clamped, item_id)
        self._item_ids.append(item_id)  # so _update_in_place's count check passes
        self._update_in_place(new_ids)

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
        self._update_in_place(new_ids)

    def _update_in_place(self, new_ids: list[str]) -> None:
        """Reorder qlementine slots in place via setItemText/setItemIcon.

        Caller guarantees ``len(new_ids) == self._nav.itemCount()``.
        This avoids the destructive remove-all + add-all path, which
        was triggering a qlementine animation/currentIndex bug where
        the bar would visibly disappear after a reorder past index 0.
        Items in the C++ ``_items`` vector keep their identity (and
        their animation objects); only the text, icon, and our parallel
        ``_item_ids`` list change to reflect the new logical ordering.
        """
        if self._nav.itemCount() != len(new_ids):
            return
        active = self._active
        self._item_ids = list(new_ids)
        self._nav.blockSignals(True)
        try:
            for i, iid in enumerate(new_ids):
                display_text, display_icon = self._effective_text_icon(iid)
                self._nav.setItemText(i, display_text)
                # setItemIcon must always be called (even with empty icon)
                # to clear any leftover icon from the slot's previous role.
                self._nav.setItemIcon(i, display_icon)
            if active and active in new_ids:
                self._nav.setCurrentIndex(new_ids.index(active))
        finally:
            self._nav.blockSignals(False)
        self._nav.update()

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

    # ---- drop target (stretch area beside the inner bar) -----------------
    #
    # Drops that land on the inner ``_DraggableNavigationBar`` go
    # through its own ``dropEvent`` (which computes a precise
    # insertion index). These overrides fire only for drops that land
    # in the adapter's *stretch* region — the empty horizontal space
    # after the last tab — and append to the end of the bar.

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent) -> None:
        view_id = decode_view_id(e.mimeData())
        if view_id is None:
            e.ignore()
            return
        e.acceptProposedAction()
        self.itemDropped.emit(view_id, len(self._item_ids))

    # ---- internals --------------------------------------------------------

    def _on_index_changed(self) -> None:
        index = self._nav.currentIndex()
        if 0 <= index < len(self._item_ids):
            item_id = self._item_ids[index]
            self._active = item_id
            self.itemToggled.emit(item_id)

    def _on_drag_requested(self, index: int) -> None:
        """Build and execute a QDrag for the item at *index*.

        The inner ``_DraggableNavigationBar`` detected a press+drag on
        this item; we turn that into a real ``QDrag`` carrying the
        view id payload. ``QDrag.exec`` is modal — it blocks until the
        user drops or cancels.

        The drag preview pixmap is just the bounding rect of the
        dragged item (computed via ``itemRect``) — *not* the whole
        nav bar — so the user sees only the tab they grabbed follow
        the cursor.
        """
        if not (0 <= index < len(self._item_ids)):
            return
        view_id = self._item_ids[index]
        drag = QDrag(self._nav)
        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id(view_id))
        drag.setMimeData(mime)
        rect = self._nav.itemRect(index)
        if not rect.isEmpty():
            pixmap = self._nav.grab(rect)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)
