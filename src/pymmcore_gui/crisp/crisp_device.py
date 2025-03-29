#!/usr/bin/env python3
# Project: ASI CRISP Control - CRISP Device Interface
# License: BSD 3-clause

from contextlib import suppress

from pymmcore_plus import CMMCorePlus, DeviceType

from .crisp_settings import CRISPSettings


class ControllerType:
    """Controller type constants."""

    NONE = "NONE"
    TIGER = "TIGER"
    MS2000 = "MS2000"


class PropName:
    """Property names that correspond to those in the Micro-Manager device adapter."""

    CRISP_STATE = "CRISP State"
    DESCRIPTION = "Description"
    AXIS_LETTER = "AxisLetter"
    SUM = "Sum"
    SNR = "Signal Noise Ratio"
    GAIN = "GainMultiplier"
    LOG_AMP_AGC = "LogAmpAGC"
    LED_INTENSITY = "LED Intensity"
    OBJECTIVE_NA = "Objective NA"
    NUMBER_OF_SKIPS = "Number of Skips"
    NUMBER_OF_AVERAGES = "Number of Averages"
    MAX_LOCK_RANGE = "Max Lock Range(mm)"
    DITHER_ERROR = "Dither Error"
    SAVE_TO_CONTROLLER = "Save to Controller"
    REFRESH_PROP_VALUES = "RefreshPropertyValues"

    class MS2000:
        """Property names only on MS2000."""

        OBTAIN_FOCUS_CURVE = "Obtain Focus Curve"
        FOCUS_CURVE_DATA_PREFIX = "Focus Curve Data"


class PropValue:
    """Property values that correspond to those in the Micro-Manager device adapter."""

    NO = "No"
    YES = "Yes"
    STATE_IDLE = "Idle"
    STATE_LOG_CAL = "loG_cal"
    STATE_DITHER = "Dither"
    STATE_GAIN_CAL = "gain_Cal"
    RESET_FOCUS_OFFSET = "Reset Focus Offset"
    SAVE_TO_CONTROLLER = "Save to Controller"

    class MS2000:
        """Property values only on MS2000."""

        DO_IT = "Do it"


class DeviceLibrary:
    """Device library names for CRISP."""

    TIGER = "ASITiger"
    MS2000 = "ASIStage"


class Description:
    """Device descriptions for CRISP."""

    TIGER = "ASI CRISP AutoFocus"
    MS2000 = "ASI CRISP Autofocus adapter"


