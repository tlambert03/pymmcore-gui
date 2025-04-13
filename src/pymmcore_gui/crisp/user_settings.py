from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from .crisp_settings import CRISPSettings

if TYPE_CHECKING:
    from pymmcore_gui.crisp.crisp_device import CRISP
    from pymmcore_gui.crisp.crisp_timer import CRISPTimer
    from pymmcore_gui.crisp.crisp_widget import CRISPWidget


class UserSettings:
    """Handler for saving and loading user settings."""

    def __init__(self, crisp: CRISP, timer: CRISPTimer, widget: CRISPWidget) -> None:
        self.crisp = crisp
        self.timer = timer
        self.widget = widget

        self.settings_path = os.path.expanduser("~/crisp_settings.json")

    def save(self) -> bool | None:
        """Save current settings to file."""
        try:
            # Get spinner panel
            spinner_panel = self.widget.get_spinner_panel()

            # Create settings profiles array
            settings_list = []
            for setting in self.crisp.get_settings_list():
                settings_list.append(
                    {
                        "name": setting.name,
                        "gain": setting.gain,
                        "led_intensity": setting.led_intensity,
                        "update_rate_ms": setting.update_rate_ms,
                        "num_averages": setting.num_averages,
                        "objective_na": setting.objective_na,
                        "lock_range": setting.lock_range,
                    }
                )

            # Create settings dictionary
            settings_data = {
                "settings_profiles": settings_list,
                "current_settings_index": self.crisp.settings_index,
                "loop_gain": self.crisp.get_loop_gain(),  # Not part of CRISPSettings
                "polling_enabled": spinner_panel.is_polling_enabled(),
                "timer_interval": self.timer.interval,
                # Add window position and size if needed
                "window_geometry": {
                    "x": self.widget.x(),
                    "y": self.widget.y(),
                    "width": self.widget.width(),
                    "height": self.widget.height(),
                },
            }

            # Save to file
            with open(self.settings_path, "w") as f:
                json.dump(settings_data, f, indent=2)

            return True
        except Exception:
            return False

    def load(self) -> bool | None:
        """Load settings from file."""
        if not os.path.exists(self.settings_path):
            # No settings file, use defaults
            return False

        try:
            # Read settings from file
            with open(self.settings_path) as f:
                settings_data = json.load(f)

            # Load settings profiles
            if "settings_profiles" in settings_data:
                # Clear existing settings (except default which is at index 0)
                while len(self.crisp.settings) > 1:
                    self.crisp.settings.pop()

                # Update default profile (index 0)
                if len(settings_data["settings_profiles"]) > 0:
                    default_profile = settings_data["settings_profiles"][0]
                    self.crisp.settings[0].name = default_profile["name"]
                    self.crisp.settings[0].gain = default_profile["gain"]
                    self.crisp.settings[0].led_intensity = default_profile[
                        "led_intensity"
                    ]
                    self.crisp.settings[0].update_rate_ms = default_profile[
                        "update_rate_ms"
                    ]
                    self.crisp.settings[0].num_averages = default_profile[
                        "num_averages"
                    ]
                    self.crisp.settings[0].objective_na = default_profile[
                        "objective_na"
                    ]
                    self.crisp.settings[0].lock_range = default_profile["lock_range"]

                # Add additional profiles
                for profile in settings_data["settings_profiles"][1:]:
                    self.crisp.settings.append(
                        CRISPSettings(
                            name=profile["name"],
                            gain=profile["gain"],
                            led_intensity=profile["led_intensity"],
                            update_rate_ms=profile["update_rate_ms"],
                            num_averages=profile["num_averages"],
                            objective_na=profile["objective_na"],
                            lock_range=profile["lock_range"],
                        )
                    )

            # Set current settings index
            if "current_settings_index" in settings_data:
                index = settings_data["current_settings_index"]
                if 0 <= index < len(self.crisp.settings):
                    self.crisp.set_settings_index(index)

            # Apply loop gain (not part of CRISPSettings)
            if "loop_gain" in settings_data:
                self.crisp.set_loop_gain(settings_data["loop_gain"])

            # Apply timer settings
            if "timer_interval" in settings_data:
                self.timer.set_interval(settings_data["timer_interval"])

            # Get spinner panel to update UI
            spinner_panel = self.widget.get_spinner_panel()

            # Set polling checkbox state
            if "polling_enabled" in settings_data and spinner_panel:
                # Note: this will trigger the checkbox's changed event
                # which will start/stop the timer
                spinner_panel.polling_checkbox.setChecked(
                    settings_data["polling_enabled"]
                )

            # Update profile combo box
            if hasattr(spinner_panel, "update_profile_combo"):
                spinner_panel.update_profile_combo()

            return True
        except Exception:
            return False
