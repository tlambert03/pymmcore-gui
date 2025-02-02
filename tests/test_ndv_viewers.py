from __future__ import annotations

import datetime
import gc
import os
from typing import TYPE_CHECKING

import pytest
import useq
from PyQt6.QtWidgets import QApplication, QWidget
from useq import MDASequence

from pymmcore_gui._main_window import _ViewersManager

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus
    from pytestqt.qtbot import QtBot


@pytest.mark.skipif(bool(os.getenv("CI")), reason="Segfaults on CI")
def test_viewers_manager(mmcore: CMMCorePlus, qtbot: QtBot) -> None:
    """Ensure that the viewers manager creates and cleans up viewers during MDA."""
    dummy = QWidget()
    manager = _ViewersManager(dummy, mmcore)

    assert len(manager) == 0
    mmcore.mda.run(
        MDASequence(
            time_plan=useq.TIntervalLoops(
                interval=datetime.timedelta(seconds=0.1), loops=2
            ),
            channels=["DAPI", "FITC"],  # pyright: ignore
            z_plan=useq.ZRangeAround(range=4, step=1),
        )
    )
    assert len(manager) == 1

    with qtbot.waitSignal(dummy.destroyed, timeout=1000):
        dummy.deleteLater()
    gc.collect()
    QApplication.processEvents()
    qtbot.waitUntil(lambda: len(manager) == 0, timeout=1000)
