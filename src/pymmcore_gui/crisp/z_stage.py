from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus


class ZStage:
    """Interface to the Z-stage device.
    This is a simplified version for demonstration purposes.
    In a real implementation, this would communicate with the actual hardware.
    """

    def __init__(self, core: CMMCorePlus) -> None:
        self.core = core

        # Default values
        self._device_name = ""
        self._position = 0.0

    def find_device(self) -> bool:
        """Attempt to find the Z-stage device.
        In a real implementation, this would search for the device in the system.
        """
        # For demo purposes, always succeed
        self._device_name = "ZStage"
        return True

    def get_position(self):
        """Get the current Z position."""
        return self._position

    def set_position(self, position) -> None:
        """Set the Z position."""
        self._position = position

    def set_relative_position(self, delta) -> None:
        """Move the Z stage by a relative amount."""
        # In a real implementation, would move the actual device
        self._position += delta

    def get_name(self):
        """Get the device name."""
        return self._device_name
