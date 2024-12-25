import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from pymmcore_gui.theme.model import MACOS_LIGHT


class TestWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("QWidget Styling Test")
        self.setMinimumSize(800, 600)

        # Main Layout
        main_layout = QVBoxLayout(self)

        # Label
        label = QLabel("QLabel: This is a test label.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Line Edit
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("QLineEdit: Type something here...")

        # Button
        button = QPushButton("QPushButton: Click Me")

        # Checkbox
        checkbox = QCheckBox("QCheckBox: Check me")

        # Radio Button
        radio_button = QRadioButton("QRadioButton: Select me")

        # Combo Box
        combo_box = QComboBox()
        combo_box.addItems(["QComboBox: Item 1", "Item 2", "Item 3"])

        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(50)

        # Spin Box
        spin_box = QSpinBox()
        spin_box.setRange(0, 100)

        # Progress Bar
        progress_bar = QProgressBar()
        progress_bar.setValue(40)

        # Tab Widget
        tab_widget = QTabWidget()
        tab1 = QWidget()
        tab2 = QWidget()
        tab_widget.addTab(tab1, "Tab 1")
        tab_widget.addTab(tab2, "Tab 2")

        # Table Widget
        table_widget = QTableWidget(3, 3)
        table_widget.setHorizontalHeaderLabels(["Column 1", "Column 2", "Column 3"])

        # Tree Widget
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabels(["Tree Widget"])
        for i in range(3):
            item = tree_widget.topLevelItem(i)
            tree_widget.addTopLevelItem(item)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QLabel("QScrollArea: Scrollable content here.")
        scroll_content.setMinimumHeight(200)
        scroll_area.setWidget(scroll_content)

        # Group Box
        group_box = QGroupBox("QGroupBox: Grouped Widgets")
        group_box_layout = QVBoxLayout()
        group_box_layout.addWidget(QPushButton("Grouped Button"))
        group_box.setLayout(group_box_layout)

        # Plain Text Edit
        plain_text_edit = QPlainTextEdit()
        plain_text_edit.setPlainText("QPlainTextEdit: Editable text here.")

        # Text Edit
        text_edit = QTextEdit()
        text_edit.setHtml("<b>QTextEdit:</b> <i>Rich text editor with formatting.</i>")

        # Layouts for Widgets
        widget_layout = QVBoxLayout()
        widget_layout.addWidget(label)
        widget_layout.addWidget(line_edit)
        widget_layout.addWidget(button)
        widget_layout.addWidget(checkbox)
        widget_layout.addWidget(radio_button)
        widget_layout.addWidget(combo_box)
        widget_layout.addWidget(slider)
        widget_layout.addWidget(spin_box)
        widget_layout.addWidget(progress_bar)
        widget_layout.addWidget(tab_widget)
        widget_layout.addWidget(table_widget)
        widget_layout.addWidget(tree_widget)
        widget_layout.addWidget(scroll_area)
        widget_layout.addWidget(group_box)
        widget_layout.addWidget(plain_text_edit)
        widget_layout.addWidget(text_edit)

        # Add Widgets to Main Layout
        main_layout.addLayout(widget_layout)
        self.setLayout(main_layout)


if __name__ == "__main__":
    from rich import print

    from pymmcore_gui.theme.model import MACOS_DARK

    app = QApplication(sys.argv)
    print(MACOS_DARK)
    app.setPalette(MACOS_LIGHT.to_qpalette())
    window = TestWidget()
    window.show()
    sys.exit(app.exec())
