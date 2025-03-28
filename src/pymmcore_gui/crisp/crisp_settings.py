#!/usr/bin/env python3
# Project: ASI CRISP Control - CRISP Settings Dataclass
# License: BSD 3-clause

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class CRISPSettings:
    """A dataclass to store software settings for CRISP."""

    name: str
    gain: int = 1
    led_intensity: int = 50
    update_rate_ms: int = 10
    num_averages: int = 1
    objective_na: float = 0.65
    lock_range: float = 1.0

    NAME_PREFIX: ClassVar[str] = "Profile"
    SETTINGS_NOT_FOUND: ClassVar[str] = "No Settings"
    DEFAULT_PROFILE_NAME: ClassVar[str] = "Default"

    def __str__(self) -> str:
        """String representation of the settings."""
        return (
            f'CRISPSettings[name="{self.name}", gain={self.gain}, '
            f"led_intensity={self.led_intensity}, update_rate_ms={self.update_rate_ms}, "
            f"num_averages={self.num_averages}, objective_na={self.objective_na}, "
            f"lock_range={self.lock_range}]"
        )
