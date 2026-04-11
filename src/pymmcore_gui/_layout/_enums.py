from __future__ import annotations

from enum import Enum


class PanelAlignment(Enum):
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    JUSTIFY = "justify"


class ActivityBarPosition(Enum):
    DEFAULT = "default"
    TOP = "top"
    BOTTOM = "bottom"
    HIDDEN = "hidden"


class ViewContainerLocation(Enum):
    LEFT_SIDEBAR = "left_sidebar"
    RIGHT_SIDEBAR = "right_sidebar"
    PANEL = "panel"


class NavDisplayMode(Enum):
    """Visual density for a horizontal navigation bar's items."""

    BOTH = "both"  # icon + text (default)
    ICONS_ONLY = "icons"  # icon only, text hidden
    TEXT_ONLY = "text"  # text only, icon hidden
