import re
from pathlib import Path
from typing import cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import MDAWidget
from qtpy.QtWidgets import QBoxLayout, QWidget

from ._save_widget import SaveGroupBox

NUM_SPLIT = re.compile(r"(.*?)(?:_(\d{3,}))?$")


def get_next_available_path(requested_path: Path | str, min_digits: int = 3) -> Path:
    """Get the next available paths (filepath or folderpath if extension = "").

    This method adds a counter of min_digits to the filename or foldername to ensure
    that the path is unique.

    Parameters
    ----------
    requested_path : Path | str
        A path to a file or folder that may or may not exist.
    min_digits : int, optional
        The min_digits number of digits to be used for the counter. By default, 3.
    """
    if isinstance(requested_path, str):  # pragma: no cover
        requested_path = Path(requested_path)
    directory = requested_path.parent
    extension = requested_path.suffix
    # ome files like .ome.tiff or .ome.zarr are special,treated as a single extension
    if (stem := requested_path.stem).endswith(".ome"):
        extension = f".ome{extension}"
        stem = stem[:-4]
    # NOTE: added in micromanager_gui ---------------------------------------------
    elif (stem := requested_path.stem).endswith(".tensorstore"):
        extension = f".tensorstore{extension}"
        stem = stem[:-12]
    # -----------------------------------------------------------------------------

    # look for ANY existing files in the folder that follow the pattern of
    # stem_###.extension
    current_max = 0
    for existing in directory.glob(f"*{extension}"):
        # cannot use existing.stem because of the ome (2-part-extension) special case
        base = existing.name.replace(extension, "")
        # if base name ends with a number and stem is the same, increase current_max
        if (
            (match := NUM_SPLIT.match(base))
            and (num := match.group(2))
            # NOTE: added in micromanager_gui -------------------------------------
            # this breaks pymmcore_widgets test_get_next_available_paths_special_cases
            and match.group(1) == stem
            # ---------------------------------------------------------------------
        ):
            current_max = max(int(num), current_max)
            # if it has more digits than expected, update the ndigits
            if len(num) > min_digits:
                min_digits = len(num)
    # if the path does not exist and there are no existing files,
    # return the requested path
    if not requested_path.exists() and current_max == 0:
        return requested_path

    current_max += 1
    # otherwise return the next path greater than the current_max
    # remove any existing counter from the stem
    if match := NUM_SPLIT.match(stem):
        stem, num = match.groups()
        if num:
            # if the requested path has a counter that is greater than any other files
            # use it
            current_max = max(int(num), current_max)
    return directory / f"{stem}_{current_max:0{min_digits}d}{extension}"


class MDAWidget_(MDAWidget):
    """Multi-dimensional acquisition widget."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(parent=parent, mmcore=mmcore)

        # remove the existing save_info widget from the layout and replace it with
        # the custom SaveGroupBox widget that also handles tensorstore-zarr
        main_layout = cast("QBoxLayout", self.layout())
        if hasattr(self, "save_info"):
            self.save_info.valueChanged.disconnect(self.valueChanged)
            main_layout.removeWidget(self.save_info)
            self.save_info.deleteLater()
        self.save_info: SaveGroupBox = SaveGroupBox(parent=self)
        self.save_info.valueChanged.connect(self.valueChanged)
        main_layout.insertWidget(0, self.save_info)

    def get_next_available_path(self, requested_path: Path) -> Path:
        """Get the next available path.

        Overwrites the method in the parent class to use the custom
        'get_next_available_path' function.
        """
        return get_next_available_path(requested_path=requested_path)
