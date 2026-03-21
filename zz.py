from PyQt6Ads import DockWidgetArea

from pymmcore_gui._ads_style import AdsAwareStyle
from pymmcore_gui._qt.Qlementine import QlementineStyle
from pymmcore_gui._qt.QtAds import CDockManager, CDockWidget
from pymmcore_gui._qt.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

app = QApplication([])
app.setStyle(AdsAwareStyle(QlementineStyle()))

main = QMainWindow()
main.setWindowTitle("Ads + Qlementine Test")
main.resize(800, 500)

dock_manager = CDockManager(main)
dock_manager.setStyleSheet("")

# --- Panel 1: simple text editor ---
editor = QTextEdit()
editor.setPlaceholderText("Type something here...")
dock1 = CDockWidget(dock_manager, "Editor", main)
dock1.setWidget(editor)
area = dock_manager.addDockWidget(DockWidgetArea.LeftDockWidgetArea, dock1)

# --- Panel 2: a combo + label ---
w2 = QWidget()
lay2 = QVBoxLayout(w2)
combo = QComboBox()
combo.addItems(["Alpha", "Beta", "Gamma", "Delta"])
lay2.addWidget(QLabel("Pick one:"))
lay2.addWidget(combo)
lay2.addWidget(QPushButton("Go"))
lay2.addStretch()
dock2 = CDockWidget(dock_manager, "Controls", main)
dock2.setWidget(w2)
dock_manager.addDockWidget(DockWidgetArea.RightDockWidgetArea, dock2)

# --- Panel 3: a list (tabbed with Panel 2) ---
lst = QListWidget()
lst.addItems([f"Item {i}" for i in range(20)])
dock3 = CDockWidget(dock_manager, "List", main)
dock3.setWidget(lst)
dock_manager.addDockWidgetTabToArea(dock3, dock2.dockAreaWidget())

main.show()
app.exec()
