"""Registry tracking view descriptors and their current containers.

Mirrors VS Code's ``IViewDescriptorService`` (see
``vscode/src/vs/workbench/common/views.ts`` ~line 607) and the closely
related ``IViewContainerModel`` (~line 358). Descriptors are immutable;
this class owns the mutable "where is view X, and what order are views in
each container" state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pymmcore_gui._qt.QtCore import QObject, Signal

from ._enums import ViewContainerLocation

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtWidgets import QWidget

    from ._view_descriptor import ViewDescriptor


class ViewRegistry(QObject):
    """Central directory of views, their locations, and their instances.

    Three pieces of state:

    * **descriptors** — static :class:`ViewDescriptor` by id (immutable
      once registered). Mirrors VS Code's ``IViewsRegistry``.
    * **locations** — current :class:`ViewContainerLocation` per view id
      (mutable — changes on ``move_view_to_location``). Mirrors the
      "where does view X live right now?" lookup provided by VS Code's
      ``IViewDescriptorService.getViewLocationById``.
    * **instances** — lazily instantiated ``QWidget`` cache. The widget
      is built the first time the view is actually shown, analogous to
      VS Code's lazy ``ctorDescriptor`` pattern.
    """

    view_registered = Signal(str)
    """A new view was registered. → VS Code ``onViewsRegistered``.
    Argument: view id."""

    view_deregistered = Signal(str)
    """A view was deregistered. → VS Code ``onViewsDeregistered``.
    Argument: view id."""

    view_moved = Signal(str, object, object)
    """A view moved between containers.
    → VS Code ``onDidChangeLocation``.
    Arguments: ``(view_id, from_location, to_location)``."""

    view_reordered = Signal(str, object, int)
    """A view was reordered within its current container.
    → VS Code ``IViewContainerModel.onDidMoveVisibleViewDescriptors``.
    Arguments: ``(view_id, location, new_index)``."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._descriptors: dict[str, ViewDescriptor] = {}
        self._locations: dict[str, ViewContainerLocation] = {}
        self._instances: dict[str, QWidget] = {}
        self._order: dict[ViewContainerLocation, list[str]] = {
            loc: [] for loc in ViewContainerLocation
        }

    # ---- registration -----------------------------------------------------

    def register_view(self, descriptor: ViewDescriptor) -> None:
        """Register *descriptor* at its ``default_location``.

        → VS Code ``IViewsRegistry.registerViews``.
        """
        if descriptor.id in self._descriptors:
            raise ValueError(f"View {descriptor.id!r} already registered")
        self._descriptors[descriptor.id] = descriptor
        self._locations[descriptor.id] = descriptor.default_location
        self._insert_ordered(descriptor.id, descriptor.default_location)
        self.view_registered.emit(descriptor.id)

    def deregister_view(self, view_id: str) -> None:
        """Remove *view_id* from the registry.

        → VS Code ``IViewsRegistry.deregisterViews``.
        """
        if view_id not in self._descriptors:
            return
        loc = self._locations.pop(view_id)
        self._order[loc].remove(view_id)
        del self._descriptors[view_id]
        self._instances.pop(view_id, None)
        self.view_deregistered.emit(view_id)

    # ---- lookups ----------------------------------------------------------

    def get_view_descriptor(self, view_id: str) -> ViewDescriptor | None:
        """→ VS Code ``getViewDescriptorById``."""
        return self._descriptors.get(view_id)

    def get_view_location(self, view_id: str) -> ViewContainerLocation | None:
        """→ VS Code ``getViewLocationById``."""
        return self._locations.get(view_id)

    def get_views_in_location(self, location: ViewContainerLocation) -> list[str]:
        """Return view ids in *location*, in display order.

        → VS Code composition of ``getViewContainersByLocation`` with
        ``IViewContainerModel.visibleViewDescriptors``.
        """
        return list(self._order[location])

    def get_view_instance(self, view_id: str) -> QWidget:
        """Return the widget for *view_id*, instantiating lazily.

        Mirrors VS Code's lazy view-pane instantiation via
        ``ctorDescriptor``. The first call invokes the descriptor's
        ``factory``; subsequent calls return the cached instance so
        reparenting the widget between containers preserves its state.
        """
        if view_id not in self._descriptors:
            raise KeyError(f"Unknown view: {view_id!r}")
        instance = self._instances.get(view_id)
        if instance is None:
            instance = self._descriptors[view_id].factory()
            self._instances[view_id] = instance
        return instance

    @property
    def view_ids(self) -> list[str]:
        """All registered view ids, in registration order."""
        return list(self._descriptors)

    # ---- moves ------------------------------------------------------------

    def move_view_to_location(
        self,
        view_id: str,
        location: ViewContainerLocation,
        index: int | None = None,
    ) -> None:
        """Move *view_id* to *location*, optionally at *index*.

        If *index* is ``None`` the view is appended. A move within the
        same location reorders; a move between locations emits
        ``view_moved``, a reorder emits ``view_reordered``.

        Raises :class:`PermissionError` if the descriptor has
        ``can_move=False``. This enforcement is checked here so every
        caller (including DnD drop handlers and :meth:`reorder_view`)
        inherits it automatically.

        → VS Code ``moveViewToLocation`` / ``moveViewsToContainer``.
        """
        descriptor = self._descriptors.get(view_id)
        if descriptor is None:
            raise KeyError(f"Unknown view: {view_id!r}")
        if not descriptor.can_move:
            raise PermissionError(
                f"View {view_id!r} is pinned (can_move=False) and cannot be moved"
            )
        old_loc = self._locations[view_id]
        self._order[old_loc].remove(view_id)
        self._locations[view_id] = location
        if index is None:
            self._order[location].append(view_id)
        else:
            clamped = max(0, min(index, len(self._order[location])))
            self._order[location].insert(clamped, view_id)

        if old_loc != location:
            self.view_moved.emit(view_id, old_loc, location)
        else:
            new_idx = self._order[location].index(view_id)
            self.view_reordered.emit(view_id, location, new_idx)

    def reorder_view(self, view_id: str, new_index: int) -> None:
        """Reorder *view_id* within its current container."""
        loc = self._locations.get(view_id)
        if loc is None:
            raise KeyError(f"Unknown view: {view_id!r}")
        self.move_view_to_location(view_id, loc, index=new_index)

    # ---- persistence ------------------------------------------------------

    def dump_state(self) -> dict[str, Any]:
        """Serialize mutable registry state for persistence.

        Descriptors are *not* serialized — they're expected to be
        re-registered on startup from code. Only the user-affected
        state (per-view location and per-container order) is returned.
        """
        return {
            "locations": {
                view_id: loc.value for view_id, loc in self._locations.items()
            },
            "order": {loc.value: list(ids) for loc, ids in self._order.items()},
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Restore mutable registry state produced by :meth:`dump_state`.

        Only affects views that have already been registered; unknown
        view ids in *state* are silently ignored.
        """
        locations = state.get("locations", {})
        order = state.get("order", {})

        # Rebuild _locations for known views
        for view_id, loc_str in locations.items():
            if view_id not in self._descriptors:
                continue
            try:
                loc = ViewContainerLocation(loc_str)
            except ValueError:
                continue
            old = self._locations[view_id]
            if old != loc:
                self._order[old].remove(view_id)
                self._locations[view_id] = loc
                # Will be re-placed by the order pass below

        # Rebuild _order, filtered to known views
        new_order: dict[ViewContainerLocation, list[str]] = {
            loc: [] for loc in ViewContainerLocation
        }
        for loc_str, ids in order.items():
            try:
                loc = ViewContainerLocation(loc_str)
            except ValueError:
                continue
            for view_id in ids:
                if view_id in self._descriptors:
                    new_order[loc].append(view_id)

        # Any registered view not mentioned in the saved order falls
        # back to the end of its current location.
        placed = {vid for ids in new_order.values() for vid in ids}
        for view_id, loc in self._locations.items():
            if view_id not in placed:
                new_order[loc].append(view_id)

        self._order = new_order

    # ---- internals --------------------------------------------------------

    def _insert_ordered(self, view_id: str, location: ViewContainerLocation) -> None:
        """Insert *view_id* into ``_order[location]``.

        Respects descriptor ``order`` fields as a stable sort key.
        """
        descriptor = self._descriptors[view_id]
        bucket = self._order[location]
        # Find the first position whose descriptor has a strictly
        # greater ``order`` value. This preserves insertion order
        # among equal-ordered views.
        insert_at = len(bucket)
        for i, existing_id in enumerate(bucket):
            existing = self._descriptors[existing_id]
            if existing.order > descriptor.order:
                insert_at = i
                break
        bucket.insert(insert_at, view_id)
