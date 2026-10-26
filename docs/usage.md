# Using pymmcore-gui

## Launching the app

Double-click the bundled application, or run `mmgui` from a terminal in the
environment where you installed pymmcore-gui.

If no configuration is loaded, the GUI uses Micro-Manager's demo devices, so you
can try it without any hardware.  Load your own configuration from the
**Devices** menu, or create one with the Hardware Configuration Wizard.

## Launching from Python

Start the GUI from a script or an interactive session with
[`create_mmgui`][pymmcore_gui.create_mmgui]:

```python
from pymmcore_gui import create_mmgui

create_mmgui()
```

### Customizing before launch

Pass `exec_app=False` to get the main window back *before* the Qt event loop
starts, customize it, then start the event loop yourself:

```python
from pymmcore_gui import create_mmgui
from pymmcore_gui._qt.QtWidgets import QApplication

window = create_mmgui(exec_app=False)

# customize the window, or script the core it uses:
mmcore = window.mmcore

QApplication.instance().exec()
```

### Using your own core

If you already have a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] instance, pass
it with `create_mmgui(mmcore=my_core)`.  Otherwise the GUI uses the global
[`CMMCorePlus.instance()`][pymmcore_plus.CMMCorePlus.instance], creating it if
needed, so any script can reach the same core the GUI is driving.
