from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import fields
from typing import TYPE_CHECKING, cast

from PyQt6.QtGui import QColor, QGuiApplication, QPalette

from pymmcore_gui.theme.model import ColorGroup, Palette

if TYPE_CHECKING:
    from typing import Literal, TypeAlias

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


def _to_snake_case(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()


def _to_camel_case(s: str) -> str:
    return "".join(word.title() for word in s.split("_"))


def qpalette_to_palette(qpalette: QPalette, palette_type: type[Palette]) -> Palette:
    """Create a Palette from a QPalette."""
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

    return palette_type(
        active=ColorGroup(**data["active"]),
        inactive=ColorGroup(**data["inactive"]),
        disabled=ColorGroup(**data["disabled"]),
    )


def palette_to_qpalette(palette: Palette) -> QPalette:
    """Convert a Palette to a QPalette."""
    qpalette = QGuiApplication.palette()
    for group in ("active", "inactive", "disabled"):
        qgroup = getattr(qpalette.ColorGroup, group.capitalize())
        for field_ in fields(ColorGroup):
            role_name = cast("ColorRoleName", field_.name)
            try:
                qrole = getattr(qpalette.ColorRole, _to_camel_case(role_name))
            except AttributeError:
                continue
            color = palette.color(group, role_name)
            qpalette.setColor(qgroup, qrole, QColor(color))
    return qpalette
