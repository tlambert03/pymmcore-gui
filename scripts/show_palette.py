"""Show every QPalette ColorRole as rendered by QlementineStyle."""

from __future__ import annotations

import sys

from pymmcore_gui._ads_style import AdsAwareQlementineStyle, apply_dark_theme
from pymmcore_gui._qt.QtCore import Qt
from pymmcore_gui._qt.QtGui import QColor, QPalette
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

COLOR_ROLES = [
    QPalette.ColorRole.Window,
    QPalette.ColorRole.WindowText,
    QPalette.ColorRole.Base,
    QPalette.ColorRole.AlternateBase,
    QPalette.ColorRole.ToolTipBase,
    QPalette.ColorRole.ToolTipText,
    QPalette.ColorRole.PlaceholderText,
    QPalette.ColorRole.Text,
    QPalette.ColorRole.Button,
    QPalette.ColorRole.ButtonText,
    QPalette.ColorRole.BrightText,
    QPalette.ColorRole.Light,
    QPalette.ColorRole.Midlight,
    QPalette.ColorRole.Dark,
    QPalette.ColorRole.Mid,
    QPalette.ColorRole.Shadow,
    QPalette.ColorRole.Highlight,
    QPalette.ColorRole.HighlightedText,
    QPalette.ColorRole.Link,
    QPalette.ColorRole.LinkVisited,
    QPalette.ColorRole.Accent,
]

COLOR_GROUPS = [
    ("Active", QPalette.ColorGroup.Active),
    ("Inactive", QPalette.ColorGroup.Inactive),
    ("Disabled", QPalette.ColorGroup.Disabled),
]


def _swatch(color: QColor) -> QLabel:
    lbl = QLabel()
    lbl.setFixedSize(60, 28)
    lbl.setAutoFillBackground(True)
    lbl.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")
    lbl.setToolTip(color.name())
    return lbl


def _hex_label(color: QColor) -> QLabel:
    lbl = QLabel(color.name())
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


def build_ui(palette: QPalette) -> QWidget:
    """Build the palette inspector UI."""
    outer = QWidget()
    outer.setWindowTitle("Qlementine Palette Inspector")
    outer_layout = QVBoxLayout(outer)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    outer_layout.addWidget(scroll)

    container = QWidget()
    grid = QGridLayout(container)
    grid.setSpacing(6)

    # Header row
    grid.addWidget(QLabel("<b>ColorRole</b>"), 0, 0)
    for col, (group_name, _) in enumerate(COLOR_GROUPS):
        grid.addWidget(QLabel(f"<b>{group_name}</b>"), 0, 1 + col * 2, 1, 2)

    for row, role in enumerate(COLOR_ROLES, start=1):
        role_name = role.name if hasattr(role, "name") else str(role).rsplit(".", 1)[-1]
        grid.addWidget(QLabel(role_name), row, 0)
        for col, (_group_name, group) in enumerate(COLOR_GROUPS):
            c = palette.color(group, role)
            grid.addWidget(_swatch(c), row, 1 + col * 2)
            grid.addWidget(_hex_label(c), row, 2 + col * 2)

    scroll.setWidget(container)
    outer.resize(900, 700)
    return outer


def main() -> None:
    """Main entry point."""
    app = QApplication(sys.argv)
    style = AdsAwareQlementineStyle()
    apply_dark_theme(style)
    app.setStyle(style)

    # Force palette generation by creating a temporary widget
    tmp = QWidget()
    palette = tmp.palette()
    del tmp

    win = build_ui(palette)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
