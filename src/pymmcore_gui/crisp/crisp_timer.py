#!/usr/bin/env python3
# Project: ASI CRISP Control - Timer for CRISP Polling
# License: BSD 3-clause

from PyQt6.QtCore import QTimer


class CRISPTimer:
    """Timer to poll the CRISP device and update the UI."""

    def __init__(self, crisp) -> None:
        self.crisp = crisp
        self.timer = QTimer()
        self.status_panel = None
        self.interval = 100  # Default interval in milliseconds
        self._running = False

        # Counter for skipping polling when device is unresponsive
        self._skip_count = 0
        self._skip_polling = False

    def create_timer_task(self, status_panel) -> None:
        """Set up the timer task to update the status panel."""
        self.status_panel = status_panel
        self.timer.timeout.connect(self.update_task)

    def update_task(self) -> None:
        """Update task that runs on timer ticks."""
        # Skip polling if needed (used during log_cal when device may be unresponsive)
        if self._skip_polling:
            self._skip_count -= 1
            if self._skip_count <= 0:
                self._skip_polling = False
            return

        if self.status_panel:
            # In a real implementation, this would poll the actual device
            # For demo, we'll just update the status panel
            self.status_panel.update()

    def start(self) -> None:
        """Start the timer."""
        if not self._running:
            self.timer.start(self.interval)
            self._running = True

    def stop(self) -> None:
        """Stop the timer."""
        if self._running:
            self.timer.stop()
            self._running = False

    def is_running(self):
        """Check if timer is running."""
        return self._running

    def set_interval(self, interval) -> None:
        """Set the timer interval in milliseconds."""
        self.interval = interval
        if self._running:
            self.timer.setInterval(interval)

    def on_log_cal(self) -> None:
        """Called when log_cal is started.
        The controller becomes unresponsive during Log Cal,
        so we skip polling for a few timer ticks.
        """
        self._skip_count = 30  # Skip about 3 seconds of polling (30 * 100ms)
        self._skip_polling = True
