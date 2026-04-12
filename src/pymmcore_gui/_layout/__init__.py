"""VS Code-style workbench layout components.

Naming mirrors VS Code's ``vs/workbench`` source tree so the VS Code
codebase can be used as a reference while extending this package:
:class:`ViewDescriptor` ↔ ``IViewDescriptor``,
:class:`ViewRegistry` ↔ ``IViewDescriptorService``,
:class:`PaneContainer` ↔ ``ViewContainer`` (VS Code's single-view
``ViewPaneContainer`` flavor),
:class:`WorkbenchWidget` ↔ the workbench ``Part`` layout.
"""

from ._enums import (
    ActivityBarPosition,
    NavDisplayMode,
    PanelAlignment,
    ViewContainerLocation,
)
from ._item_bar import ItemBar
from ._pane_container import PaneContainer, SidebarContainer
from ._splitter_utils import splitter_size
from ._view_descriptor import ViewDescriptor, ViewFactory
from ._view_registry import ViewRegistry
from ._workbench import WorkbenchWidget

__all__ = [
    "ActivityBarPosition",
    "ItemBar",
    "NavDisplayMode",
    "PaneContainer",
    "PanelAlignment",
    "SidebarContainer",
    "ViewContainerLocation",
    "ViewDescriptor",
    "ViewFactory",
    "ViewRegistry",
    "WorkbenchWidget",
    "splitter_size",
]
