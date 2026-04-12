from __future__ import annotations

import sys
from pathlib import Path

from pymmcore_plus import CMMCorePlus
from superqt import QIconifyIcon

from pymmcore_gui._qt.QtCore import Qt
from pymmcore_gui._qt.QtGui import QIcon
from pymmcore_gui._qt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ._layout import (
    ItemBar,
    PanelAlignment,
    ViewContainerLocation,
    ViewDescriptor,
    WorkbenchWidget,
)
from .widgets._configure_widget import ConfigureModeWidget

RESOURCES = Path(__file__).parent / "resources"
ICON = RESOURCES / ("icon.ico" if sys.platform.startswith("win") else "logo.png")

# ---- Status Bar -----------------------------------------------------------


class StatusBar(QStatusBar):
    """Status bar with a notification bell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bell_button = QPushButton(QIconifyIcon("codicon:bell"), "")
        self.bell_button.setFlat(True)
        self.addPermanentWidget(self.bell_button)


# ---- Helper ---------------------------------------------------------------


def _make_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("font-size: 18px; color: gray;")
    return lbl


# ---- View descriptors -----------------------------------------------------
#
# Declared at module level so that the set of views is static data rather
# than imperative setup inside ``__init__``. Mirrors VS Code's pattern of
# registering views at module import via ``contribution`` files.

_PLACEHOLDER_VIEWS: tuple[ViewDescriptor, ...] = (
    ViewDescriptor(
        id="explorer",
        name="Explorer",
        factory=lambda: _make_label("Explorer"),
        icon=QIconifyIcon("codicon:files"),
        default_location=ViewContainerLocation.LEFT_SIDEBAR,
    ),
    ViewDescriptor(
        id="search",
        name="Search",
        factory=lambda: _make_label("Search"),
        icon=QIconifyIcon("codicon:search"),
        default_location=ViewContainerLocation.LEFT_SIDEBAR,
    ),
    ViewDescriptor(
        id="source-control",
        name="Source Control",
        factory=lambda: _make_label("Source Control"),
        icon=QIconifyIcon("codicon:source-control"),
        default_location=ViewContainerLocation.LEFT_SIDEBAR,
    ),
    ViewDescriptor(
        id="properties",
        name="Properties",
        factory=lambda: _make_label("Properties"),
        icon=QIconifyIcon("codicon:settings-gear"),
        default_location=ViewContainerLocation.RIGHT_SIDEBAR,
    ),
    ViewDescriptor(
        id="terminal",
        name="Terminal",
        factory=lambda: _make_label("Terminal"),
        icon=QIconifyIcon("codicon:terminal"),
        default_location=ViewContainerLocation.PANEL,
    ),
    ViewDescriptor(
        id="console",
        name="Console",
        factory=lambda: _make_label("Console"),
        icon=QIconifyIcon("codicon:output"),
        default_location=ViewContainerLocation.PANEL,
    ),
)

_INITIAL_ACTIVE_VIEWS: tuple[str, ...] = ("explorer", "properties", "terminal")


# ---- Main Window ----------------------------------------------------------


class MicroManagerGUI(QMainWindow):
    def __init__(self, *, mmcore: CMMCorePlus | None = None) -> None:
        super().__init__()
        self.setWindowTitle("pyMM")
        self.setWindowIcon(QIcon(str(ICON)))
        self.setObjectName("MicroManagerGUI")

        self._mmc = mmcore or CMMCorePlus.instance()

        # ---- mode widgets ----
        self._configure_mode = ConfigureModeWidget(self)
        self._acquire_mode = WorkbenchWidget(central=_make_label("Editor Area"))

        # Register placeholder views from the module-level descriptor list.
        wb = self._acquire_mode
        for desc in _PLACEHOLDER_VIEWS:
            wb.registerView(desc)
        for view_id in _INITIAL_ACTIVE_VIEWS:
            wb.setActiveView(view_id)

        # ---- set icons on workbench actions ----
        wb.setActionIcons(
            wb.toggleLeftSidebarAction,
            QIconifyIcon("codicon:layout-sidebar-left"),
            QIconifyIcon("codicon:layout-sidebar-left-off"),
        )
        wb.setActionIcons(
            wb.togglePanelAction,
            QIconifyIcon("codicon:layout-panel"),
            QIconifyIcon("codicon:layout-panel-off"),
        )
        wb.setActionIcons(
            wb.toggleRightSidebarAction,
            QIconifyIcon("codicon:layout-sidebar-right"),
            QIconifyIcon("codicon:layout-sidebar-right-off"),
        )
        wb.setAlignmentIcons(
            {
                PanelAlignment.LEFT: QIconifyIcon("codicon:layout-panel-left"),
                PanelAlignment.CENTER: QIconifyIcon("codicon:layout-panel-center"),
                PanelAlignment.RIGHT: QIconifyIcon("codicon:layout-panel-right"),
                PanelAlignment.JUSTIFY: QIconifyIcon("codicon:layout-panel-justify"),
            }
        )

        # ---- mode stack ----
        self._mode_stack = QStackedWidget()
        self._mode_stack.addWidget(self._configure_mode)
        self._mode_stack.addWidget(self._acquire_mode)

        # ---- mode switcher (top bar) ----
        # ItemBar in horizontal text-only mode is a perfect fit: a
        # mutually-exclusive list of two text labels with an animated
        # selection underline.
        self._navigation = ItemBar(orientation=Qt.Orientation.Horizontal)
        self._navigation.setCollapsible(False)  # one mode is always active
        self._navigation.addItem("configure", "Configure")
        self._navigation.addItem("acquire", "Acquire")
        self._navigation.setActiveSilent("configure")
        self._mode_stack.setCurrentIndex(0)
        self._navigation.itemToggled.connect(self._on_mode_changed)

        # ---- layout ----
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)
        top_row.addWidget(self._navigation)
        top_row.addStretch()
        top_row.addWidget(wb.stateButtons())

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top_row)
        layout.addWidget(self._mode_stack, 1)
        self.setCentralWidget(central)

        # ---- status bar ----
        self._status_bar = StatusBar(self)
        self.setStatusBar(self._status_bar)

        self.resize(1200, 800)

    # ---- public API -------------------------------------------------------
    _MODE_IDS = ("configure", "acquire")

    def setMode(self, mode: str | int) -> None:
        """Set the current mode ('configure' / 'acquire' or index 0/1)."""
        if isinstance(mode, str):
            mid = mode.lower()
            if mid not in self._MODE_IDS:
                raise ValueError(f"Invalid mode: {mode!r}")
        elif isinstance(mode, int):
            if not (0 <= mode < len(self._MODE_IDS)):
                raise ValueError(f"Invalid mode index: {mode}")
            mid = self._MODE_IDS[mode]
        else:
            raise TypeError(f"Mode must be a string or integer, got {type(mode)}")
        self._navigation.setActive(mid)

    @property
    def mmcore(self) -> CMMCorePlus:
        return self._mmc

    @property
    def acquire_mode(self) -> WorkbenchWidget:
        return self._acquire_mode

    @property
    def configure_mode(self) -> ConfigureModeWidget:
        return self._configure_mode

    # ---- internals --------------------------------------------------------

    def _on_mode_changed(self, item_id: str) -> None:
        if item_id in self._MODE_IDS:
            self._mode_stack.setCurrentIndex(self._MODE_IDS.index(item_id))


# ---- Standalone entry point ------------------------------------------------
# Run with: ``python -m pymmcore_gui._modern_window``


def main() -> None:
    from pymmcore_gui._ads_style import AdsAwareQlementineStyle, apply_dark_theme
    from pymmcore_gui._qt.QtWidgets import QApplication

    app = QApplication(sys.argv)
    style = AdsAwareQlementineStyle()
    apply_dark_theme(style)
    app.setStyle(style)

    win = MicroManagerGUI()
    win.setMode("acquire")
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
