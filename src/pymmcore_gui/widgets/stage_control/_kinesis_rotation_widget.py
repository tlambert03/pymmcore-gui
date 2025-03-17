# to use with thorlabs kinesis rotation stage
# https://github.com/micro-manager/mmdev-ThorlabsKinesis

from __future__ import annotations

from typing import cast

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy import QtCore
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QDial,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

AlignCenter = Qt.AlignmentFlag.AlignCenter
STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}
STYLE = """
QPushButton {
    border: none;
    background: transparent;
    color: rgb(0, 180, 0);
    font-size: 40px;
}
QPushButton:hover:!pressed {
    color: rgb(0, 255, 0);
}
QPushButton:pressed {
    color: rgb(0, 100, 0);
}
QSpinBox {
    min-width: 35px;
    height: 22px;
}
QLabel {
    color: #999;
}
QCheckBox {
    color: #999;
}
QCheckBox::indicator {
    width: 11px;
    height: 11px;
}
"""


class _DialWidget(QWidget):
    valueChanged = Signal(int)

    def __init__(self, DeviceUnitsPerRevolution: float, parent: QWidget | None = None):
        super().__init__(parent)

        self._one_deg_unit = DeviceUnitsPerRevolution / 360

        layout = QGridLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.setLayout(layout)

        _top_label = self._create_label("180")
        _bottom_label = self._create_label("0")
        _left_label = self._create_label("90")
        _right_label = self._create_label("270")

        self.dial = QDial(self)
        self.dial.setWrapping(True)
        self.dial.setMinimumSize(130, 130)
        self.dial.setMinimum(0)
        self.dial.setMaximum(360)
        self.dial.setNotchesVisible(True)
        self.dial.setNotchTarget(23)
        self.dial.valueChanged.connect(self._on_dial_value_changed)

        layout.addWidget(_top_label, 0, 1)
        layout.addWidget(_left_label, 1, 0)
        layout.addWidget(self.dial, 1, 1)
        layout.addWidget(_right_label, 1, 2)
        layout.addWidget(_bottom_label, 2, 1)

        self.setFixedSize(self.sizeHint())

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return label

    def _on_dial_value_changed(self, value: int) -> None:
        self.valueChanged.emit(value)

    def setValue(self, value: int) -> int:
        return cast(int, self.dial.value())


