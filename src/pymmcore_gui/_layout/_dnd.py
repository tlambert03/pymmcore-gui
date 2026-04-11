"""Shared DnD primitives for workbench bars.

This module holds the MIME type used on the drag payload and small
helpers for encoding/decoding it. Both :class:`ActivityBar` and
:class:`NavigationBarAdapter` emit drops carrying the same payload so
cross-container moves work uniformly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymmcore_gui._qt.QtCore import QMimeData

PMM_VIEW_MIME_TYPE = "application/x-pymmcore-view-id"
"""MIME format used when dragging a view between bars.

Payload is the view id as UTF-8 bytes.
"""


def encode_view_id(view_id: str) -> bytes:
    return view_id.encode("utf-8")


def decode_view_id(mime: QMimeData) -> str | None:
    """Return the view id carried by *mime*, or ``None`` if absent."""
    if not mime.hasFormat(PMM_VIEW_MIME_TYPE):
        return None
    raw = bytes(mime.data(PMM_VIEW_MIME_TYPE))
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
