from __future__ import annotations

from pathlib import Path

from pymmcore_plus.mda.handlers import (
    ImageSequenceWriter,
    OMETiffWriter,
    OMEZarrWriter,
    TensorStoreHandler,
)

from .tesnrostore_writer import _TensorStoreHandler as TensorStoreHandlerDisk

__all__ = [
    "ImageSequenceWriter",
    "OMETiffWriter",
    "OMEZarrWriter",
    "TensorStoreHandler",
    "handler_for_path",
]


def handler_for_path(path: str | Path) -> object:
    """Convert a string or Path into a handler object.

    This method picks from the built-in handlers based on the extension of the path.
    """
    if str(path).rstrip("/").rstrip(":").lower() == "memory":
        return TensorStoreHandler(kvstore="memory://")

    path = str(Path(path).expanduser().resolve())

    if path.endswith("tensorstore.zarr"):
        return TensorStoreHandlerDisk(path=path)

    if path.endswith(".zarr"):
        return OMEZarrWriter(path)

    if path.endswith((".tiff", ".tif")):
        return OMETiffWriter(path)

    # FIXME: ugly hack for the moment to represent a non-existent directory
    # there are many features that ImageSequenceWriter supports, and it's unclear
    # how to infer them all from a single string.
    if not (Path(path).suffix or Path(path).exists()):
        return ImageSequenceWriter(path)

    raise ValueError(f"Could not infer a writer handler for path: '{path}'")
