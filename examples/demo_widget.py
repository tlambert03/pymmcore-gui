from PyQt6 import QtWidgets as QtW
from PyQt6.QtCore import Qt, QTimer
from superqt import QIconifyIcon


class TestWidget(QtW.QWidget):
    """Widget to test various PyQt6 widgets with styling."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("QWidget Styling Test")
        self.setMinimumSize(600, 400)

        toolbar = QtW.QToolBar("QToolBar")
        action = toolbar.addAction("Copy")
        if btn := toolbar.widgetForAction(action):
            btn.setObjectName("copy_action")

        toolbar.addAction(QIconifyIcon("mdi:content-paste"), "Paste")
        if act := toolbar.addAction(QIconifyIcon("mdi:toggle-switch"), "Toggle"):
            act.setCheckable(True)
            act.setChecked(True)

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
        widget_layout.addWidget(toolbar)
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
        main_layout = QtW.QVBoxLayout(self)
        main_layout.addLayout(widget_layout)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Capture a screenshot of the TestWidget.")
    parser.add_argument(
        "dest",
        nargs="?",
        default="demo_widget.png",
        help="Output file for the screenshot (default: demo_widget.png)",
    )
    parser.add_argument(
        "--theme",
        default="",
        help="Theme to apply to the application (default: macos-dark)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the application instead of capturing a screenshot",
    )
    args = parser.parse_args()
    app = QtW.QApplication([])
    if args.theme:
        from pymmcore_gui.theme.model import get_theme

        get_theme(args.theme).apply_to_qapplication(app)

    window = TestWidget()
    window.show()

    if args.run:
        app.exec()
    else:
        app.processEvents()
        QTimer.singleShot(10, lambda: window.grab().save(args.dest, "PNG"))
        app.processEvents()
