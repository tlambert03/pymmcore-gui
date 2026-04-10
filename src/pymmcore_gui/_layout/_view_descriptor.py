"""Declarative descriptor for a workbench view.

Mirrors VS Code's ``IViewDescriptor``. See
``vscode/src/vs/workbench/common/views.ts`` (``IViewDescriptor`` ~line 284)
for the reference model — field names here use snake_case but the docstrings
cross-reference the original camelCase names so the VS Code source remains
easily searchable as a mirror.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainValidator

from pymmcore_gui._qt.QtGui import QIcon
from pymmcore_gui._qt.QtWidgets import QWidget

from ._enums import ViewContainerLocation


def _check_qicon(value: Any) -> QIcon:
    if not isinstance(value, QIcon):
        raise TypeError(f"Expected QIcon, got {type(value).__name__}")
    return value


QIconType = Annotated[QIcon, PlainValidator(_check_qicon)]

ViewFactory = Callable[[], QWidget]
"""A zero-arg callable that returns the view widget."""


class ViewDescriptor(BaseModel):
    """Declarative metadata for a single workbench view.

    Mirrors VS Code's ``IViewDescriptor``. Descriptors are immutable:
    "where the view currently lives" is tracked by :class:`ViewRegistry`,
    not here.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    """Unique id for the view. → VS Code ``IViewDescriptor.id``."""

    name: str
    """Human-readable title shown in tab strips and menus.
    → VS Code ``IViewDescriptor.name``."""

    factory: ViewFactory
    """Zero-arg callable that returns the view widget. Invoked lazily
    the first time the view is shown, so heavy views (consoles,
    viewers) don't pay their cost until needed.
    → VS Code ``IViewDescriptor.ctorDescriptor``."""

    icon: QIconType | None = None
    """Optional icon shown in the activity bar / nav bar.
    → VS Code ``IViewDescriptor.containerIcon``."""

    default_location: ViewContainerLocation = ViewContainerLocation.LEFT_SIDEBAR
    """Container this view belongs to when first registered. The user
    may later move it; the current location is tracked by the registry.
    → VS Code has no direct analogue — containers are registered
    separately and views are attached to them by id."""

    order: int = 0
    """Ordering hint within a container (lower = earlier).
    → VS Code ``IViewDescriptor.order``."""

    can_move: bool = True
    """Whether the user may drag this view to another container.
    → VS Code ``IViewDescriptor.canMoveView``."""

    hide_by_default: bool = False
    """Whether the view is hidden on first registration. Hidden views
    still exist in the registry; the user can show them later.
    → VS Code ``IViewDescriptor.hideByDefault``."""