class CRISP:
    """Interface to the ASI CRISP autofocus device.
    This communicates with the actual hardware through CMMCorePlus.
    """

    # CRISP state constants
    STATE_IDLE = 0
    STATE_LOCKED = 1
    STATE_LOGGING = 2
    STATE_LOGGINGEXT = 3
    STATE_DITHERING = 4
    STATE_GAINCAL = 5

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
        self.settings: list[CRISPSettings] = [CRISPSettings()]
        self.settings_index = 0

    def __str__(self) -> str:
        """String representation of the device."""
        return f"CRISP[deviceName={self._device_name}, deviceType={self._device_type}]"

    def get_settings_list(self) -> list[CRISPSettings]:
        """Get the list of settings profiles."""
        return self.settings

    def get_settings(self) -> CRISPSettings:
        """Get the current settings profile."""
        return self.settings[self.settings_index]

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

    def _get_device_library(self, device_name: str) -> str:
        """Get the device library for a given device name.

        Args:
            device_name: The name of the device

        Returns
        -------
            The device library name
        """
        try:
            return self.core.getDeviceLibrary(device_name)
        except Exception:
            return ""

    def _get_description(self, device_name: str) -> str:
        """Get the description for a given device name.

        Args:
            device_name: The name of the device

        Returns
        -------
            The device description
        """
        try:
            return self.core.getProperty(device_name, PropName.DESCRIPTION)
        except Exception:
            return ""

    def detect_device(self) -> bool:
        """Attempt to detect the CRISP device.
        Searches for the device among loaded AutoFocus devices.

        Returns
        -------
            True if a CRISP device was found
        """
        with suppress(Exception):
            for device in self.core.iterDevices(
                device_type=DeviceType.AutoFocus,
                device_adapter=DeviceLibrary.TIGER,
            ):
                description = device.description()
                print(device, f"{description=}")
                print("found tiger")
                self._device_name = device.name()
                self._device_type = ControllerType.TIGER
                self._firmware_version = float(
                    self.core.getProperty(self._device_name, "FirmwareVersion")
                )

                return True

        return False

    def reset(self) -> None:
        """Reset the CRISP device."""
        self.set_state_idle()
        self.reset_offset()

    def reset_offset(self) -> None:
        """Reset the CRISP offset value."""
        try:
            self.core.setProperty(
                self._device_name, PropName.CRISP_STATE, PropValue.RESET_FOCUS_OFFSET
            )
        except Exception as e:
            print(e)

    # State control methods
    def set_state_idle(self) -> None:
        """Set CRISP to idle mode."""
        try:
            self.core.setProperty(
                self._device_name, PropName.CRISP_STATE, PropValue.STATE_IDLE
            )
        except Exception as e:
            print(e)

    def set_state_lock(self) -> None:
        """Set CRISP to locked mode."""
        try:
            self.core.enableContinuousFocus(True)
        except Exception as e:
            print(e)

    def set_state_log_cal(self, timer=None) -> None:
        """Start CRISP log calibration."""
        # Handle firmware-specific timer behavior
        if timer and self._device_type == ControllerType.TIGER:
            if self._firmware_version < 3.38:
                timer.on_log_cal()
        print(
            "setting CRISP state to log cal",
            self._device_name,
            PropName.CRISP_STATE,
            PropValue.STATE_LOG_CAL,
        )
        self.core.setProperty(
            self._device_name, PropName.CRISP_STATE, PropValue.STATE_LOG_CAL
        )

    def set_state_dither(self) -> None:
        """Start CRISP dither calibration."""
        self.core.setProperty(
            self._device_name, PropName.CRISP_STATE, PropValue.STATE_DITHER
        )

    def set_state_gain_cal(self) -> None:
        """Start CRISP gain calibration."""
        self.core.setProperty(
            self._device_name, PropName.CRISP_STATE, PropValue.STATE_GAIN_CAL
        )

    def is_focus_locked(self) -> bool:
        """Check if CRISP is currently focus-locked."""
        return self.get_state() == "In Focus"

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

    def get_state(self) -> str:
        """Get the current CRISP state as a string."""
        if not self._device_name:
            return "No Device"
        try:
            return self.core.getProperty(self._device_name, PropName.CRISP_STATE)
        except Exception as e:
            return str(e)[:100]

    def get_axis_string(self) -> str:
        """Get the axis string."""
        if self._device_type == ControllerType.TIGER:
            return f"{self._device_type}:{self._device_name}"
        if self._device_type == ControllerType.MS2000:
            return f"{self._device_type}:{self._device_name}:{self.get_axis()}"
        return ""

    def get_axis(self) -> str:
        """Get the axis CRISP is controlling."""
        try:
            return self.core.getProperty(self._device_name, PropName.AXIS_LETTER)
        except Exception:
            return ""

    def get_error(self) -> float:
        """Get the current focus error."""
        try:
            return float(
                self.core.getProperty(self._device_name, PropName.DITHER_ERROR)
            )
        except Exception:
            return 0.0

    def get_snr(self) -> float:
        """Get the current signal-to-noise ratio."""
        try:
            return float(self.core.getProperty(self._device_name, PropName.SNR))
        except Exception:
            return 0.0

    def get_agc(self) -> float:
        """Get the current automatic gain control value."""
        try:
            return float(self.core.getProperty(self._device_name, PropName.LOG_AMP_AGC))
        except Exception:
            return 0.0

    def get_sum(self) -> float:
        """Get the current sum value."""
        try:
            return float(self.core.getProperty(self._device_name, PropName.SUM))
        except Exception:
            return 0.0

    def get_offset(self) -> float:
        """Get the current offset value."""
        try:
            return self.core.getAutoFocusOffset()
        except Exception:
            return 0.0

    def get_offset_string(self) -> str:
        """Get the current offset value as a string."""
        try:
            return str(self.core.getAutoFocusOffset())
        except Exception:
            return "0.0"

    # Settings getters - use actual device values
    def get_led_intensity(self) -> int:
        """Get the current LED intensity."""
        try:
            return int(self.core.getProperty(self._device_name, PropName.LED_INTENSITY))
        except Exception:
            return 0

    def get_objective_na(self) -> float:
        """Get the current objective numerical aperture."""
        try:
            return float(
                self.core.getProperty(self._device_name, PropName.OBJECTIVE_NA)
            )
        except Exception:
            return 0.0

    def get_cal_gain(self) -> int:
        """Get the current calibration gain."""
        try:
            return int(self.core.getProperty(self._device_name, PropName.GAIN))
        except Exception:
            return 0

    def get_loop_gain(self) -> int:
        """Get the loop gain."""
        # Note: This property is not directly exposed in the Java implementation
        # Keeping it here for API compatibility
        return 0

    def get_num_averages(self) -> int:
        """Get the current number of averages."""
        try:
            return int(
                self.core.getProperty(self._device_name, PropName.NUMBER_OF_AVERAGES)
            )
        except Exception:
            return 0

    def get_update_rate(self) -> int:
        """Get the current update rate."""
        try:
            return int(
                self.core.getProperty(self._device_name, PropName.NUMBER_OF_SKIPS)
            )
        except Exception:
            return 0

    def get_lock_range(self) -> float:
        """Get the current lock range."""
        try:
            return float(
                self.core.getProperty(self._device_name, PropName.MAX_LOCK_RANGE)
            )
        except Exception:
            return 0.0

    # Setter methods - update device properties
    def set_led_intensity(self, value: int) -> None:
        """Set the LED intensity."""
        self.core.setProperty(self._device_name, PropName.LED_INTENSITY, value)

    def set_objective_na(self, value: float) -> None:
        """Set the objective numerical aperture."""
        self.core.setProperty(self._device_name, PropName.OBJECTIVE_NA, value)

    def set_cal_gain(self, value: int) -> None:
        """Set the calibration gain."""
        self.core.setProperty(self._device_name, PropName.GAIN, value)

    def set_loop_gain(self, value: int) -> None:
        """Set the loop gain."""
        # This property is not directly exposed in the Java implementation
        # Keeping it here for API compatibility
        pass

    def set_num_averages(self, value: int) -> None:
        """Set the number of averages."""
        self.core.setProperty(self._device_name, PropName.NUMBER_OF_AVERAGES, value)

    def set_update_rate(self, value: int) -> None:
        """Set the update rate."""
        self.core.setProperty(self._device_name, PropName.NUMBER_OF_SKIPS, value)

    def set_lock_range(self, value: float) -> None:
        """Set the lock range."""
        self.core.setProperty(self._device_name, PropName.MAX_LOCK_RANGE, value)

    def lock(self) -> None:
        """Lock the CRISP (enable continuous focus)."""
        try:
            self.core.enableContinuousFocus(True)
        except Exception as e:
            print(e)

    def unlock(self) -> None:
        """Unlock the CRISP (disable continuous focus)."""
        try:
            self.core.enableContinuousFocus(False)
        except Exception as e:
            print(e)

    def save(self) -> None:
        """Save current settings to the device firmware."""
        try:
            self.core.setProperty(
                self._device_name, PropName.CRISP_STATE, PropValue.SAVE_TO_CONTROLLER
            )
        except Exception as e:
            print(e)

    def get_focus_curve(self) -> None:
        """Get focus curve data (only for MS2000)."""
        try:
            if self.is_ms2000():
                self.core.setProperty(
                    self._device_name,
                    PropName.MS2000.OBTAIN_FOCUS_CURVE,
                    PropValue.MS2000.DO_IT,
                )
        except Exception as e:
            print(e)

    def get_focus_curve_data(self, n: int) -> str:
        """Get part of the focus curve data (only for MS2000)."""
        try:
            if self.is_ms2000():
                return self.core.getProperty(
                    self._device_name, f"{PropName.MS2000.FOCUS_CURVE_DATA_PREFIX}{n}"
                )
        except Exception as e:
            print(e)
        return ""

    def get_all_focus_curve_data(self) -> str:
        """Get all focus curve data (only for MS2000)."""
        result = []
        for i in range(self.FC_DATA_SIZE):
            data = self.get_focus_curve_data(i)
            if data:
                result.append(data)
        return "".join(result)

    def set_refresh_property_values(self, state: bool) -> None:
        """Set whether to refresh property values (only for Tiger)."""
        try:
            if self.is_tiger():
                self.core.setProperty(
                    self._device_name,
                    PropName.REFRESH_PROP_VALUES,
                    PropValue.YES if state else PropValue.NO,
                )
        except Exception as e:
            print(e)

    # Tiger-specific serial commands
    def set_only_send_serial_command_on_change(self, state: bool) -> None:
        """Set whether to only send serial commands on change (only for Tiger)."""
        try:
            if self.is_tiger():
                self.core.setProperty(
                    "TigerCommHub",
                    "OnlySendSerialCommandOnChange",
                    "Yes" if state else "No",
                )
        except Exception as e:
            print(e)

    def send_serial_command(self, command: str) -> None:
        """Send a serial command (only for Tiger)."""
        try:
            if self.is_tiger():
                self.core.setProperty("TigerCommHub", "SerialCommand", command)
        except Exception as e:
            print(e)

    def get_serial_response(self) -> str:
        """Get the serial response (only for Tiger)."""
        try:
            if self.is_tiger():
                return self.core.getProperty("TigerCommHub", "SerialResponse")
        except Exception as e:
            print(e)
        return ""
