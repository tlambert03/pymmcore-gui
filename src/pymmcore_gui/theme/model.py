from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field, fields
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal, TypeAlias

    from PyQt6.QtGui import QPalette

    ColorGroupName: TypeAlias = Literal["active", "inactive", "disabled"]
    ColorRoleName: TypeAlias = Literal[
        "window"
        "window_text"
        "base"
        "alternate_base"
        "tool_tip_base"
        "tool_tip_text"
        "placeholder_text"
        "text"
        "button"
        "button_text"
        "bright_text"
        "light"
        "midlight"
        "mid"
        "dark"
        "shadow"
        "highlight"
        "accent"
        "highlighted_text"
        "link"
        "link_visited"
        "no_role"
    ]


@dataclass(frozen=True, slots=True)
class ColorGroup:
    """Qt Palette model."""

    window: str = ""
    """A general background color."""

    window_text: str = ""
    """A general foreground color."""

    base: str = ""
    """Used mostly as the background color for text entry widgets, but can also be used
    for other painting - such as the background of combobox drop down lists and toolbar
    handles. It is usually white or another light color."""

    alternate_base: str = ""
    """Used as the alternate background color in views with alternating row colors."""

    tool_tip_base: str = ""
    """Used as the background color for QToolTip and QWhatsThis. Tool tips use the
    Inactive color group of QPalette, because tool tips are not active windows."""

    tool_tip_text: str = ""
    """Used as the foreground color for QToolTip and QWhatsThis. Tool tips use the
    Inactive color group of QPalette, because tool tips are not active windows."""

    placeholder_text: str = ""
    """Used as the placeholder color for various text input widgets."""

    text: str = ""
    """The foreground color used with Base. This is usually the same as the WindowText,
    in which case it must provide good contrast with Window and Base."""

    button: str = ""
    """The general button background color. This background can be different from Window
    as some styles require a different background color for buttons."""

    button_text: str = ""
    """A foreground color used with the Button color."""

    bright_text: str = ""
    """A text color that is very different from WindowText, and contrasts well with e.g.
    Dark. Typically used for text that needs to be drawn where Text or WindowText would
    give poor contrast, such as on pressed push buttons. Note that text colors can be
    used for things other than just words; text colors are usually used for text, but
    it's quite common to use the text color roles for lines, icons, etc."""

    # These color roles used mostly for 3D bevel and shadow effects.
    # All of these are normally derived from Window, and used in ways that depend on
    # that relationship. For example, buttons depend on it to make the bevels look
    # attractive, and Motif scroll bars depend on Mid to be slightly different from
    # Window.

    light: str = ""
    """Lighter than Button color."""
    midlight: str = ""
    """Between Button and Light."""
    mid: str = ""
    """Between Button and Dark."""
    dark: str = ""
    """Darker than Button."""
    shadow: str = ""
    """A very dark color. By default, the shadow color is Qt::black."""

    # Selected (marked) items have two roles:
    highlight: str = ""
    """A color to indicate a selected item or the current item. By default, the
    highlight color is darkBlue."""
    accent: str = ""  # since Qt 6.6
    """A color that typically contrasts or complements Base, Window and Button colors.
    It usually represents the users' choice of desktop personalisation. Styling of
    interactive components is a typical use case. Unless explicitly set, it defaults to
    Highlight."""
    highlighted_text: str = ""
    """A text color that contrasts with Highlight. By default, the highlighted text
    color is white."""

    # related to hyperlinks:
    link: str = ""
    """A text color used for unvisited hyperlinks. By default, blue"""
    link_visited: str = ""
    """A text color used for already visited hyperlinks. By default, magenta"""

    no_role: str = ""
    """This special role is often used to indicate that a role has not been assigned."""

    def __rich_repr__(self) -> Iterator[str, str]:
        """Rich repr without default values."""
        for key, value in asdict(self).items():
            if value:
                yield key, value


