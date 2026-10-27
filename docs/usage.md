# Using pymmcore-gui

## Launching the app

Double-click the bundled application, or run `mmgui` from a terminal in the
environment where you installed pymmcore-gui.

On first launch, no configuration is loaded, so there isn't much to control yet.  To
try the GUI without hardware, load Micro-Manager's demo devices with
**Devices > Load Demo Configuration**, or start the app with them:

```sh
mmgui run --demo-config
```

Load your own configuration from **Devices > Load System Configuration...**, or
create one with the Hardware Configuration Wizard (**Devices > Hardware Config
Wizard...**).  On later launches, the GUI offers to reload the last configuration you
used.

!!! note "Error reports"

    The first time you launch it, the app asks whether you'd like to send error
    reports to the developers (through [Sentry](https://sentry.io)).  This is opt-in:
    nothing is sent unless you agree, and the
    [privacy policy](https://github.com/pymmcore-plus/pymmcore-gui/blob/main/PRIVACY.md)
    lists what's included.  Your answer is saved in the app's settings
    (`mmgui settings --reset` clears it).  Starting the app with
    `mmgui run --no-telemetry` skips the question and doesn't send anything.

### Command-line options

`mmgui` is short for `mmgui run`, which starts the app.  It takes these options:

| Option | What it does |
| --- | --- |
| `-c FILE`, `--config FILE` | Load this Micro-Manager configuration file. |
| `--demo-config` | Load Micro-Manager's demo configuration. |
| `--no-telemetry` | Don't ask about (or send) error reports. |

For example, `mmgui run -c path/to/my_scope.cfg`.  (Spell out `run` when you pass
options.  Plain `mmgui -c FILE` works, but `mmgui --demo-config` does not.)

The app keeps its settings (window layout, last configuration, your answer about error
reports) in a settings file.  `mmgui settings --edit` opens that file,
`mmgui settings --reveal` shows it in your file browser, and `mmgui settings --reset`
restores the defaults.  `mmgui --version` prints the versions of pymmcore-gui,
pymmcore-plus and pymmcore.

## The console

The **Console** (in the **Window** menu, and the `>_` button in the toolbar) is an
IPython console running in the app itself.  It predefines a few names, so you can
script the running GUI:

- `mmc` (also `core` and `mmcore`): the [`CMMCorePlus`][pymmcore_plus.CMMCorePlus]
  the GUI is using;
- `mda`: its acquisition runner (`mmc.mda`);
- `window`: the main window;
- `np`, `useq`, and the top-level names from `pymmcore_plus` and `useq`
  (`MDASequence`, ...).

For example, `mmc.setExposure(50)` updates the exposure everywhere in the GUI.

## Launching from Python

Start the GUI from a script or an interactive session with
[`create_mmgui`][pymmcore_gui.create_mmgui]:

```python
from pymmcore_gui import create_mmgui

create_mmgui()
```

This call blocks until the window is closed (it runs the Qt event loop).

### Customizing before launch

Pass `exec_app=False` to get the main window back *before* the Qt event loop
starts, customize it, then start the event loop yourself.  (You don't need to create
a `QApplication`, because `create_mmgui` makes one for you.)

```python
from pymmcore_gui import create_mmgui
from qtpy.QtWidgets import QApplication

window = create_mmgui(exec_app=False)

# customize the window, or script the core it uses:
mmcore = window.mmcore

QApplication.instance().exec()
```

### Using your own core

By default, the GUI uses the global
[`CMMCorePlus.instance()`][pymmcore_plus.CMMCorePlus.instance], creating it if
needed, so any script can reach the same core the GUI is driving.  If you already have
a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] instance with a configuration loaded,
pass it in, along with `mm_config=False`:

```python
from pymmcore_gui import create_mmgui
from pymmcore_plus import CMMCorePlus

my_core = CMMCorePlus()
my_core.loadSystemConfiguration()  # or your own configuration file

create_mmgui(mmcore=my_core, mm_config=False)
```

Without `mm_config=False`, the GUI goes through its usual startup logic, and may load
(or offer to load) the last configuration you used on top of the one you set up.

### Adding your own widget

!!! warning "Experimental"

    Clearer paths for customizing the interface are on the to-do list, so this may
    change.

The panels in the **Window** menu are registered as
[`WidgetActionInfo`][pymmcore_gui.actions.WidgetActionInfo] objects, and you can
register your own.  Give it a unique `key`, the `text` to show in the menu, and a
function that takes the main window (the parent) and returns your widget.  Register
it *before* calling `create_mmgui`, and it shows up in the **Window** menu, and opens
as a dockable panel:

```python
from pymmcore_gui import create_mmgui
from pymmcore_gui.actions import WidgetActionInfo
from qtpy.QtWidgets import QApplication, QLabel


def make_notes(parent):
    return QLabel("Remember to turn off the laser!", parent)


WidgetActionInfo(key="mylab.notes", text="Lab Notes", create_widget=make_notes)

window = create_mmgui(exec_app=False)
window.get_widget("mylab.notes")  # (optional) open it right away
QApplication.instance().exec()
```

Widgets from [pymmcore-widgets](../pymmcore-widgets/widgets/index.md) work too.  The
`parent` passed to your function is the main window, so you can hand them the GUI's
core: `ExposureWidget(parent=parent, mmcore=parent.mmcore)`.
