"""Same demo as demo.py but using QtAds dock widgets instead of QTabWidget."""

from __future__ import annotations

import sys

from pymmcore_gui._ads_style import AdsAwareQlementineStyle, apply_dark_theme
from pymmcore_gui._qt.QtAds import CDockManager, CDockWidget, DockWidgetArea
from pymmcore_gui._qt.QtCore import Qt
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


def main() -> None:
    app = QApplication([])

    # Set style and theme BEFORE creating widgets
    if "--plain" not in sys.argv:
        style = AdsAwareQlementineStyle()
        if "--dark" in sys.argv:
            apply_dark_theme(style)
        app.setStyle(style)

    win = QMainWindow()
    win.setWindowTitle("QtAds + Qlementine Demo")

    CDockManager.setConfigFlag(CDockManager.eConfigFlag.DockAreaHasCloseButton, False)
    dock_manager = CDockManager(win)
    dock_manager.setStyleSheet("")

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
