from PyQt6.QtWidgets import QApplication
from rich import print

from pymmcore_gui.theme.model import Palette

app = QApplication([])
qpal = app.palette()

pal = Palette.from_qpalette(qpal)
print(pal)
print(pal.to_qpalette())
assert pal == Palette.from_qpalette(pal.to_qpalette())
