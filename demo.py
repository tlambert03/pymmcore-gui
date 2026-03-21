"""Simple demo of Qt widgets styled with Qlementine."""

from __future__ import annotations

import sys

from pymmcore_gui._qt.Qlementine import QlementineStyle
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
    QTabWidget,
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


class SimpleDemoWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simple Qt Demo")

        tabs = QTabWidget(self)
        self.setCentralWidget(tabs)
        tabs.addTab(InputsTab(self), "Inputs")
        tabs.addTab(ControlsTab(self), "Controls")
        tabs.addTab(ListTab(self), "List")
        tabs.addTab(GroupsTab(self), "Groups")

        self.resize(500, 400)


def main() -> None:
    """Run the simple demo."""
    import argparse

    parser = argparse.ArgumentParser(description="Simple Qt Demo")
    parser.add_argument(
        "--style",
        choices=["native", "fusion", "qlementine"],
        default="qlementine",
        help="widget style to use (default: qlementine)",
    )
    args, _ = parser.parse_known_args()
    app = QApplication([])
    if args.style == "fusion":
        app.setStyle("Fusion")
    elif args.style == "qlementine":
        qlem = QlementineStyle(app)
        qlem.setAnimationsEnabled(True)
        app.setStyle(qlem)

    window = SimpleDemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
