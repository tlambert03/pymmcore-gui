from pathlib import Path
from typing import Any

import ndv
import useq
from ndv import DataWrapper
from ndv.views._app import ndv_app
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.mda.handlers import TensorStoreHandler
from pymmcore_plus.metadata import SummaryMetaV1
from pymmcore_widgets import MDAWidget

# TODO: manage state of these better
HANDLER: TensorStoreHandler | None = None
VIEWER: ndv.ArrayViewer | None = None


class _MDAWidget(MDAWidget):
    def execute_mda(self, output: Path | str | object | None) -> None:
        global HANDLER
        sequence = self.value()
        HANDLER = TensorStoreHandler(
            path="/Users/talley/Desktop/ndv_test.zarr", delete_existing=True
        )
        self._mmc.run_mda(sequence, output=HANDLER)


app = ndv_app()
app.create_app()

core = CMMCorePlus.instance()
core.loadSystemConfiguration()


@core.mda.events.frameReady.connect
def _on_frame_ready(frame: Any, event: useq.MDAEvent, meta: SummaryMetaV1) -> None:
    # if 1st frame, create a new wrapper
    global VIEWER
    if VIEWER is None:
        if HANDLER is not None:
            VIEWER = ndv.ArrayViewer(DataWrapper.create(HANDLER._store))
            VIEWER.show()
    else:
        dims = {d: i for i, d in enumerate(VIEWER.data_wrapper.dims)}
        VIEWER.display_model.current_index.update(
            {dims[ax]: idx for ax, idx in event.index.items()}
        )


mda = _MDAWidget()
seq = useq.MDASequence(channels=["Cy5", "DAPI"], time_plan={"interval": 1, "loops": 3})
mda.setValue(seq)
mda.show()
app.run()
