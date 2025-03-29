#!/usr/bin/env python3
# Project: ASI CRISP Control - Status Panel
# License: BSD 3-clause

from PyQt6.QtWidgets import QFormLayout, QLabel, QWidget

from pymmcore_gui.crisp.crisp_device import CRISP


class StatusPanel(QWidget):
    """Displays values being queried from CRISP by the polling task."""

    def __init__(self, crisp: CRISP) -> None:
        super().__init__()

        self.crisp = crisp

        self._state = QLabel("State")
        self._error = QLabel("###")
        self._snr = QLabel("###")
        self._agc = QLabel("###")
        self._sum = QLabel("###")
        self._offset = QLabel("###")

        # Create layout
        layout = QFormLayout(self)
        layout.addRow(QLabel("CRISP Status"), self._state)
        layout.addRow(QLabel("Error"), self._error)
        layout.addRow(QLabel("SNR"), self._snr)
        layout.addRow(QLabel("AGC"), self._agc)
        layout.addRow(QLabel("Sum"), self._sum)
        layout.addRow(QLabel("Offset"), self._offset)

        # Update status values
        self._update()

    def _update(self) -> None:
        """Update displayed values from CRISP."""
        self._state.setText(self.crisp.get_state())
        self._error.setText(f"{self.crisp.get_error():.2f}")
        self._snr.setText(f"{self.crisp.get_snr():.2f}")
        self._agc.setText(f"{self.crisp.get_agc():.2f}")
        self._sum.setText(f"{self.crisp.get_sum():.2f}")
        self._offset.setText(f"{self.crisp.get_offset():.2f}")
