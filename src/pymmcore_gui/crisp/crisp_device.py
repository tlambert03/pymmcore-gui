#!/usr/bin/env python3
# Project: ASI CRISP Control - CRISP Device Interface
# License: BSD 3-clause

from pymmcore_plus import CMMCorePlus

from .crisp_settings import CRISPSettings


class ControllerType:
    """Controller type constants."""

    NONE = "NONE"
    TIGER = "TIGER"
    MS2000 = "MS2000"


class CRISP:
    """Interface to the ASI CRISP autofocus device.
    In a real implementation, this would communicate with the actual hardware.
    """

    # CRISP state constants
    STATE_IDLE = 0
    STATE_LOCKED = 1
    STATE_LOGGING = 2
    STATE_LOGGINGEXT = 3
    STATE_DITHERING = 4
    STATE_GAINCAL = 5

    # Device library constants
    class DeviceLibrary:
        TIGER = "ASITiger"
        MS2000 = "ASIStage"

    # Device description constants
    class Description:
        TIGER = "ASI CRISP AutoFocus"
        MS2000 = "ASI CRISP Autofocus adapter"

    # Number of MM::Strings used for the focus curve data property
    FC_DATA_SIZE = 24

    def __init__(self, core: CMMCorePlus) -> None:
        self.core = core

        # Device properties
        self._device_name = ""
        self._device_type = ControllerType.NONE
        self._firmware_version = 0.0
        self._firmware_version_letter = " "

        # Settings
        self.settings: list[CRISPSettings] = []
        self.settings_index = 0

        # Add default settings profile
        self.settings.append(CRISPSettings(name=CRISPSettings.DEFAULT_PROFILE_NAME))

        # Default hardware values (used when not connected to real hardware)
        self._state = self.STATE_IDLE
        self._error = 0.0
        self._snr = 25.0
        self._agc = 75.0
        self._sum = 1024.0
        self._offset = 0.0
        self._axis = "Z"
        self._loop_gain = 50  # Not part of CRISPSettings

    def __str__(self) -> str:
        """String representation of the device."""
        return f"CRISP[deviceName={self._device_name}, deviceType={self._device_type}]"

    def get_settings_list(self) -> list[CRISPSettings]:
        """Get the list of settings profiles."""
        return self.settings

    def get_settings(self) -> CRISPSettings:
        """Get the current settings profile."""
        return self.settings[self.settings_index]

    def get_settings_by_index(self, index: int) -> CRISPSettings:
        """Get settings profile by index."""
        return self.settings[index]

    def get_num_settings(self) -> int:
        """Get the number of settings profiles."""
        return len(self.settings)

    def add_settings(self) -> str:
        """Add a new settings profile."""
        name = f"{CRISPSettings.NAME_PREFIX}{len(self.settings)}"
        self.settings.append(CRISPSettings(name=name))
        return name

    def remove_settings(self) -> bool:
        """Remove the last settings profile."""
        if len(self.settings) == 1:
            return False
        self.settings.pop()
        return True

    def set_settings_index(self, index: int) -> None:
        """Set the current settings profile index."""
        self.settings_index = index

    def get_settings_from_device(self) -> CRISPSettings:
        """Get current device settings as a CRISPSettings object."""
        return CRISPSettings(
            name="Current Values",
            gain=self.get_cal_gain(),
            led_intensity=self.get_led_intensity(),
            update_rate_ms=self.get_update_rate(),
            num_averages=self.get_num_averages(),
            objective_na=self.get_objective_na(),
            lock_range=self.get_lock_range(),
        )

    def detect_device(self) -> bool:
        """Attempt to detect the CRISP device.
        In a real implementation, this would search for the device in the system.
        """
        # For demo purposes, always succeed
        self._device_name = "CRISP"
        self._device_type = ControllerType.TIGER
        self._firmware_version = 3.40
        self._firmware_version_letter = "p"
        return True

    def reset(self) -> None:
        """Reset the CRISP device."""
        self._state = self.STATE_IDLE
        self._error = 0.0
        self._offset = 0.0

    def reset_offset(self) -> None:
        """Reset the CRISP offset value."""
        self._offset = 0.0

    # State control methods
    def set_state_idle(self) -> None:
        """Set CRISP to idle mode."""
        self._state = self.STATE_IDLE

    def set_state_lock(self) -> None:
        """Set CRISP to locked mode."""
        self._state = self.STATE_LOCKED

    def set_state_log_cal(self, timer=None) -> None:
        """Start CRISP log calibration."""
        self._state = self.STATE_LOGGING

        # Handle firmware-specific timer behavior
        if timer and self._device_type == ControllerType.TIGER:
            if self._firmware_version < 3.38:
                timer.on_log_cal()
        elif timer and self._device_type == ControllerType.MS2000:
            if self._firmware_version < 9.2 and self._firmware_version_letter < "j":
                timer.on_log_cal()

    def set_state_dither(self) -> None:
        """Start CRISP dither calibration."""
        self._state = self.STATE_DITHERING

    def set_state_gain_cal(self) -> None:
        """Start CRISP gain calibration."""
        self._state = self.STATE_GAINCAL

    def is_focus_locked(self) -> bool:
        """Check if CRISP is currently focus-locked."""
        return self._state == self.STATE_LOCKED

    def is_tiger(self) -> bool:
        """Check if device is a Tiger controller."""
        return self._device_type == ControllerType.TIGER

    def is_ms2000(self) -> bool:
        """Check if device is a MS2000 controller."""
        return self._device_type == ControllerType.MS2000

    # Getter methods
    def get_device_type(self) -> str:
        """Get the CRISP controller type."""
        return self._device_type

    def get_device_name(self) -> str:
        """Get the device name."""
        return self._device_name

    def get_firmware_version(self) -> float:
        """Get the firmware version number."""
        return self._firmware_version

    def get_firmware_version_letter(self) -> str:
        """Get the firmware version letter."""
        return self._firmware_version_letter

    def get_state_string(self) -> str:
        """Get the current CRISP state as a string."""
        states = {
            self.STATE_IDLE: "Idle",
            self.STATE_LOCKED: "Locked",
            self.STATE_LOGGING: "Logging",
            self.STATE_LOGGINGEXT: "LoggingExt",
            self.STATE_DITHERING: "Dithering",
            self.STATE_GAINCAL: "GainCal",
        }
        return states.get(self._state, "Unknown")

    def get_axis_string(self) -> str:
        """Get the axis string."""
        if self._device_type == ControllerType.TIGER:
            return f"{self._device_type}:{self._device_name}"
        if self._device_type == ControllerType.MS2000:
            return f"{self._device_type}:{self._device_name}:{self.get_axis()}"
        return ""

    def get_axis(self) -> str:
        """Get the axis CRISP is controlling."""
        return self._axis

    def get_error(self) -> float:
        """Get the current focus error."""
        return self._error

    def get_snr(self) -> float:
        """Get the current signal-to-noise ratio."""
        return self._snr

    def get_agc(self) -> float:
        """Get the current automatic gain control value."""
        return self._agc

    def get_sum(self) -> float:
        """Get the current sum value."""
        return self._sum

    def get_offset(self) -> float:
        """Get the current offset value."""
        return self._offset

    # Settings getters - use values from current settings profile
    def get_led_intensity(self) -> int:
        """Get the current LED intensity."""
        return self.get_settings().led_intensity

    def get_objective_na(self) -> float:
        """Get the current objective numerical aperture."""
        return self.get_settings().objective_na

    def get_cal_gain(self) -> int:
        """Get the current calibration gain."""
        return self.get_settings().gain

    def get_loop_gain(self) -> int:
        """Get the loop gain - not in settings, using instance variable."""
        return self._loop_gain

    def get_num_averages(self) -> int:
        """Get the current number of averages."""
        return self.get_settings().num_averages

    def get_update_rate(self) -> int:
        """Get the current update rate."""
        return self.get_settings().update_rate_ms

    def get_lock_range(self) -> float:
        """Get the current lock range."""
        return self.get_settings().lock_range

    # Setter methods - update both settings and device
    def set_led_intensity(self, value: int) -> None:
        """Set the LED intensity."""
        # Update settings
        self.get_settings().led_intensity = value
        # In a real implementation, would call core.setProperty

    def set_objective_na(self, value: float) -> None:
        """Set the objective numerical aperture."""
        # Update settings
        self.get_settings().objective_na = value
        # In a real implementation, would call core.setProperty

    def set_cal_gain(self, value: int) -> None:
        """Set the calibration gain."""
        # Update settings
        self.get_settings().gain = value
        # In a real implementation, would call core.setProperty

    def set_loop_gain(self, value: int) -> None:
        """Set the loop gain - not in settings."""
        # This is not stored in settings
        self._loop_gain = value
        # In a real implementation, would call core.setProperty

    def set_num_averages(self, value: int) -> None:
        """Set the number of averages."""
        # Update settings
        self.get_settings().num_averages = value
        # In a real implementation, would call core.setProperty

    def set_update_rate(self, value: int) -> None:
        """Set the update rate."""
        # Update settings
        self.get_settings().update_rate_ms = value
        # In a real implementation, would call core.setProperty

    def set_lock_range(self, value: float) -> None:
        """Set the lock range."""
        # Update settings
        self.get_settings().lock_range = value
        # In a real implementation, would call core.setProperty
