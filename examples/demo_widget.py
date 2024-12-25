import sys
from dataclasses import asdict

from PyQt6 import QtWidgets as QtW
from PyQt6.QtCore import Qt


class TestWidget(QtW.QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("QWidget Styling Test")
        self.setMinimumSize(600, 400)

        # Main Layout
        main_layout = QtW.QVBoxLayout(self)

        # Label
        label = QtW.QLabel("QLabel: This is a test label.")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Line Edit
        line_edit = QtW.QLineEdit()
        line_edit.setPlaceholderText("QLineEdit: Type something here...")

        # Button
        button = QtW.QPushButton("QPushButton: Click Me")

        # Checkbox
        checkbox = QtW.QCheckBox("QCheckBox: Check me")

        # Radio Button
        radio_button = QtW.QRadioButton("QRadioButton: Select me")

        # Combo Box
        combo_box = QtW.QComboBox()
        combo_box.addItems(["QComboBox: Item 1", "Item 2", "Item 3"])

        # Slider
        slider = QtW.QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(50)

        # Spin Box
        spin_box = QtW.QSpinBox()
        spin_box.setRange(0, 100)

        # Progress Bar
        progress_bar = QtW.QProgressBar()
        progress_bar.setValue(40)

        # Tab Widget
        tab_widget = QtW.QTabWidget()
        tab1 = QtW.QWidget()
        tab2 = QtW.QWidget()
        tab_widget.addTab(tab1, "Tab 1")
        tab_widget.addTab(tab2, "Tab 2")

        # Table Widget
        table_widget = QtW.QTableWidget(3, 3)
        table_widget.setHorizontalHeaderLabels(["Column 1", "Column 2", "Column 3"])

        # Tree Widget
        tree_widget = QtW.QTreeWidget()
        tree_widget.setHeaderLabels(["Tree Widget"])
        for i in range(3):
            item = tree_widget.topLevelItem(i)
            tree_widget.addTopLevelItem(item)

        # Scroll Area
        scroll_area = QtW.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QtW.QLabel("QScrollArea: Scrollable content here.")
        scroll_content.setMinimumHeight(200)
        scroll_area.setWidget(scroll_content)

        # Group Box
        group_box = QtW.QGroupBox("QGroupBox: Grouped Widgets")
        group_box_layout = QtW.QVBoxLayout()
        group_box_layout.addWidget(QtW.QPushButton("Grouped Button"))
        group_box.setLayout(group_box_layout)

        # Plain Text Edit
        plain_text_edit = QtW.QPlainTextEdit()
        plain_text_edit.setPlainText("QPlainTextEdit: Editable text here.")

        # Text Edit
        text_edit = QtW.QTextEdit()
        text_edit.setHtml("<b>QTextEdit:</b> <i>Rich text editor with formatting.</i>")

        # Layouts for Widgets
        widget_layout = QtW.QVBoxLayout()
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


# Define the QSS template
QSS_TEMPLATE = """
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
}}

QPushButton::pressed {{
    background-color: #7B7B7B;
}}

/* --------------------------------------- */


QComboBox::drop-down:button {{
    border-radius:4px;
    background: {highlight};
}}

QComboBox::drop-down:button {{
    border-radius: 4px;
    margin: 1.5px;
    width: 14px;
    background-color: {highlight};
}}

QComboBox::down-arrow {{
    image: url(/Users/talley/Downloads/fluent--chevron-up-down-16-filled.svg);
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


"""

if __name__ == "__main__":
    from pymmcore_gui.theme.model import MACOS_DARK

    app = QtW.QApplication(sys.argv)
    app.setStyleSheet(QSS_TEMPLATE.format(**asdict(MACOS_DARK.active)))
    app.setPalette(MACOS_DARK.to_qpalette())
    window = TestWidget()
    window.show()
    sys.exit(app.exec())
