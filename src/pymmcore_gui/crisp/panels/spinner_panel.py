#!/usr/bin/env python3
# Project: ASI CRISP Control - Spinner Panel
# License: BSD 3-clause

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SpinnerPanel(QWidget):
    """A panel for CRISP settings with numeric spinners."""

    def __init__(self, crisp, timer) -> None:
        super().__init__()

        self.crisp = crisp
        self.timer = timer

        # Create layout
        self.axis_label = QLabel("Axis: Z")

        self.led_intensity = QSpinBox()
        self.led_intensity.setMaximum(100)
        self.led_intensity.valueChanged.connect(self.on_led_intensity_changed)

        self.objective_na = QDoubleSpinBox()
        self.objective_na.setMinimum(0.1)
        self.objective_na.setMaximum(1.4)
        self.objective_na.setSingleStep(0.1)
        self.objective_na.valueChanged.connect(self.on_objective_na_changed)

        self.loop_gain = QSpinBox()
        self.loop_gain.setMaximum(100)
        self.loop_gain.valueChanged.connect(self.on_loop_gain_changed)

        self.num_averages = QSpinBox()
        self.num_averages.setMaximum(10)
        self.num_averages.valueChanged.connect(self.on_num_averages_changed)

        self.update_rate = QSpinBox()
        self.update_rate.setMinimum(1)
        self.update_rate.setMaximum(100)

        self.lock_range = QSpinBox()
        self.lock_range.setMaximum(1000)
        self.lock_range.setSingleStep(1)
        # self.lock_range.valueChanged.connect(self.on_lock_range_changed)

        self.poll_rate = QSpinBox()
        self.poll_rate.setMinimum(1)
        self.poll_rate.setMaximum(1000)
        self.poll_rate.setValue(200)

        self.polling_checkbox = QCheckBox("Enable Polling")

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(form.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        form.addRow("LED Intensity [%]", self.led_intensity)
        form.addRow("Objective NA", self.objective_na)
        form.addRow("Loop Gain", self.loop_gain)
        form.addRow("Averaging", self.num_averages)
        form.addRow("Update Rate [ms]", self.update_rate)
        form.addRow("Lock Range [mm]", self.lock_range)
        form.addRow("Polling Rate [ms]", self.poll_rate)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.polling_checkbox)

        # Create spinners and labels
        # self.create_spinners()

        # Create profile controls
        # self.create_profile_controls()

    def create_profile_controls(self) -> None:
        """Create profile selection and management controls."""
        # Get current row
        row = self._layout.rowCount()

        # Profile label
        profile_label = QLabel("Profile:")
        profile_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._layout.addWidget(profile_label, row, 0)

        # Profile combo box
        self.profile_combo = QComboBox()
        self._layout.addWidget(self.profile_combo, row, 1, 1, 2)
        row += 1

        # Profile buttons container
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        # Add profile button
        self.add_profile_btn = QPushButton("Add")
        btn_layout.addWidget(self.add_profile_btn)

        # Remove profile button
        self.remove_profile_btn = QPushButton("Remove")
        self.remove_profile_btn.setEnabled(
            False,
        )  # Disable initially (can't remove Default)
        btn_layout.addWidget(self.remove_profile_btn)

        self._layout.addWidget(btn_container, row, 0, 1, 3)

        self.profile_combo.currentIndexChanged.connect(self.on_profile_selected)
        self.add_profile_btn.clicked.connect(self.on_add_profile)
        self.remove_profile_btn.clicked.connect(self.on_remove_profile)
        self.update_profile_combo()  # Add initial profiles from CRISP

    def _update(self) -> None:
        """Update spinner values from CRISP."""
        # Update all spinner values from device
        self.led_intensity.setValue(self.crisp.get_led_intensity())
        self.objective_na.setValue(self.crisp.get_objective_na())
        # self.cal_gain_spinner.setValue(self.crisp.get_cal_gain())
        self.loop_gain.setValue(self.crisp.get_loop_gain())
        self.num_averages.setValue(self.crisp.get_num_averages())
        self.update_rate.setValue(self.crisp.get_update_rate())

    def update_profile_combo(self) -> None:
        """Update profile combo box with current profiles from CRISP."""
        # Save current selection if any
        current_index = self.profile_combo.currentIndex()
        current_index = max(current_index, 0)

        # Clear the combo box
        self.profile_combo.clear()

        # Add all profiles from CRISP
        for profile in self.crisp.get_settings_list():
            self.profile_combo.addItem(profile.name)

        # Set selection to current settings index, or restore previous selection
        index_to_set = self.crisp.settings_index
        if 0 <= index_to_set < self.profile_combo.count():
            self.profile_combo.setCurrentIndex(index_to_set)
        elif 0 <= current_index < self.profile_combo.count():
            self.profile_combo.setCurrentIndex(current_index)

        # Update remove button state
        self.remove_profile_btn.setEnabled(self.profile_combo.currentIndex() > 0)

    def set_axis_label_text(self, axis) -> None:
        """Set the axis label text."""
        self.axis_label.setText(f"Axis: {axis}")

    def is_polling_enabled(self):
        """Check if polling is enabled."""
        return self.polling_checkbox.isChecked()

    def set_enabled_focus_lock_spinners(self, enabled) -> None:
        """Enable/disable spinners that can't be changed during focus lock."""
        self.led_intensity_spinner.setEnabled(enabled)
        self.cal_gain_spinner.setEnabled(enabled)

    def set_enabled_update_rate_spinner(self, enabled) -> None:
        """Enable/disable update rate spinner (for firmware compatibility)."""
        self.update_rate.setEnabled(enabled)

    # Event handlers
    def on_led_intensity_changed(self, value) -> None:
        """Handle LED intensity change."""
        self.crisp.set_led_intensity(value)

    def on_objective_na_changed(self, value) -> None:
        """Handle objective NA change."""
        self.crisp.set_objective_na(value)

    def on_cal_gain_changed(self, value) -> None:
        """Handle calibration gain change."""
        self.crisp.set_cal_gain(value)

    def on_loop_gain_changed(self, value) -> None:
        """Handle loop gain change."""
        self.crisp.set_loop_gain(value)

    def on_num_averages_changed(self, value) -> None:
        """Handle number of averages change."""
        self.crisp.set_num_averages(value)

    def on_update_rate_changed(self, value) -> None:
        """Handle update rate change."""
        self.crisp.set_update_rate(value)

    def on_polling_changed(self, state) -> None:
        """Handle polling checkbox change."""
        if state:
            self.timer.start()
        else:
            self.timer.stop()

    def on_profile_selected(self, index) -> None:
        """Handle profile selection change."""
        # Enable/disable remove button (can't remove Default profile)
        self.remove_profile_btn.setEnabled(index > 0)

        # Set the active settings profile in CRISP
        if 0 <= index < self.crisp.get_num_settings():
            self.crisp.set_settings_index(index)
            # Update spinners with values from selected profile
            self._update()

    def on_add_profile(self) -> None:
        """Handle add profile button click."""
        # Get profile name from user
        name, ok = QInputDialog.getText(
            self,
            "New Profile",
            "Enter profile name:",
            text=self.crisp.add_settings(),
        )

        if ok and name:
            # Set the name in the newly created profile
            last_index = self.crisp.get_num_settings() - 1
            self.crisp.get_settings_by_index(last_index).name = name

            # Update the profile combo and select the new profile
            self.update_profile_combo()
            self.profile_combo.setCurrentIndex(last_index)

    def on_remove_profile(self) -> None:
        """Handle remove profile button click."""
        # Get selected profile
        profile_name = self.profile_combo.currentText()
        current_index = self.profile_combo.currentIndex()

        # Don't allow removing Default profile
        if current_index <= 0:
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove the profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Remove the profile from CRISP
            self.crisp.settings.pop(current_index)

            # Update the combo box
            self.update_profile_combo()

            # Set selection to default profile
            self.profile_combo.setCurrentIndex(0)
            self.crisp.set_settings_index(0)