@dataclass(frozen=True, slots=True)
class Palette:
    """Qt Palette model.

    In most styles, Active and Inactive look the same.
    """

    active: ColorGroup = field(default_factory=ColorGroup)
    """Group used for the window that has keyboard focus."""

    inactive: ColorGroup = field(default_factory=ColorGroup)
    """Group used for other windows."""

    disabled: ColorGroup = field(default_factory=ColorGroup)
    """Group used for widgets (not windows) that are disabled for some reason."""

    def color(self, group: ColorGroupName, role: ColorRoleName) -> str:
        """Return color for the given role and state."""
        color_group = getattr(self, group)
        color = cast(str, getattr(color_group, role))
        if not color and group != "active":
            # it's possible that disabled should also check in inactive first...
            return self.color("active", role)
        return color

    @classmethod
    def from_qpalette(cls, qpalette: QPalette) -> Palette:
        """Create a Palette from a QPalette."""
        from PyQt6.QtGui import QPalette

        CG = QPalette.ColorGroup
        CR = QPalette.ColorRole

        data = defaultdict[str, dict](dict)
        for group in (CG.Active, CG.Inactive, CG.Disabled):
            group_name = group.name.lower()
            for role in CR:
                if role == CR.NColorRoles:
                    continue
                role_name = _to_snake_case(role.name)
                color = qpalette.color(group, role).name()
                if group == CG.Active or (data["active"][role_name] != color):
                    data[group_name][role_name] = color

        return cls(
            active=ColorGroup(**data["active"]),
            inactive=ColorGroup(**data["inactive"]),
            disabled=ColorGroup(**data["disabled"]),
        )

    def to_qpalette(self) -> QPalette:
        """Convert to a QPalette."""
        from PyQt6.QtGui import QColor, QPalette

        qpalette = QPalette()
        for group in ("active", "inactive", "disabled"):
            qgroup = getattr(QPalette.ColorGroup, group.capitalize())
            for field_ in fields(ColorGroup):
                role_name = cast("ColorRoleName", field_.name)
                qrole = getattr(QPalette.ColorRole, _to_camel_case(role_name))
                color = self.color(group, role_name)
                qpalette.setColor(qgroup, qrole, QColor(color))
        return qpalette


def _to_snake_case(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def _to_camel_case(s: str) -> str:
    return "".join(word.title() for word in s.split("_"))


MACOS_LIGHT = Palette(
    active=ColorGroup(
        window="#ececec",
        window_text="#000000",
        base="#ffffff",
        alternate_base="#f5f5f5",
        tool_tip_base="#ffffff",
        tool_tip_text="#000000",
        placeholder_text="#000000",
        text="#000000",
        button="#ececec",
        button_text="#000000",
        bright_text="#ffffff",
        light="#ffffff",
        midlight="#f5f5f5",
        mid="#a9a9a9",
        dark="#bfbfbf",
        shadow="#000000",
        highlight="#a5cdff",
        accent="#0a60ff",
        highlighted_text="#000000",
        link="#094fd1",
        link_visited="#ff00ff",
        no_role="#000000",
    ),
    inactive=ColorGroup(highlight="#d4d4d4", link="#0000ff"),
    disabled=ColorGroup(base="#ececec", highlight="#d4d4d4", link="#0000ff"),
)

MACOS_DARK = Palette(
    active=ColorGroup(
        window="#323232",
        window_text="#ffffff",
        base="#171717",
        alternate_base="#989898",
        tool_tip_base="#ffffff",
        tool_tip_text="#000000",
        placeholder_text="#ffffff",
        text="#ffffff",
        button="#323232",
        button_text="#ffffff",
        bright_text="#373737",
        light="#373737",
        midlight="#343434",
        mid="#242424",
        dark="#bfbfbf",
        shadow="#000000",
        highlight="#314f78",
        accent="#0a60ff",
        highlighted_text="#ffffff",
        link="#3586ff",
        link_visited="#ff00ff",
        no_role="#000000",
    ),
    inactive=ColorGroup(button_text="#000000", highlight="#363636", link="#0000ff"),
    disabled=ColorGroup(base="#323232", highlight="#363636", link="#0000ff"),
)
