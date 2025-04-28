# pyright: reportCallIssue=none
import pymmcore_widgets as pmmw
from app_model.expressions import Name
from app_model.types import Action, KeyBindingRule, KeyCode, KeyMod
from pymmcore_plus import CMMCorePlus
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6Ads import DockWidgetArea, SideBarLocation

from pymmcore_gui.actions import ActionKey
from pymmcore_gui.widgets._exception_log import ExceptionLog
from pymmcore_gui.widgets._mm_console import MMConsole
from pymmcore_gui.widgets._stage_control import StagesControlWidget

# ######################### Global State Keys #########################

IS_ACQUISITION_RUNNING = Name[bool]("is_acquisition_running")


# ######################## Functions acting on the Core #########################
class CoreAction(ActionKey):
    """Actions that act on the global CMMCore instance."""

    SNAP = "pymm.snap_image"
    TOGGLE_LIVE = "pymm.toggle_live"
    LOAD_DEMO_CONFIG = "pymm.load_demo_config"


def snap_image(mmcore: CMMCorePlus) -> None:
    """Snap an image, stopping sequence if running."""
    if mmcore.isSequenceRunning():
        mmcore.stopSequenceAcquisition()
    mmcore.snapImage()


def toggle_live(mmcore: CMMCorePlus) -> None:
    """Start or stop live mode."""
    if mmcore.isSequenceRunning():
        mmcore.stopSequenceAcquisition()
    else:
        mmcore.startContinuousSequenceAcquisition(0)


def load_demo_config(mmcore: CMMCorePlus) -> None:
    """Load the demo configuration."""
    mmcore.loadSystemConfiguration()


# ######################## Functions that create widgets #########################


class WidgetAction(ActionKey):
    """Widget Actions toggle/create singleton widgets."""

    ABOUT = "pymm.wdg.about_widget"
    PROP_BROWSER = "pymm.wdg.property_browser"
    PIXEL_CONFIG = "pymm.wdg.pixel_config_widget"
    INSTALL_DEVICES = "pymm.wdg.install_devices_widget"
    MDA_WIDGET = "pymm.wdg.mda_widget"
    CONFIG_GROUPS = "pymm.wdg.config_groups_widget"
    CAMERA_ROI = "pymm.wdg.camera_roi_widget"
    CONSOLE = "pymm.wdg.console"
    EXCEPTION_LOG = "pymm.wdg.exception_log"
    STAGE_CONTROL = "pymm.wdg.stage_control_widget"
    CONFIG_WIZARD = "pymm.wdg.hardware_config_wizard"


def create_property_browser(mmcore: CMMCorePlus) -> pmmw.PropertyBrowser:
    """Create a Property Browser widget."""
    from pymmcore_widgets import PropertyBrowser

    return PropertyBrowser(mmcore=mmcore)


def create_mm_console() -> MMConsole:
    """Create a console widget."""
    from pymmcore_gui.widgets._mm_console import MMConsole

    return MMConsole()


def create_install_widgets() -> pmmw.InstallWidget:
    """Create the Install Devices widget."""
    from pymmcore_widgets import InstallWidget

    class InstallDialog(QDialog, InstallWidget): ...

    wdg = InstallDialog()
    wdg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
    wdg.resize(800, 400)
    return wdg


def create_mda_widget(mmcore: CMMCorePlus) -> pmmw.MDAWidget:
    """Create the MDA widget."""
    # from pymmcore_gui.widgets import _MDAWidget
    from pymmcore_widgets import MDAWidget

    return MDAWidget(mmcore=mmcore)


def create_camera_roi(mmcore: CMMCorePlus) -> pmmw.CameraRoiWidget:
    """Create the Camera ROI widget."""
    from pymmcore_widgets import CameraRoiWidget

    return CameraRoiWidget(mmcore=mmcore)


def create_config_groups(mmcore: CMMCorePlus) -> pmmw.GroupPresetTableWidget:
    """Create the Config Groups widget."""
    from pymmcore_widgets import GroupPresetTableWidget

    return GroupPresetTableWidget(mmcore=mmcore)


def create_pixel_config(mmcore: CMMCorePlus) -> pmmw.PixelConfigurationWidget:
    """Create the Pixel Configuration widget."""
    from pymmcore_widgets import PixelConfigurationWidget

    return PixelConfigurationWidget(mmcore=mmcore)


