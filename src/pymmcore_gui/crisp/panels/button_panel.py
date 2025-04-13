from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from pymmcore_gui.crisp.crisp_device import CRISP
    from pymmcore_gui.crisp.crisp_timer import CRISPTimer
    from pymmcore_gui.crisp.panels.spinner_panel import SpinnerPanel


class ButtonPanel(QWidget):
    """A panel with buttons for calibrating CRISP."""

    def __init__(
        self, crisp: CRISP, timer: CRISPTimer, spinner_panel: SpinnerPanel
    ) -> None:
        super().__init__()

        self.crisp = crisp
        self.timer = timer
        self.spinner_panel = spinner_panel

        # Create buttons
        self.btn_idle = QPushButton("1: Idle")
        self.btn_logcal = QPushButton("2: Log Cal")
        self.btn_dither = QPushButton("3: Dither")
        self.btn_setgain = QPushButton("4: Set Gain")
        self.btn_reset = QPushButton("Reset Offsets")
        self.btn_save = QPushButton("Save Settings")

        self.btn_lock = QPushButton("Lock")
        self.btn_lock.setFixedHeight(60)
        self.btn_lock.setCheckable(True)
        font = self.btn_lock.font()
        font.setWeight(500)  # Bold
        self.btn_lock.setFont(font)

        # Connect button signals to slots
        self.btn_idle.clicked.connect(self.on_idle_clicked)
        self.btn_logcal.clicked.connect(self.on_log_cal_clicked)
        self.btn_dither.clicked.connect(self.on_dither_clicked)
        self.btn_setgain.clicked.connect(self.on_set_gain_clicked)
        self.btn_reset.clicked.connect(self.on_reset_offset_clicked)
        self.btn_save.clicked.connect(self.on_save_clicked)
        self.btn_lock.clicked.connect(self.on_focus_lock_clicked)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Add buttons to layout
        layout.addWidget(self.btn_idle)
        layout.addWidget(self.btn_logcal)
        layout.addWidget(self.btn_dither)
        layout.addWidget(self.btn_setgain)
        layout.addWidget(self.btn_reset)
        layout.addWidget(self.btn_save)
        layout.addStretch()
        layout.addWidget(self.btn_lock)

    def on_idle_clicked(self) -> None:
        """Set CRISP to idle mode."""
        self.crisp.set_state_idle()
        # Update UI components after state change
        self.spinner_panel.set_enabled_focus_lock_spinners(True)
        self.set_calibration_button_states(True)

    def on_log_cal_clicked(self) -> None:
        """Start CRISP log calibration."""
        self.crisp.set_state_log_cal()

    def on_dither_clicked(self) -> None:
        """Start CRISP dither calibration."""
        self.crisp.set_state_dither()

    def on_set_gain_clicked(self) -> None:
        """Set CRISP gain."""
        self.crisp.set_state_gain_cal()

    def on_reset_offset_clicked(self) -> None:
        """Reset CRISP offset."""
        self.crisp.reset_offset()

    def on_save_clicked(self) -> None:
        self.crisp.save()

    def on_focus_lock_clicked(self) -> None:
        """Toggle CRISP focus lock."""
        if self.crisp.is_focus_locked():
            # Already locked, so unlock
            self.crisp.set_state_idle()
            self.spinner_panel.set_enabled_focus_lock_spinners(True)
            self.set_calibration_button_states(True)
        else:
            print("Locking CRISP")
            # Not locked, so lock
            self.crisp.set_state_lock(True)
            self.spinner_panel.set_enabled_focus_lock_spinners(False)
            self.set_calibration_button_states(False)

    def on_refind_led_clicked(self) -> None:
        """Reset CRISP and refind LED."""
        # Stop timer if running
        was_polling = False
        if self.timer.is_running():
            was_polling = True
            self.timer.stop()

        # Reset CRISP
        self.crisp.reset()

        # Restart timer if it was running
        if was_polling:
            self.timer.start()

    def set_calibration_button_states(self, enabled: bool) -> None:
        """Enable/disable calibration buttons."""
        self.btn_idle.setEnabled(enabled)
        self.btn_logcal.setEnabled(enabled)
        self.btn_dither.setEnabled(enabled)
        self.btn_setgain.setEnabled(enabled)
