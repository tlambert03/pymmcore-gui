#!/usr/bin/env python3
# Project: ASI CRISP Control
# License: BSD 3-clause
# Author: Converted to PyQt6 from original Java version by Brandon Simpson


from pymmcore_plus import CMMCorePlus
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .crisp_device import CRISP
from .crisp_timer import CRISPTimer
from .panels.button_panel import ButtonPanel
from .panels.plot_panel import PlotPanel
from .panels.spinner_panel import SpinnerPanel
from .panels.status_panel import StatusPanel
from .user_settings import UserSettings
from .z_stage import ZStage


class CRISPWidget(QWidget):
    """The main window that opens when the plugin is selected in Micro-Manager."""

    # DEBUG => flag to turn on debug mode when editing the ui
    DEBUG = False

    def __init__(self, core: CMMCorePlus, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.core = core

        self.crisp = CRISP(core)
        self.z_stage = ZStage(core)
        self.timer = CRISPTimer(self.crisp)

        # save/load user settings
        self.settings = UserSettings(self.crisp, self.timer, self)

        # Create central widget and main layout
        self.setWindowTitle("CRISP Control")

        if self.crisp.detect_device():
            self.create_user_interface()  # some ui panels require both crisp and the timer
            self.init()  # called after ui is created because it updates the panels
            print("STATE", self.crisp.get_state())
        else:
            # If CRISP device is not detected, create a simple error interface
            self.create_error_interface()

    def init(self) -> None:
        """Updates panels and starts the timer."""
        # find the Z stage
        self.z_stage.find_device()

        # query values from CRISP and update the ui
        self.spinner_panel.set_axis_label_text(self.crisp.get_axis_string())

        # the timer task updates the status panel
        self.timer.create_timer_task(self.status_panel)

        # load settings
        self.settings.load()

        # update panels after we load the settings
        self.spinner_panel.update()
        self.status_panel.update()

        # start the timer if polling CheckBox enabled
        if self.spinner_panel.is_polling_enabled():
            self.timer.start()

        # disable spinners if already focus locked
        if self.crisp.is_focus_locked():
            self.spinner_panel.set_enabled_focus_lock_spinners(False)
            self.button_panel.set_calibration_button_states(False)

        # disable update rate spinner if using old firmware
        if self.crisp.get_device_type() == "TIGER":
            if self.crisp.get_firmware_version() < 3.38:
                self.spinner_panel.set_enabled_update_rate_spinner(False)
        elif (
            self.crisp.get_firmware_version() < 9.2
            or self.crisp.get_firmware_version_letter() < "n"
        ):
            self.spinner_panel.set_enabled_update_rate_spinner(False)

    def create_error_interface(self) -> None:
        """This UI is created when the plugin encounters an error when trying to detect CRISP."""
        # window settings
        # self.setFixedSize(400, 250)

        # Create layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title label
        title_label = QLabel("CRISP Control: Error")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Error message
        error_label = QLabel("This plugin requires an ASI CRISP Autofocus device.")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Help message
        help_label = QLabel(
            "Add the CRISP device from the <b>ASIStage</b> or "
            "<b>ASITiger</b><br> device adapter in the Hardware Configuration Wizard.",
        )
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add widgets to layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(error_label)
        main_layout.addWidget(help_label)

    def create_user_interface(self) -> None:
        """Create the user interface for the plugin."""
        # Title
        title_label = QLabel("CRISP Control")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create panels
        self.spinner_panel = SpinnerPanel(self.crisp, self.timer)
        self.button_panel = ButtonPanel(self.crisp, self.timer, self.spinner_panel)
        self.status_panel = StatusPanel(self.crisp)
        self.plot_panel = PlotPanel(self)

        # Create left and right panels
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.spinner_panel)
        left_layout.addWidget(self.status_panel)

        top_layout = QHBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addWidget(self.button_panel, 0)
        # bot_layout = QVBoxLayout()

        # Add sub-panels to main panels
        # bot_layout.addWidget(self.button_panel)

        # Create panel layout
        panel_layout = QHBoxLayout()
        panel_layout.addLayout(top_layout)
        # panel_layout.addLayout(bot_layout)

        # Add components to main layout
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(title_label)
        main_layout.addLayout(panel_layout)
        # main_layout.addWidget(self.plot_panel)

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.timer.stop()
        self.settings.save()
        event.accept()

    def open_website(self) -> None:
        """Open the CRISP website."""
        import webbrowser

        webbrowser.open(
            "https://www.asiimaging.com/products/focus-control-and-stabilization/crisp-autofocus-system",
        )

    def open_manual(self) -> None:
        """Open the CRISP manual."""
        import webbrowser

        webbrowser.open("http://asiimaging.com/docs/crisp_mm_plugin")

    # Getter methods
    def get_spinner_panel(self):
        return self.spinner_panel

    def get_timer(self):
        return self.timer

    def get_crisp(self):
        return self.crisp

    def get_z_stage(self):
        return self.z_stage
