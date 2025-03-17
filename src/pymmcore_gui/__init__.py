"""A Micro-Manager GUI based on pymmcore-widgets and pymmcore-plus."""

from importlib.metadata import PackageNotFoundError, version

import pymmcore_plus.mda.handlers

from .writers._patch_pymmcore_plus import handler_for_path

pymmcore_plus.mda.handlers.handler_for_path = handler_for_path

try:
    __version__ = version("pymmcore-gui")
except PackageNotFoundError:
    __version__ = "uninstalled"

from ._main_window import MicroManagerGUI
from .actions import ActionInfo, CoreAction, WidgetAction

__all__ = ["ActionInfo", "CoreAction", "MicroManagerGUI", "WidgetAction"]
