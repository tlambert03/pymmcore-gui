from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import GroupPresetTableWidget

from pymmcore_gui._qt.Qlementine import QlementineStyle
from pymmcore_gui._qt.QtAds import CDockManager, CDockWidget, DockWidgetArea
from pymmcore_gui._qt.QtWidgets import QApplication, QMainWindow

app = QApplication([])
app.setStyle(QlementineStyle())

core = CMMCorePlus.instance()
core.loadSystemConfiguration()

main = QMainWindow()
dock_manager = CDockManager(main)
dock_manager.setStyleSheet("")

widget = GroupPresetTableWidget()
dock = CDockWidget(dock_manager, "Config Groups", main)
dock.setWidget(widget)
dock_manager.addDockWidget(DockWidgetArea.RightDockWidgetArea, dock)

main.show()
app.exec()
