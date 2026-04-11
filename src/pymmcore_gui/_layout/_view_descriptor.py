"""Declarative descriptor for a workbench view.

Mirrors VS Code's `IViewDescriptor`. See
`vscode/src/vs/workbench/common/views.ts` (`IViewDescriptor` ~line 284)
for the reference model — field names here use snake_case but the docstrings
cross-reference the original camelCase names so the VS Code source remains
easily searchable as a mirror.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainValidator

from pymmcore_gui._qt.QtGui import QIcon
from pymmcore_gui._qt.QtWidgets import QWidget

from ._enums import ViewContainerLocation

if TYPE_CHECKING:
    from typing import TypeAlias


def _check_qicon(value: Any) -> QIcon:
    if not isinstance(value, QIcon):
        raise TypeError(f"Expected QIcon, got {type(value).__name__}")
    return value


QIconType: TypeAlias = Annotated[QIcon, PlainValidator(_check_qicon)]

ViewFactory: TypeAlias = Callable[[], QWidget]
"""A zero-arg callable that returns the view widget."""


class ViewDescriptor(BaseModel):
    """Declarative metadata for a single workbench view.

    Mirrors VS Code's `IViewDescriptor`. Descriptors are immutable:
    "where the view currently lives" is tracked by :class:`ViewRegistry`,
    not here.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    """Unique id for the view. """

    name: str
    """Human-readable title shown in tab strips and menus."""

    factory: ViewFactory
    """Zero-arg callable that returns the view widget.

    Invoked lazily the first time the view is shown, so heavy views (consoles, viewers)
    don't pay their cost until needed.
    """

    icon: QIconType
    """Icon shown in activity bars and nav bars.

    Required so the view can be rendered uniformly in any container,
    including the vertical icon-only ActivityBar where there's no
    horizontal room to fall back to a text label. Dragging a view
    between containers must not depend on which bar style the target
    happens to use.
    """

    default_location: ViewContainerLocation = ViewContainerLocation.LEFT_SIDEBAR
    """Container this view belongs to when first registered.

    The user may later move the view to another container; the current
    (mutable) location is tracked by :class:`ViewRegistry`, not here.
    """

    order: int = 0
    """Ordering hint within a container (lower = earlier)."""

    can_move: bool = True
    """Whether the user may drag this view to another container."""

    hide_by_default: bool = False
    """Whether the view is hidden on first registration.

    Hidden views still exist in the registry; the user can show them later.
    """
