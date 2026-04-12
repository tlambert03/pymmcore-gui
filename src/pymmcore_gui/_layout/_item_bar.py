"""Single hand-rolled bar widget that replaces qlementine's NavigationBar.

A :class:`ItemBar` is a mutually-exclusive list of items that paints
itself directly (no child widgets, no QFocusFrame). It supports both
vertical and horizontal orientations behind a single API and provides
the union of behaviors needed by the workbench:

- Add / insert / remove / move / setText / setIcon
- Mutually exclusive selection with optional collapse-on-click
- Animated selection indicator (3px line) interpolating between items
- Display modes (text only, icons only, both) — applies in both
  orientations
- Drag source (press + move past threshold → ``QDrag``)
- Drop target (computes precise insertion index, shows drop indicator)

Why a hand-rolled widget instead of subclassing qlementine? Heavy
runtime mutation, cross-container DnD, and our custom display modes
were colliding with several qlementine internals (QFocusFrame
positioning, animation state corruption on destructive rebuilds, sip
binding gaps). Owning the paint loop directly avoids the entire class
of those issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymmcore_gui._qt.Qlementine import utils as qlem_utils
from pymmcore_gui._qt.QtCore import (
    QEasingCurve,
    QMimeData,
    QPoint,
    QRect,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from pymmcore_gui._qt.QtGui import (
    QColor,
    QDrag,
    QFontMetrics,
    QIcon,
    QPainter,
    QPalette,
)
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QSizePolicy,
    QStyle,
    QWidget,
)

from ._dnd import PMM_VIEW_MIME_TYPE, decode_view_id, encode_view_id
from ._drop_indicator import DropIndicator
from ._enums import NavDisplayMode

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtGui import (
        QDragEnterEvent,
        QDragLeaveEvent,
        QDragMoveEvent,
        QDropEvent,
        QMouseEvent,
        QPaintEvent,
        QResizeEvent,
    )


# Default item icon size
_ICON_SIZE_V = 26
_ICON_SIZE_H = 16

# Selection indicator thickness in pixels.
_INDICATOR_THICKNESS = 3

# Default item padding (l, t, r, b).
_ITEM_PAD_H = 12  # horizontal padding inside an item
_ITEM_PAD_V = 6  # vertical padding inside an item

# Spacing between icon and text.
_ICON_TEXT_SPACING = 6

# Click area pad (for hit testing) — slightly forgiving on edges.
_HIT_PAD = 2


@dataclass
class _Item:
    """Internal item record. Position is set by :meth:`ItemBar._layout_items`."""

    id: str
    text: str
    icon: QIcon | None
    rect: QRect = field(default_factory=QRect)
    size_hint: QSize = field(default_factory=QSize)


# TODO: remove me.
def _theme_colors(
    widget: QWidget,
) -> tuple[QColor, QColor, QColor, QColor, QColor, QColor]:
    """Return ``(bg, bg_hover, bg_pressed, fg, fg_disabled, indicator)``.

    Tries to read from the active QlementineStyle theme; falls back to
    palette colors if a different style is in use, so the widget still
    renders sensibly under any QStyle.
    """
    pal = widget.palette()
    fallback_bg = pal.color(QPalette.ColorRole.Base)
    fallback_bg_hover = pal.color(QPalette.ColorRole.AlternateBase)
    fallback_bg_pressed = pal.color(QPalette.ColorRole.Mid)
    fallback_fg = pal.color(QPalette.ColorRole.WindowText)
    fallback_fg_disabled = pal.color(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText
    )
    fallback_indicator = pal.color(QPalette.ColorRole.Highlight)

    style = widget.style()
    theme = getattr(style, "theme", None)
    if theme is None:
        return (
            fallback_bg,
            fallback_bg_hover,
            fallback_bg_pressed,
            fallback_fg,
            fallback_fg_disabled,
            fallback_indicator,
        )
    try:
        t = theme()
    except Exception:
        return (
            fallback_bg,
            fallback_bg_hover,
            fallback_bg_pressed,
            fallback_fg,
            fallback_fg_disabled,
            fallback_indicator,
        )

    def _attr(name: str, fallback: QColor) -> QColor:
        c = getattr(t, name, None)
        return c if isinstance(c, QColor) else fallback

    return (
        _attr("backgroundColorMain2", fallback_bg),
        _attr("backgroundColorMain3", fallback_bg_hover),
        _attr("backgroundColorMain4", fallback_bg_pressed),
        _attr("secondaryColor", fallback_fg),
        _attr("secondaryColorDisabled", fallback_fg_disabled),
        _attr("primaryColor", fallback_indicator),
    )


class ItemBar(QWidget):
    """Mutually exclusive list of items, vertical or horizontal."""

    itemToggled = Signal(str)
    """Emitted with the new active id, or ``""`` if the bar collapsed."""

    itemDropped = Signal(str, int)
    """Emitted on drop: ``(view_id, target_insertion_index)``."""

    def __init__(
        self,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._orientation = orientation
        self._items: list[_Item] = []
        self._active_id: str | None = None
        self._hovered_index: int = -1
        self._pressed_index: int = -1
        self._collapsible: bool = True
        # Default display mode mirrors what the workbench expects:
        # icon-only for vertical (sidebar activity bars), text-only for
        # horizontal (top/bottom navigation bars).
        if orientation == Qt.Orientation.Vertical:
            self._display_mode = NavDisplayMode.ICONS_ONLY
        else:
            self._display_mode = NavDisplayMode.TEXT_ONLY

        # Drag-source state.
        self._drag_start_pos: QPoint | None = None
        self._drag_candidate_index: int = -1

        # Selection indicator animation interpolates a QRect from the
        # previous active-item rect to the new one.
        self._indicator_anim = QVariantAnimation(self)
        self._indicator_anim.setDuration(
            self.style().styleHint(QStyle.StyleHint.SH_Widget_Animation_Duration) or 200
        )
        self._indicator_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._indicator_anim.valueChanged.connect(lambda _v: self.update())

        # Drop indicator overlay (parented to self, transparent to mouse).
        self._drop_indicator = DropIndicator(self, orientation)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        if orientation == Qt.Orientation.Vertical:
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ---- public API -------------------------------------------------------

    def orientation(self) -> Qt.Orientation:
        return self._orientation

    def activeItem(self) -> str | None:
        return self._active_id

    def isCollapsible(self) -> bool:
        return self._collapsible

    def setCollapsible(self, value: bool) -> None:
        self._collapsible = value

    def itemIds(self) -> list[str]:
        return [it.id for it in self._items]

    def displayMode(self) -> NavDisplayMode:
        return self._display_mode

    def setDisplayMode(self, mode: NavDisplayMode) -> None:
        """Switch how items are rendered (text/icons/both)."""
        if mode == self._display_mode:
            return
        self._display_mode = mode
        self._invalidate_layout()
        self.updateGeometry()
        self.update()

    # -- item management --

    def addItem(self, item_id: str, text: str, *, icon: QIcon | None = None) -> None:
        """Append an item."""
        self.insertItem(len(self._items), item_id, text, icon=icon)

    def insertItem(
        self,
        index: int,
        item_id: str,
        text: str,
        *,
        icon: QIcon | None = None,
    ) -> None:
        """Insert an item at *index*; clamps into ``[0, count]``."""
        if any(it.id == item_id for it in self._items):
            raise ValueError(f"Item {item_id!r} already exists")
        clamped = max(0, min(index, len(self._items)))
        self._items.insert(clamped, _Item(id=item_id, text=text, icon=icon))
        self._invalidate_layout()
        self.updateGeometry()
        self.update()

    def removeItem(self, item_id: str) -> None:
        """Remove an item; no-op if absent."""
        for i, it in enumerate(self._items):
            if it.id == item_id:
                self._items.pop(i)
                if self._active_id == item_id:
                    self._active_id = None
                # Cancel any drag-candidate state pointing at this item.
                if self._pressed_index == i:
                    self._pressed_index = -1
                if self._hovered_index == i:
                    self._hovered_index = -1
                self._invalidate_layout()
                self.updateGeometry()
                self.update()
                return

    def moveItem(self, old_index: int, new_index: int) -> None:
        """Move the item at *old_index* to *new_index*."""
        count = len(self._items)
        if not (0 <= old_index < count):
            raise IndexError(f"old_index out of range: {old_index}")
        new_index = max(0, min(new_index, count - 1))
        if old_index == new_index:
            return
        item = self._items.pop(old_index)
        self._items.insert(new_index, item)
        self._invalidate_layout()
        self.update()

    def setItemText(self, item_id: str, text: str) -> None:
        for it in self._items:
            if it.id == item_id:
                it.text = text
                self._invalidate_layout()
                self.updateGeometry()
                self.update()
                return

    def setItemIcon(self, item_id: str, icon: QIcon | None) -> None:
        for it in self._items:
            if it.id == item_id:
                it.icon = icon
                self._invalidate_layout()
                self.updateGeometry()
                self.update()
                return

    # -- selection --

    def setActive(self, item_id: str | None) -> None:
        """Activate (or, if collapsible, toggle) an item."""
        if item_id:
            self._toggle(item_id)
        elif self._active_id and self._collapsible:
            self._toggle(self._active_id)

    def setActiveSilent(self, item_id: str | None) -> None:
        """Update the active id without emitting :attr:`itemToggled`."""
        if item_id is None:
            self._active_id = None
        elif any(it.id == item_id for it in self._items):
            old_rect = self._active_rect()
            self._active_id = item_id
            self._animate_indicator(old_rect, self._active_rect())
        self.update()

    def deselect(self) -> None:
        """Clear active selection without emitting any signal."""
        self._active_id = None
        self.update()

    def activateFirst(self) -> None:
        """Activate the first item if any exist (emits :attr:`itemToggled`)."""
        if not self._items:
            return
        first = self._items[0].id
        self._activate_without_collapse(first)

    # -- hit testing --

    def itemAt(self, pos: QPoint) -> int:
        """Return the index of the item at *pos*, or ``-1`` if none."""
        for i, it in enumerate(self._items):
            if it.rect.adjusted(-_HIT_PAD, -_HIT_PAD, _HIT_PAD, _HIT_PAD).contains(pos):
                return i
        return -1

    def itemRect(self, index: int) -> QRect:
        """Return the bounding rect of item *index* in widget coordinates."""
        if 0 <= index < len(self._items):
            return QRect(self._items[index].rect)
        return QRect()

    # ---- internals --------------------------------------------------------

    def _toggle(self, item_id: str) -> None:
        if self._active_id == item_id:
            if not self._collapsible:
                return
            self._active_id = None
            self.update()
            self.itemToggled.emit("")
        else:
            old_rect = self._active_rect()
            self._active_id = item_id
            self._animate_indicator(old_rect, self._active_rect())
            self.update()
            self.itemToggled.emit(item_id)

    def _activate_without_collapse(self, item_id: str) -> None:
        old_rect = self._active_rect()
        self._active_id = item_id
        self._animate_indicator(old_rect, self._active_rect())
        self.update()
        self.itemToggled.emit(item_id)

    def _active_rect(self) -> QRect:
        if self._active_id is None:
            return QRect()
        for it in self._items:
            if it.id == self._active_id:
                return self._indicator_rect_for(it.rect)
        return QRect()

    def _indicator_rect_for(self, item_rect: QRect) -> QRect:
        """Return the indicator's geometry for an item with *item_rect*.

        Vertical bars draw a left bar; horizontal bars draw a bottom underline.
        """
        if self._orientation == Qt.Orientation.Vertical:
            return QRect(0, item_rect.y(), _INDICATOR_THICKNESS, item_rect.height())
        return QRect(
            item_rect.x(),
            item_rect.y() + item_rect.height() - _INDICATOR_THICKNESS,
            item_rect.width(),
            _INDICATOR_THICKNESS,
        )

    def _animate_indicator(self, start: QRect, end: QRect) -> None:
        if start.isEmpty() or end.isEmpty():
            self._indicator_anim.stop()
            return
        self._indicator_anim.stop()
        self._indicator_anim.setStartValue(start)
        self._indicator_anim.setEndValue(end)
        self._indicator_anim.start()

    # ---- layout ----------------------------------------------------------

    def _invalidate_layout(self) -> None:
        """Mark size hints stale; the next paint/resize will recompute."""
        for it in self._items:
            it.size_hint = QSize()
            it.rect = QRect()

    def _ensure_size_hints(self) -> None:
        if not self._items:
            return
        if all(it.size_hint.isValid() for it in self._items):
            return
        fm = QFontMetrics(self.font())
        text_h = fm.height()
        icon_size = (
            _ICON_SIZE_V
            if self._orientation == Qt.Orientation.Vertical
            else _ICON_SIZE_H
        )
        for it in self._items:
            display_text = self._effective_text(it)
            display_icon = self._effective_icon(it)
            content_w = 0
            content_h = 0
            if not display_icon.isNull():
                content_w += icon_size
                content_h = max(content_h, icon_size)
            if display_text:
                if content_w > 0:
                    content_w += _ICON_TEXT_SPACING
                content_w += fm.horizontalAdvance(display_text)
                content_h = max(content_h, text_h)
            it.size_hint = QSize(
                content_w + _ITEM_PAD_H * 2,
                content_h + _ITEM_PAD_V * 2,
            )

    def _layout_items(self) -> None:
        """Recompute every item's ``rect`` based on current size."""
        self._ensure_size_hints()
        if not self._items:
            return
        if self._orientation == Qt.Orientation.Vertical:
            y = 0
            width = self.width()
            for it in self._items:
                h = it.size_hint.height()
                it.rect = QRect(0, y, width, h)
                y += h
        else:
            x = 0
            height = self.height()
            for it in self._items:
                w = it.size_hint.width()
                it.rect = QRect(x, 0, w, height)
                x += w

    def _effective_text(self, item: _Item) -> str:
        if self._display_mode == NavDisplayMode.ICONS_ONLY:
            return ""
        return item.text

    def _effective_icon(self, item: _Item) -> QIcon:
        if self._display_mode == NavDisplayMode.TEXT_ONLY:
            return QIcon()
        return item.icon if item.icon is not None else QIcon()

    def sizeHint(self) -> QSize:
        self._ensure_size_hints()
        if not self._items:
            return (
                QSize(40, 40)
                if self._orientation == Qt.Orientation.Vertical
                else QSize(40, 32)
            )
        if self._orientation == Qt.Orientation.Vertical:
            w = max(it.size_hint.width() for it in self._items)
            h = sum(it.size_hint.height() for it in self._items)
            return QSize(w, h)
        w = sum(it.size_hint.width() for it in self._items)
        h = max(it.size_hint.height() for it in self._items)
        return QSize(w, h)

    def minimumSizeHint(self) -> QSize:
        self._ensure_size_hints()
        if not self._items:
            return QSize(20, 20)
        if self._orientation == Qt.Orientation.Vertical:
            w = max(it.size_hint.width() for it in self._items)
            h = max(it.size_hint.height() for it in self._items)
            return QSize(w, h)
        w = max(it.size_hint.width() for it in self._items)
        h = max(it.size_hint.height() for it in self._items)
        return QSize(w, h)

    # ---- paint -----------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout_items()

    def paintEvent(self, event: QPaintEvent) -> None:
        # Make sure rects are up to date in case we paint before a resize.
        if self._items and any(r.rect.isEmpty() for r in self._items):
            self._layout_items()

        bg, bg_hover, bg_pressed, fg, fg_disabled, indicator_color = _theme_colors(self)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), bg)

        icon_size = (
            _ICON_SIZE_V
            if self._orientation == Qt.Orientation.Vertical
            else _ICON_SIZE_H
        )
        for i, it in enumerate(self._items):
            if it.rect.isEmpty():
                continue
            # Background per state
            if i == self._pressed_index:
                painter.fillRect(it.rect, bg_pressed)
            elif i == self._hovered_index:
                painter.fillRect(it.rect, bg_hover)

            display_text = self._effective_text(it)
            display_icon = self._effective_icon(it)

            content_w = 0
            if not display_icon.isNull():
                content_w += icon_size
            if display_text:
                if content_w > 0:
                    content_w += _ICON_TEXT_SPACING
                content_w += QFontMetrics(self.font()).horizontalAdvance(display_text)

            x = it.rect.x() + (it.rect.width() - content_w) // 2
            y_center = it.rect.y() + it.rect.height() // 2

            if not display_icon.isNull():
                # Tint to match the active foreground color so icons
                # respect dark/light themes — same helper qlementine
                # uses internally for AutoIconColor.ForegroundColor.
                pix = display_icon.pixmap(icon_size, icon_size)
                if it.id == self._active_id:
                    pix = qlem_utils.getColorizedPixmap(pix, fg)
                else:
                    pix = qlem_utils.getColorizedPixmap(pix, fg_disabled)
                painter.drawPixmap(
                    x,
                    y_center - icon_size // 2,
                    pix,
                )
                x += icon_size
                if display_text:
                    x += _ICON_TEXT_SPACING

            if display_text:
                painter.setPen(fg)
                fm = QFontMetrics(self.font())
                text_h = fm.height()
                text_rect = QRect(
                    x,
                    y_center - text_h // 2,
                    it.rect.x() + it.rect.width() - x - _ITEM_PAD_H // 2,
                    text_h,
                )
                elided = fm.elidedText(
                    display_text, Qt.TextElideMode.ElideRight, text_rect.width()
                )
                painter.drawText(
                    text_rect,
                    int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                    elided,
                )

        # Selection indicator (animated). Use the live animation value if
        # the animation is running; otherwise the steady-state rect for
        # the active item.
        indicator_rect = QRect()
        if self._indicator_anim.state() == self._indicator_anim.State.Running:
            v = self._indicator_anim.currentValue()
            if isinstance(v, QRect):
                indicator_rect = v
        else:
            indicator_rect = self._active_rect()

        if not indicator_rect.isEmpty():
            painter.fillRect(indicator_rect, indicator_color)

    # ---- mouse events ----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self.itemAt(event.pos())
        if idx < 0:
            self._pressed_index = -1
            self._drag_candidate_index = -1
            self._drag_start_pos = None
            return
        self._pressed_index = idx
        self._drag_candidate_index = idx
        self._drag_start_pos = event.pos()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        # Hover tracking
        new_hover = self.itemAt(event.pos())
        if new_hover != self._hovered_index:
            self._hovered_index = new_hover
            self.update()

        # Drag detection
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_candidate_index < 0 or self._drag_start_pos is None:
            return
        delta = (event.pos() - self._drag_start_pos).manhattanLength()
        if delta < QApplication.startDragDistance():
            return
        candidate = self._items[self._drag_candidate_index]
        self._drag_candidate_index = -1
        self._drag_start_pos = None
        self._pressed_index = -1
        self.update()
        self._start_drag(candidate.id)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self.itemAt(event.pos())
        was_pressed = self._pressed_index
        self._pressed_index = -1
        self._drag_candidate_index = -1
        self._drag_start_pos = None
        self.update()
        if idx >= 0 and idx == was_pressed:
            self._toggle(self._items[idx].id)

    def leaveEvent(self, event: object) -> None:
        super().leaveEvent(event)  # type: ignore[arg-type]
        if self._hovered_index != -1:
            self._hovered_index = -1
            self.update()

    # ---- drag source -----------------------------------------------------

    def _start_drag(self, item_id: str) -> None:
        idx = next((i for i, it in enumerate(self._items) if it.id == item_id), -1)
        if idx < 0:
            return
        rect = self._items[idx].rect
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(PMM_VIEW_MIME_TYPE, encode_view_id(item_id))
        drag.setMimeData(mime)
        if not rect.isEmpty():
            pix = self.grab(rect)
            drag.setPixmap(pix)
            drag.setHotSpot(QPoint(pix.width() // 2, pix.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    # ---- drop target -----------------------------------------------------

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        e.acceptProposedAction()
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_indicator.showAt(self._drop_indicator_position(index))

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        if decode_view_id(e.mimeData()) is None:
            e.ignore()
            return
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_indicator.showAt(self._drop_indicator_position(index))
        e.acceptProposedAction()

    def dragLeaveEvent(self, e: QDragLeaveEvent) -> None:
        self._drop_indicator.hide()
        super().dragLeaveEvent(e)

    def dropEvent(self, e: QDropEvent) -> None:
        view_id = decode_view_id(e.mimeData())
        if view_id is None:
            e.ignore()
            return
        index = self._compute_insert_index(e.position().toPoint())
        self._drop_indicator.hide()
        e.acceptProposedAction()
        self.itemDropped.emit(view_id, index)

    def _compute_insert_index(self, pos: QPoint) -> int:
        """Return the insertion index a drop at *pos* would land on.

        Walks items in order, returning the index of the first one whose
        center is past *pos* along the bar's primary axis. Past all
        items → append at the end.
        """
        if not self._items:
            return 0
        vertical = self._orientation == Qt.Orientation.Vertical
        for i, it in enumerate(self._items):
            if it.rect.isEmpty():
                continue
            if vertical:
                midpoint = it.rect.y() + it.rect.height() // 2
                if pos.y() < midpoint:
                    return i
            else:
                midpoint = it.rect.x() + it.rect.width() // 2
                if pos.x() < midpoint:
                    return i
        return len(self._items)

    def _drop_indicator_position(self, index: int) -> int:
        """Primary-axis coordinate for the drop indicator at *index*."""
        count = len(self._items)
        vertical = self._orientation == Qt.Orientation.Vertical
        if count == 0:
            return 0
        clamped = max(0, min(index, count))
        if clamped == 0:
            r = self._items[0].rect
            return r.y() if vertical else r.x()
        if clamped == count:
            r = self._items[-1].rect
            return (r.y() + r.height()) if vertical else (r.x() + r.width())
        above = self._items[clamped - 1].rect
        below = self._items[clamped].rect
        if vertical:
            return (above.y() + above.height() + below.y()) // 2
        return (above.x() + above.width() + below.x()) // 2
