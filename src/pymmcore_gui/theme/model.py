from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, cast

from pyconify import svg_path

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal, TypeAlias

    from PyQt6.QtGui import QPalette
    from PyQt6.QtWidgets import QApplication

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
    """Qt ColorGroup model."""

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

    def __rich_repr__(self) -> Iterator[tuple[str, str]]:
        """Rich repr without default values."""
        for key, value in asdict(self).items():
            if value:
                yield key, value


@dataclass(frozen=True, slots=True)
class Icons:
    """Icons used in the theme."""

    down_arrow_svg: str = "fluent:chevron-down-16-filled"
    """Down arrow used to the right of, e.g. ComboBox."""

    def to_posix(self, color: str | None = None) -> dict[str, str]:
        """Convert to a dictionary with paths as posix strings."""
        return {
            k: svg_path(v, color=color).as_posix() for k, v in asdict(self).items() if v
        }


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
        color = cast("str", getattr(color_group, role))
        if not color and group != "active":
            # it's possible that disabled should also check in inactive first...
            return self.color("active", role)
        return color

    @classmethod
    def from_qpalette(cls, qpalette: QPalette) -> Palette:
        """Create a Palette from a QPalette."""
        from .adapters import qpalette_to_palette

        return qpalette_to_palette(qpalette, cls)

    def to_qpalette(self) -> QPalette:
        """Convert to a QPalette."""
        from .adapters import palette_to_qpalette

        return palette_to_qpalette(self)


# Define the QSS template
MACOS_QSS_TEMPLATE = """
/* --------------------------------------- */

QLineEdit, QAbstractSpinBox, QPushButton, QComboBox {{
    border: 0.5px solid {mid};
    placeholder-text-color: {placeholder_text};
}}


/* --------------------------------------- */

/* border-gradient */

QPushButton, QComboBox {{
    height: 20px;
    background-color: {button};
    border-radius: 6px;
    border-top-color: #848484;
    border-bottom-color: #272727;
    selection-background-color: {highlight};
    color: {button_text};
}}

QPushButton::pressed {{
    background-color: #7B7B7B;
}}

/* --------------------------------------- */


QComboBox {{
    padding-left: 8px;
}}

QComboBox::drop-down:button {{
    border-radius:4px;
    margin: 1.5px;
    width: 14px;
    background-color: none;
}}

QComboBox::down-arrow {{
    image: url({down_arrow_svg});
    margin-right: 4px;
}}

/* --------------------------------------- */

QSlider::add-page {{
    background-color: #474747;
}}

QSlider::groove, QSlider::add-page {{
    border: 0px;
    border-radius: 2px;
}}

QSlider::groove::horizontal {{
    height: 4px;
}}

QSlider::groove::vertical {{
    width: 4px;
}}

QSlider::groove {{
    background: {highlight};
}}

QSlider::handle {{
    background: #9A9493;
    border: 0.5px solid {mid};
    width: 18px;
    margin: -8px 0;
    border-radius: 10px;
}}

/* --------------------------------------- */

QTabWidget::pane {{
    background: {light};
    border: 1px solid #464646;
    border-radius: 4px;
    margin-top: -12px;
}}

QTabBar::tab {{
    background: {button};
    padding: 4px;
    border-radius: 4px;
}}

QTabBar::tab:selected {{
}}

QToolBar QToolButton#copy_action {{
    qproperty-icon: url({down_arrow_svg});
}}
"""

THEME_REGISTRY: dict[str, Theme] = {}


@dataclass(frozen=True, slots=True)
class Theme:
    """Theme model for the application."""

    name: str
    """Name of the theme."""

    palette: Palette = field(default_factory=Palette)
    """Palette used in the theme."""

    qss_template: str = MACOS_QSS_TEMPLATE

    icons: Icons = field(default_factory=Icons)
    """Icons used in the theme."""

    def __post_init__(self) -> None:
        """Post-initialization checks."""
        if self.name in THEME_REGISTRY:
            raise ValueError(f"Theme with name '{self.name}' already exists.")
        THEME_REGISTRY[self.name] = self

    def to_qpalette(self) -> QPalette:
        """Convert to a QPalette."""
        return self.palette.to_qpalette()

    def to_qss(self) -> str:
        """Convert to a QSS string."""
        return self.qss_template.format(
            **asdict(self.palette.active),
            **self.icons.to_posix(color=self.palette.active.button_text or None),
        )

    def apply_to_qapplication(self, app: QApplication | None) -> None:
        """Apply the theme to the given QApplication."""
        if app is None:
            from PyQt6.QtWidgets import QApplication

            _app = QApplication.instance()
            if _app is None:  # pragma: no cover
                raise RuntimeError(
                    "No QApplication instance found. Please create one first."
                )
            if not isinstance(_app, QApplication):  # pragma: no cover
                raise TypeError(f"Expected a QApplication instance, got {type(_app)}")
            app = _app
        app.setStyleSheet(self.to_qss())
        app.setPalette(self.to_qpalette())


def get_theme(name: str) -> Theme:
    """Get a theme by name."""
    if (theme := THEME_REGISTRY.get(name)) is None:
        available_themes = ", ".join(THEME_REGISTRY.keys())
        raise ValueError(
            f"Theme with name '{name}' not found. "
            f"Available themes are: {available_themes}"
        )
    return theme


MACOS_LIGHT = Theme(
    name="macos-light",
    qss_template=MACOS_QSS_TEMPLATE,
    palette=Palette(
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
        inactive=ColorGroup(
            highlight="#d4d4d4",
            link="#0000ff",
        ),
        disabled=ColorGroup(
            base="#ececec",
            highlight="#d4d4d4",
            link="#0000ff",
        ),
    ),
)

MACOS_DARK = Theme(
    name="macos-dark",
    qss_template=MACOS_QSS_TEMPLATE,
    palette=Palette(
        active=ColorGroup(
            window="#323232",
            window_text="#ffffff",
            base="#171717",
            alternate_base="#989898",
            tool_tip_base="#ffffff",
            tool_tip_text="#000000",
            placeholder_text="#595959",
            text="#ffffff",
            # button="#323232", # from Qt
            button="#656565",  # measured
            button_text="#ffffff",
            # bright_text="#373737", # from Qt
            bright_text="#E7E7E7",  # measured
            light="#373737",
            midlight="#343434",
            mid="#242424",
            dark="#bfbfbf",
            shadow="#000000",
            # highlight="#314f78",
            highlight="#007AFF",  # default macos blue
            accent="#0a60ff",
            highlighted_text="#ffffff",
            link="#3586ff",
            link_visited="#ff00ff",
            no_role="#000000",
        ),
        inactive=ColorGroup(
            button_text="#000000",
            highlight="#363636",
            link="#0000ff",
        ),
        disabled=ColorGroup(
            base="#323232",
            highlight="#363636",
            link="#0000ff",
        ),
    ),
)