class KinesisRotationWidget(QWidget):
    """A Widget to control Thorlabs Kinesis rotation stage.

    Parameters
    ----------
    device: str:
        Stage device.
    levels: int | None:
        Number of "arrow" buttons per widget per direction, by default, 2.
    parent : QWidget | None
        Optional parent widget.
    mmcore : CMMCorePlus | None
        Optional [`pymmcore_plus.CMMCorePlus`][] micromanager core.
        By default, None. If not specified, the widget will use the active
        (or create a new)
        [`CMMCorePlus.instance`][pymmcore_plus.core._mmcore_plus.CMMCorePlus.instance].
    """

    def __init__(
        self,
        device: str,
        levels: int | None = 2,
        *,
        parent: QWidget | None = None,
        mmcore: CMMCorePlus | None = None,
    ):
        super().__init__(parent=parent)

        self.setStyleSheet(STYLE)

        self._mmc = mmcore or CMMCorePlus.instance()
        self._levels = levels
        self._device = device
        self._dtype = self._mmc.getDeviceType(self._device)
        assert self._dtype in STAGE_DEVICES, f"{self._dtype} not in {STAGE_DEVICES}"

        self._create_widget()

        self._connect_events()

        self._set_as_default()

        self.destroyed.connect(self._disconnect)

    def _create_widget(self) -> None:
        self._step = QDoubleSpinBox()
        self._step.setValue(10)
        self._step.setMaximum(9999)
        self._step.clearFocus()
        self._step.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, 0)
        self._step.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._step.setAlignment(AlignCenter)

        self._btns = QWidget()
        self._btns.setLayout(QGridLayout())
        self._btns.layout().setContentsMargins(0, 0, 0, 0)
        self._btns.layout().setSpacing(0)

        self._dial = _DialWidget(
            float(self._mmc.getProperty(self._device, "DeviceUnitsPerRevolution"))
        )
        self._dial.valueChanged.connect(self._update_position_label)
        self._dial.valueChanged.connect(self._on_value_changed)
        self._btns.layout().addWidget(self._dial, 0, 0, AlignCenter)

        self._readout = QLabel()
        self._readout.setAlignment(AlignCenter)
        self._update_position_label()

        self._poll_cb = QCheckBox("poll")
        self._poll_cb.setMaximumWidth(50)
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._update_position_label)
        self._poll_cb.toggled.connect(self._toggle_poll_timer)

        self.snap_checkbox = QCheckBox(text="Snap on Click")

        self.radiobutton = QRadioButton(text="Set as Default")
        self.radiobutton.toggled.connect(self._on_radiobutton_toggled)

        top_row = QWidget()
        top_row_layout = QHBoxLayout()
        top_row_layout.setAlignment(AlignCenter)
        top_row.setLayout(top_row_layout)
        top_row.layout().addWidget(self.radiobutton)

        bottom_row_1 = QWidget()
        bottom_row_1.setLayout(QHBoxLayout())
        bottom_row_1.layout().addWidget(self._readout)

        bottom_row_2 = QWidget()
        bottom_row_2_layout = QHBoxLayout()
        bottom_row_2_layout.setSpacing(10)
        bottom_row_2_layout.setContentsMargins(0, 0, 0, 0)
        bottom_row_2_layout.setAlignment(AlignCenter)
        bottom_row_2.setLayout(bottom_row_2_layout)
        bottom_row_2.layout().addWidget(self.snap_checkbox)
        bottom_row_2.layout().addWidget(self._poll_cb)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().addWidget(top_row)
        self.layout().addWidget(self._btns, AlignCenter)
        self.layout().addWidget(bottom_row_1)
        self.layout().addWidget(bottom_row_2)

        with signals_blocked(self._dial):
            self._dial.setValue(round(self._mmc.getPosition(self._device)))

    def _connect_events(self) -> None:
        self._mmc.events.propertyChanged.connect(self._on_prop_changed)
        self._mmc.events.systemConfigurationLoaded.connect(self._on_system_cfg)
        if self._dtype is DeviceType.XYStage:
            event = self._mmc.events.XYStagePositionChanged
        elif self._dtype is DeviceType.Stage:
            event = self._mmc.events.stagePositionChanged
        event.connect(self._update_position_label)

    def _enable_wdg(self, enabled: bool) -> None:
        self._step.setEnabled(enabled)
        self._btns.setEnabled(enabled)
        self.snap_checkbox.setEnabled(enabled)
        self.radiobutton.setEnabled(enabled)
        self._poll_cb.setEnabled(enabled)

    def _on_system_cfg(self) -> None:
        if self._dtype is DeviceType.XYStage:
            if self._device not in self._mmc.getLoadedDevicesOfType(DeviceType.XYStage):
                self._enable_and_update(False)
            else:
                self._enable_and_update(True)

        if self._dtype is DeviceType.Stage:
            if self._device not in self._mmc.getLoadedDevicesOfType(DeviceType.Stage):
                self._enable_and_update(False)
            else:
                self._enable_and_update(True)

        self._set_as_default()

    def _enable_and_update(self, enable: bool) -> None:
        if enable:
            self._enable_wdg(True)
            self._update_position_label()
            with signals_blocked(self._dial):
                self._dial.setValue(round(self._mmc.getPosition(self._device)))
        else:
            self._readout.setText(f"{self._device} not loaded.")
            self._enable_wdg(False)

    def _set_as_default(self) -> None:
        current_xy = self._mmc.getXYStageDevice()
        current_z = self._mmc.getFocusDevice()
        if self._dtype is DeviceType.XYStage and current_xy == self._device:
            self.radiobutton.setChecked(True)
        elif self._dtype is DeviceType.Stage and current_z == self._device:
            self.radiobutton.setChecked(True)

    def _on_radiobutton_toggled(self, state: bool) -> None:
        if self._dtype is DeviceType.XYStage:
            if state:
                self._mmc.setProperty("Core", "XYStage", self._device)
            elif (
                not state
                and len(self._mmc.getLoadedDevicesOfType(DeviceType.XYStage)) == 1
            ):
                with signals_blocked(self.radiobutton):
                    self.radiobutton.setChecked(True)
            else:
                self._mmc.setProperty("Core", "XYStage", "")

        elif self._dtype is DeviceType.Stage:
            if state:
                self._mmc.setProperty("Core", "Focus", self._device)
            elif (
                not state
                and len(self._mmc.getLoadedDevicesOfType(DeviceType.Stage)) == 1
            ):
                with signals_blocked(self.radiobutton):
                    self.radiobutton.setChecked(True)
            else:
                self._mmc.setProperty("Core", "Focus", "")

    def _on_prop_changed(self, dev: str, prop: str, val: str) -> None:
        if dev != "Core":
            return

        if self._dtype is DeviceType.XYStage and prop == "XYStage":
            with signals_blocked(self.radiobutton):
                self.radiobutton.setChecked(val == self._device)

        if self._dtype is DeviceType.Stage and prop == "Focus":
            with signals_blocked(self.radiobutton):
                self.radiobutton.setChecked(val == self._device)

    def _toggle_poll_timer(self, on: bool) -> None:
        self._poll_timer.start() if on else self._poll_timer.stop()

    def _update_position_label(self) -> None:
        if (
            self._dtype is DeviceType.Stage
            and self._device in self._mmc.getLoadedDevicesOfType(DeviceType.Stage)
        ):
            p = str(round(self._mmc.getPosition(self._device), 2))
            # / self._dial._one_deg_unit)
            self._readout.setText(f"{self._device}:  {p}")

    def _on_value_changed(self, angle: int) -> None:
        # print("angle:", angle)
        self._readout.setText(f"{self._device}:  {angle}")
        self._move_stage(angle)

    def _move_stage(self, a: int) -> None:
        self._mmc.setPosition(self._device, float(a))
        if self.snap_checkbox.isChecked():
            self._mmc.snap()
        # print('getPosition:', self._mmc.getPosition(self._device))

    def _disconnect(self) -> None:
        self._mmc.events.propertyChanged.disconnect(self._on_prop_changed)
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_system_cfg)
        if self._dtype is DeviceType.XYStage:
            event = self._mmc.events.XYStagePositionChanged
        elif self._dtype is DeviceType.Stage:
            event = self._mmc.events.stagePositionChanged
        event.disconnect(self._update_position_label)
