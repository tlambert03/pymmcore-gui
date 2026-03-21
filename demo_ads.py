"""Same demo as demo.py but using QtAds dock widgets instead of QTabWidget."""

from __future__ import annotations

import sys
from typing import Any

from pymmcore_gui._ads_style import AdsAwareStyle
from pymmcore_gui._qt.Qlementine import AutoIconColor, QlementineStyle, Theme
from pymmcore_gui._qt.QtAds import CDockManager, CDockWidget, DockWidgetArea
from pymmcore_gui._qt.QtCore import QJsonDocument, Qt
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

radix_slate_blue = {
    "meta": {
        "name": "Radix Slate Blue",
        "version": "1.0.0",
        "author": "WorkOS/Radix (adapted)",
    },
    "background_color_main1": "#111113",
    "background_color_main2": "#18191B",
    "background_color_main3": "#212225",
    "background_color_main4": "#272A2D",
    "background_color_workspace": "#0C0C0E",
    "background_color_tab_bar": "#111113",
    "neutral_color": "#2E3135",
    "neutral_color_hovered": "#363A3F",
    "neutral_color_pressed": "#3E4349",
    "neutral_color_disabled": "#1C1D1F",
    "focus_color": "#0090FF6A",
    "primary_color": "#0090FF",
    "primary_color_hovered": "#3B9EFF",
    "primary_color_pressed": "#6CB4FF",
    "primary_color_disabled": "#142840",
    "primary_color_foreground": "#FFFFFF",
    "primary_color_foreground_hovered": "#FFFFFF",
    "primary_color_foreground_pressed": "#FFFFFF",
    "primary_color_foreground_disabled": "#384858",
    "primary_alternative_color": "#3E63DD",
    "primary_alternative_color_hovered": "#5472E4",
    "primary_alternative_color_pressed": "#6A81EB",
    "primary_alternative_color_disabled": "#161E38",
    "secondary_color": "#EDEEF0",
    "secondary_color_hovered": "#D0D2D6",
    "secondary_color_pressed": "#DFE0E3",
    "secondary_color_disabled": "#EDEEF033",
    "secondary_color_foreground": "#18191B",
    "secondary_color_foreground_hovered": "#18191B",
    "secondary_color_foreground_pressed": "#18191B",
    "secondary_color_foreground_disabled": "#18191B3F",
    "secondary_alternative_color": "#696E77",
    "secondary_alternative_color_hovered": "#868B94",
    "secondary_alternative_color_pressed": "#9DA2AA",
    "secondary_alternative_color_disabled": "#696E773F",
    "status_color_success": "#30A46C",
    "status_color_success_hovered": "#3DB57D",
    "status_color_success_pressed": "#4AC68E",
    "status_color_success_disabled": "#14221C",
    "status_color_info": "#0090FF",
    "status_color_info_hovered": "#3B9EFF",
    "status_color_info_pressed": "#6CB4FF",
    "status_color_info_disabled": "#101E30",
    "status_color_warning": "#F5D90A",
    "status_color_warning_hovered": "#F6DE2E",
    "status_color_warning_pressed": "#F7E352",
    "status_color_warning_disabled": "#2A2810",
    "status_color_error": "#E5484D",
    "status_color_error_hovered": "#EC5D62",
    "status_color_error_pressed": "#F37277",
    "status_color_error_disabled": "#2C1416",
    "status_color_foreground": "#FFFFFF",
    "status_color_foreground_hovered": "#FFFFFF",
    "status_color_foreground_pressed": "#FFFFFF",
    "status_color_foreground_disabled": "#FFFFFF26",
    "shadow_color1": "#00000066",
    "shadow_color2": "#000000BB",
    "shadow_color3": "#000000FF",
    "border_color": "#43484E",
    "border_color_hovered": "#50565E",
    "border_color_pressed": "#5D646E",
    "border_color_disabled": "#282A2E",
    "semi_transparent_color1": "#0090FF0A",
    "semi_transparent_color2": "#0090FF14",
    "semi_transparent_color3": "#0090FF1E",
    "semi_transparent_color4": "#0090FF28",
    "use_system_fonts": True,
    "font_size": 13,
    "font_size_monospace": 13,
    "font_size_h1": 34,
    "font_size_h2": 26,
    "font_size_h3": 22,
    "font_size_h4": 18,
    "font_size_h5": 14,
    "font_size_s1": 10,
    "animation_duration": 200,
    "focus_animation_duration": 400,
    "slider_animation_duration": 120,
    "border_radius": 8.0,
    "check_box_border_radius": 4.0,
    "menu_item_border_radius": 6.0,
    "menu_bar_item_border_radius": 4.0,
    "border_width": 1,
    "control_height_large": 32,
    "control_height_medium": 28,
    "control_height_small": 20,
    "control_default_width": 120,
    "dial_mark_length": 8,
    "dial_mark_thickness": 2,
    "dial_tick_length": 4,
    "dial_tick_spacing": 4,
    "dial_groove_thickness": 4,
    "focus_border_width": 2,
    "icon_extent": 16,
    "slider_tick_size": 3,
    "slider_tick_spacing": 2,
    "slider_tick_thickness": 1,
    "slider_groove_height": 4,
    "progress_bar_groove_height": 6,
    "spacing": 8,
    "scroll_bar_thickness_full": 12,
    "scroll_bar_thickness_small": 6,
    "scroll_bar_margin": 0,
    "tab_bar_padding_top": 4,
    "tab_bar_tab_max_width": 0,
    "tab_bar_tab_min_width": 0,
}


class InputsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        line = QLineEdit(self)
        line.setPlaceholderText("Enter your name...")
        line.setClearButtonEnabled(True)
        layout.addWidget(line)

        layout.addWidget(QLabel("Category:"))
        combo = QComboBox(self)
        combo.addItems(["Option A", "Option B", "Option C"])
        layout.addWidget(combo)

        layout.addWidget(QLabel("Quantity:"))
        spin = QSpinBox(self)
        spin.setRange(0, 100)
        spin.setValue(10)
        layout.addWidget(spin)

        layout.addStretch()


class ControlsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        cb1 = QCheckBox("Enable feature", self)
        cb1.setChecked(True)
        cb2 = QCheckBox("Verbose mode", self)
        layout.addWidget(cb1)
        layout.addWidget(cb2)

        progress = QProgressBar(self)
        progress.setRange(0, 100)
        progress.setValue(50)
        layout.addWidget(progress)

        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(0, 100)
        slider.setValue(50)
        slider.valueChanged.connect(progress.setValue)
        layout.addWidget(slider)

        row = QHBoxLayout()
        row.addWidget(QPushButton("OK", self))
        btn_flat = QPushButton("Cancel", self)
        btn_flat.setFlat(True)
        row.addWidget(btn_flat)
        layout.addLayout(row)

        layout.addStretch()


class ListTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        lw = QListWidget(self)
        for i in range(8):
            lw.addItem(f"Item {i + 1}")
        layout.addWidget(lw)

        self._label = QLabel("Selected: (none)", self)
        layout.addWidget(self._label)
        lw.currentTextChanged.connect(lambda t: self._label.setText(f"Selected: {t}"))


class GroupsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        mode_group = QGroupBox("Mode", self)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.addWidget(QRadioButton("Auto", mode_group))
        rb = QRadioButton("Manual", mode_group)
        rb.setChecked(True)
        mode_layout.addWidget(rb)
        mode_layout.addWidget(QRadioButton("Scheduled", mode_group))
        layout.addWidget(mode_group)

        opts_group = QGroupBox("Options", self)
        opts_group.setCheckable(True)
        opts_layout = QVBoxLayout(opts_group)
        opts_layout.addWidget(QCheckBox("Notify on completion", opts_group))
        opts_layout.addWidget(QCheckBox("Save logs", opts_group))
        layout.addWidget(opts_group)

        layout.addStretch()


def _to_camel_case_dict(d: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively convert all dict keys from snake_case to camelCase."""
    out: dict[str, Any] = {}
    for key, value in d.items():
        part0, *rest = key.split("_")
        camel_key = part0 + "".join(p.capitalize() for p in rest)
        if isinstance(value, dict):
            value = _to_camel_case_dict(value)
        out[camel_key] = value
    return out


def make_qlementine_theme(theme: dict | None = None, /, **kwargs: Any) -> Theme:
    """Convert a ThemeDict or Theme configuration into a Qlementine.Theme instance."""
    camel_dict = _to_camel_case_dict({**(theme or {}), **kwargs})
    json_doc = QJsonDocument.fromVariant(camel_dict)
    return Theme.fromJsonDoc(json_doc)


def main() -> None:
    app = QApplication([])

    win = QMainWindow()
    win.setWindowTitle("QtAds + Qlementine Demo")

    CDockManager.setConfigFlag(CDockManager.eConfigFlag.DockAreaHasCloseButton, False)
    dock_manager = CDockManager(win)
    if "--plain" not in sys.argv:
        qlem = QlementineStyle()
        app.setStyle(AdsAwareStyle(qlem))
        qlem.setAutoIconColor(AutoIconColor.ForegroundColor)

        dock_manager.setStyleSheet("")

        if "--dark" in sys.argv:
            qt_theme = make_qlementine_theme(radix_slate_blue)
            qlem.setTheme(qt_theme)

    tabs = [
        ("Inputs", InputsTab()),
        ("Controls", ControlsTab()),
        ("List", ListTab()),
        ("Groups", GroupsTab()),
    ]

    area = None
    for name, widget in tabs:
        dw = CDockWidget(dock_manager, name, win)
        dw.setWidget(widget)
        if area is None:
            area = dock_manager.addDockWidget(DockWidgetArea.CenterDockWidgetArea, dw)
        else:
            dock_manager.addDockWidgetTabToArea(dw, area)

    win.resize(500, 400)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
