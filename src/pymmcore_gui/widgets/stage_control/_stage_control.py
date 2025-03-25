from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING, cast

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import StageWidget
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from ._kinesis_rotation_widget import KinesisRotationWidget

if TYPE_CHECKING:
    from qtpy.QtGui import QWheelEvent


class Stage(StageWidget):
    """Stage control widget with wheel event for z-axis control."""

    def __init__(self, device: str) -> None:
        super().__init__(device=device)

    def wheelEvent(self, event: QWheelEvent) -> None:
        # if self._dtype != DeviceType.Stage:
        #     return
        delta = event.angleDelta().y()
        increment = self._step.value()
        if delta > 0:
            self._move_stage_relative(0, increment)
        elif delta < 0:
            self._move_stage_relative(0, -increment)


class _Group(QGroupBox):
    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(name, parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


class StagesControlWidget(QWidget):
    """UI elements for stage control widgets."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent)

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(5)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._mmc = CMMCorePlus.instance()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self) -> None:
        self._clear()

        sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        stages = chain(
            self._mmc.getLoadedDevicesOfType(DeviceType.XYStage),  # pyright: ignore
            self._mmc.getLoadedDevicesOfType(DeviceType.Stage),  # pyright: ignore
        )

        for idx, stage_dev in enumerate(stages):
            bx = _Group(stage_dev, self)
            bx.setSizePolicy(sizepolicy)
            if stage_dev == "KBD101_28252107":
                cast("QHBoxLayout", bx.layout()).addWidget(
                    KinesisRotationWidget("KBD101_28252107")
                )
            else:
                cast("QHBoxLayout", bx.layout()).addWidget(Stage(device=stage_dev))

            self._layout.addWidget(bx, idx // 2, idx % 2)

        self.resize(self.sizeHint())

    def _clear(self) -> None:
        while self._layout.count():
            if (item := self._layout.takeAt(0)) and (widget := item.widget()):
                widget.setParent(self)
                widget.deleteLater()