def create_exception_log() -> ExceptionLog:
    """Create the Exception Log widget."""
    from pymmcore_gui.widgets._exception_log import ExceptionLog

    wdg = ExceptionLog()
    wdg.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
    wdg.resize(800, 400)
    return wdg


def create_stage_widget(mmcore: CMMCorePlus) -> StagesControlWidget:
    """Create the Stage Control widget."""
    from pymmcore_gui.widgets._stage_control import StagesControlWidget

    return StagesControlWidget(mmcore=mmcore)


def create_config_wizard(mmcore: CMMCorePlus) -> pmmw.ConfigWizard:
    """Create the Hardware Configuration Wizard."""
    from pymmcore_widgets import ConfigWizard

    config_file = mmcore.systemConfigurationFile() or ""
    return ConfigWizard(config_file=config_file, core=mmcore)


def create_about_widget() -> QWidget:
    """Create an "about this program" widget."""
    from pymmcore_gui.widgets._about_widget import AboutWidget

    return AboutWidget()


# ######################## Actions for the GUI #########################

ACTIONS: list[Action] = [
    Action(
        id=CoreAction.SNAP,
        title="Snap Image",
        icon="mdi-light:camera",
        callback=snap_image,
        keybindings=[
            KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyK),
        ],
    ),
    Action(
        id=CoreAction.TOGGLE_LIVE,
        title="Toggle Live",
        icon="mdi:video-outline",
        callback=toggle_live,
        keybindings=[
            KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyL),
        ],
        toggled=IS_ACQUISITION_RUNNING,
    ),
    Action(
        id=CoreAction.LOAD_DEMO_CONFIG,
        title="Load Demo Configuration",
        icon="mdi:video-outline",
        callback=load_demo_config,
    ),
    Action(
        id=WidgetAction.ABOUT,
        title="About Pymmcore Gui",
        callback=create_about_widget,
    ),
    Action(
        id=WidgetAction.CONSOLE,
        title="Console",
        shortcut="Ctrl+Shift+C",
        icon="iconoir:terminal",
        callback=create_mm_console,
        dock_area=DockWidgetArea.BottomDockWidgetArea,
    ),
    Action(
        id=WidgetAction.PROP_BROWSER,
        title="Property Browser",
        shortcut="Ctrl+Shift+P",
        icon="mdi-light:format-list-bulleted",
        callback=create_property_browser,
        dock_area=SideBarLocation.SideBarLeft,
    ),
    Action(
        id=WidgetAction.INSTALL_DEVICES,
        title="Install Devices",
        shortcut="Ctrl+Shift+I",
        icon="mdi-light:download",
        callback=create_install_widgets,
    ),
    Action(
        id=WidgetAction.MDA_WIDGET,
        title="MDA",
        shortcut="Ctrl+Shift+M",
        icon="qlementine-icons:cube-16",
        callback=create_mda_widget,
    ),
    Action(
        id=WidgetAction.CAMERA_ROI,
        title="Camera ROI",
        shortcut="Ctrl+Shift+R",
        icon="material-symbols-light:screenshot-region-rounded",
        callback=create_camera_roi,
        dock_area=DockWidgetArea.LeftDockWidgetArea,
    ),
    Action(
        id=WidgetAction.CONFIG_GROUPS,
        title="Config Groups",
        shortcut="Ctrl+Shift+G",
        icon="mdi-light:format-list-bulleted",
        callback=create_config_groups,
        dock_area=DockWidgetArea.LeftDockWidgetArea,
    ),
    Action(
        id=WidgetAction.PIXEL_CONFIG,
        title="Pixel Size Configuration",
        shortcut="Ctrl+Shift+X",
        icon="mdi-light:grid",
        callback=create_pixel_config,
    ),
    Action(
        id=WidgetAction.EXCEPTION_LOG,
        title="Exception Log",
        shortcut="Ctrl+Shift+E",
        icon="mdi-light:alert",
        callback=create_exception_log,
    ),
    Action(
        id=WidgetAction.STAGE_CONTROL,
        title="Stage Control",
        shortcut="Ctrl+Shift+S",
        icon="fa:arrows",
        callback=create_stage_widget,
        dock_area=DockWidgetArea.LeftDockWidgetArea,
    ),
    Action(
        id=WidgetAction.CONFIG_WIZARD,
        title="Hardware Config Wizard",
        icon="mdi:cog",
        callback=create_config_wizard,
    ),
]
