from __future__ import annotations

from dataclasses import dataclass

from pymmcore_gui._qt.QtCore import QPoint, Qt, Signal
from pymmcore_gui._qt.QtGui import QAction, QActionGroup, QIcon
from pymmcore_gui._qt.QtWidgets import (
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ._activity_bar import ActivityBar
from ._enums import ActivityBarPosition
from ._navigation_bar import NavigationBarAdapter
from ._splitter_utils import (
    DEFAULT_SIDEBAR_WIDTH,
    MIN_SIDEBAR_WIDTH,
    ensure_splitter_size,
    splitter_size,
)


@dataclass
class _ViewEntry:
    """Cached per-view data a container needs to re-render bar items.

    Held by the container so that :meth:`PaneContainer._ensure_correct_bar_type`
    can reconstruct bar items on orientation swap without reaching into the
    old bar's internals for title/icon.
    """

    widget: QWidget
    title: str
    icon: QIcon | None


class PaneContainer(QWidget):
    """One workbench region: activity bar + stacked view widgets.

    In VS Code terms this plays the role of a ``ViewContainer`` (or more
    precisely a ``ViewContainer`` backed by a ``ViewPaneContainer`` with
    ``mergeViewWithContainerWhenSingleView: true``) — a container that
    holds one or more views and shows them one at a time via a tab strip.

    The container is deliberately *dumb*: it doesn't know about
    :class:`ViewRegistry`. The caller passes widgets in and the container
    just draws them. The registry/workbench is the mediator.
    """

    viewToggled = Signal(str)  # forwarded from activityBar
    viewDropped = Signal(str, int)  # (view_id, target_insert_index), forwarded
    abPositionChanged = Signal(ActivityBarPosition)

    def __init__(
        self,
        *,
        default_ab_position: str = "side",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._views: dict[str, _ViewEntry] = {}
        self._default_ab_position = default_ab_position
        self._ab_position = ActivityBarPosition.DEFAULT

        self._stack.setMinimumWidth(MIN_SIDEBAR_WIDTH)

        # Combined container for top/bottom activity bar positions
        self._combined = QWidget()
        self._combined.setMinimumWidth(MIN_SIDEBAR_WIDTH)
        self._combined_layout = QVBoxLayout(self._combined)
        self._combined_layout.setContentsMargins(0, 0, 0, 0)
        self._combined_layout.setSpacing(0)

        # Create initial activity bar based on default position
        self._activity_bar: ActivityBar | NavigationBarAdapter = self._make_bar()
        self._wire_bar()

        # Enable context menu on stack
        self._stack.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._stack.customContextMenuRequested.connect(self._show_context_menu_stack)

    # ---- public API -------------------------------------------------------

    @property
    def activityBar(self) -> ActivityBar | NavigationBarAdapter:
        return self._activity_bar

    @property
    def stack(self) -> QStackedWidget:
        return self._stack

    @property
    def viewIds(self) -> list[str]:
        """View ids in display order."""
        return list(self._views)

    @property
    def resolvedAbPosition(self) -> str:
        """Return effective position: 'side', 'top', 'bottom', or 'hidden'."""
        if self._ab_position == ActivityBarPosition.DEFAULT:
            return self._default_ab_position
        return str(self._ab_position.value)

    @property
    def isAbExternal(self) -> bool:
        return self.resolvedAbPosition == "side"

    @property
    def splitterWidget(self) -> QWidget:
        """The widget to place into a splitter."""
        if self.resolvedAbPosition in ("top", "bottom"):
            return self._combined
        return self._stack

    @property
    def isCollapsed(self) -> bool:
        w = self.splitterWidget
        return not w.isVisible() or splitter_size(w) == 0

    def setAbPosition(self, pos: ActivityBarPosition) -> None:
        self._ab_position = pos

    def arrange(self) -> None:
        """Rearrange activity bar and stack for current position."""
        pos = self.resolvedAbPosition

        # Swap bar type if needed (vertical ↔ horizontal)
        self._ensure_correct_bar_type()

        self._activity_bar.setParent(None)
        self._stack.setParent(None)

        self._activity_bar.collapsible = pos == "side"

        if pos == "top":
            self._combined_layout.addWidget(self._activity_bar)
            self._combined_layout.addWidget(self._stack, 1)
            self._activity_bar.show()
        elif pos == "bottom":
            self._combined_layout.addWidget(self._stack, 1)
            self._combined_layout.addWidget(self._activity_bar)
            self._activity_bar.show()
        elif pos == "side":
            self._activity_bar.show()
        else:  # hidden
            self._activity_bar.hide()

    def addView(
        self,
        view_id: str,
        title: str,
        widget: QWidget,
        *,
        icon: QIcon | None = None,
        index: int | None = None,
    ) -> None:
        """Add a view to this container.

        Called by :class:`WorkbenchWidget` in response to
        :attr:`ViewRegistry.view_registered` (and, for cross-container
        moves, :attr:`ViewRegistry.view_moved`). The ``widget`` is the
        view pane from the registry; this container does not own its
        lifetime beyond reparenting.

        If *index* is ``None`` the view is appended. Otherwise it is
        inserted at that position in both the activity bar and the
        stacked widget, and ``self._views`` is re-keyed to match.
        """
        if view_id in self._views:
            raise ValueError(f"View {view_id!r} already in this container")

        count = len(self._views)
        if index is None or index >= count:
            # Append — simple path.
            self._activity_bar.addItem(view_id, title, icon=icon)
            self._stack.addWidget(widget)
            self._views[view_id] = _ViewEntry(widget=widget, title=title, icon=icon)
            return

        clamped = max(0, index)
        self._activity_bar.insertItem(clamped, view_id, title, icon=icon)
        self._stack.insertWidget(clamped, widget)

        # Rebuild _views with the new entry inserted at `clamped` so
        # iteration order matches visual order.
        entry = _ViewEntry(widget=widget, title=title, icon=icon)
        items = list(self._views.items())
        items.insert(clamped, (view_id, entry))
        self._views = dict(items)

    def removeView(self, view_id: str) -> QWidget | None:
        """Remove and return the widget for *view_id*.

        The widget is detached from this container's stack but *not*
        deleted — it can be re-added to another container (the DnD
        cross-container move path). Returns ``None`` if unknown.
        """
        entry = self._views.pop(view_id, None)
        if entry is None:
            return None
        self._stack.removeWidget(entry.widget)
        entry.widget.setParent(None)
        self._activity_bar.removeItem(view_id)
        return entry.widget

    def reorderView(self, view_id: str, new_index: int) -> None:
        """Reorder *view_id* to *new_index* within this container."""
        if view_id not in self._views:
            return
        ids = list(self._views)
        old_index = ids.index(view_id)
        count = len(ids)
        new_index = max(0, min(new_index, count - 1))
        if old_index == new_index:
            return

        # Reorder the _views dict.
        items = list(self._views.items())
        item = items.pop(old_index)
        items.insert(new_index, item)
        self._views = dict(items)

        # Reorder the activity bar.
        self._activity_bar.moveItem(old_index, new_index)

        # Reorder the stack: take the widget out and re-insert. If the
        # widget was the stack's current one, ``removeWidget`` makes
        # Qt pick a new current — we must restore it afterward so the
        # visible content matches the (unchanged) active-item selection.
        entry = item[1]
        was_current = self._stack.currentWidget() is entry.widget
        self._stack.removeWidget(entry.widget)
        self._stack.insertWidget(new_index, entry.widget)
        if was_current:
            self._stack.setCurrentWidget(entry.widget)

    def activate(self, view_id: str) -> None:
        """Show a specific view by id."""
        entry = self._views.get(view_id)
        if entry is None:
            return
        self._stack.setCurrentWidget(entry.widget)
        widget = self.splitterWidget
        widget.show()
        ensure_splitter_size(widget, DEFAULT_SIDEBAR_WIDTH)

    def toggle(self) -> None:
        """Toggle visibility. Show first/active view, or collapse."""
        if self.isCollapsed:
            active = self._activity_bar.activeItem
            if active:
                self.activate(active)
            else:
                self._activity_bar.activateFirst()
        else:
            self.collapse()

    def deselect(self) -> None:
        """Deselect the active AB button without hiding the widget."""
        self._activity_bar.deselect()

    def restoreFromDrag(self) -> None:
        """Re-activate the first view after being dragged from zero."""
        first = next(iter(self._views), None)
        if first:
            self._activity_bar.setActiveSilent(first)
            self._stack.setCurrentWidget(self._views[first].widget)

    def collapse(self) -> None:
        """Fully hide the container."""
        self.splitterWidget.hide()
        self.deselect()

    # ---- bar type management ----------------------------------------------

    def _needs_horizontal(self) -> bool:
        """Whether the current position requires a horizontal bar."""
        return self.resolvedAbPosition in ("top", "bottom")

    def _is_horizontal(self) -> bool:
        return isinstance(self._activity_bar, NavigationBarAdapter)

    def _make_bar(self) -> ActivityBar | NavigationBarAdapter:
        if self._needs_horizontal():
            return NavigationBarAdapter(self)
        return ActivityBar(parent=self)

    def _wire_bar(self) -> None:
        self._activity_bar.itemToggled.connect(self.viewToggled)
        self._activity_bar.itemDropped.connect(self.viewDropped)
        self._activity_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._activity_bar.customContextMenuRequested.connect(self._show_context_menu)

    def _ensure_correct_bar_type(self) -> None:
        """Recreate the bar widget if orientation changed."""
        need_h = self._needs_horizontal()
        if need_h == self._is_horizontal():
            return

        # Save active state from old bar
        active = self._activity_bar.activeItem

        # Destroy old bar
        self._activity_bar.setParent(None)
        self._activity_bar.deleteLater()

        # Create new bar and re-add items from cached view entries
        self._activity_bar = self._make_bar()
        self._wire_bar()
        for view_id, entry in self._views.items():
            self._activity_bar.addItem(view_id, entry.title, icon=entry.icon)

        # Restore active state
        if active:
            self._activity_bar.setActiveSilent(active)

    # ---- context menu -----------------------------------------------------

    def _show_context_menu(self, pos: QPoint) -> None:
        self._build_context_menu().exec(self._activity_bar.mapToGlobal(pos))

    def _show_context_menu_stack(self, pos: QPoint) -> None:
        self._build_context_menu().exec(self._stack.mapToGlobal(pos))

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self._activity_bar)

        ab_menu = menu.addMenu("Activity Bar Position")
        group = QActionGroup(ab_menu)
        group.setExclusive(True)

        for pos in ActivityBarPosition:
            action = QAction(pos.value.capitalize(), ab_menu)
            action.setCheckable(True)
            action.setChecked(self._ab_position == pos)
            action.setData(pos)
            action.triggered.connect(self._on_ab_position_action)
            group.addAction(action)
            ab_menu.addAction(action)

        return menu

    def _on_ab_position_action(self) -> None:
        action: QAction = self.sender()  # type: ignore[assignment,unused-ignore]
        pos: ActivityBarPosition = action.data()
        if pos != self._ab_position:
            self._ab_position = pos
            self.abPositionChanged.emit(pos)


# Backwards-compatible alias
SidebarContainer = PaneContainer
