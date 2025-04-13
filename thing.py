from pymmcore_plus import CMMCorePlus
from PyQt6.QtWidgets import QApplication

from pymmcore_gui.crisp.crisp_widget import CRISPWidget

if __name__ == "__main__":
    app = QApplication([])
    core = CMMCorePlus()
    window = CRISPWidget(core)
    window.show()
    app.exec()
