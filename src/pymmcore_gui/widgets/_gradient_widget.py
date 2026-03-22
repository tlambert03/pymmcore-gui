from __future__ import annotations

import math

import numpy as np

from pymmcore_gui._qt.QtGui import QColor, QImage, QPainter, QPaintEvent, QPalette
from pymmcore_gui._qt.QtWidgets import QWidget

# Palette roles used for the gradient endpoints
TOP_ROLE = QPalette.ColorRole.Dark
BOTTOM_ROLE = QPalette.ColorRole.Window


class DitheredGradientWidget(QWidget):
    """Widget that paints a dithered gradient to avoid banding."""

    def __init__(self, angle: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = angle  # degrees, 0 = top-to-bottom
        self._cache: QImage | None = None
        self._cache_key: tuple[int, int, int, int] = (0, 0, 0, 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        w, h = self.width(), self.height()
        if h < 1 or w < 1:
            return

        top = self.palette().color(TOP_ROLE)
        bottom = self.palette().color(BOTTOM_ROLE)
        key = (w, h, top.rgb(), bottom.rgb())
        if self._cache is None or self._cache_key != key:
            self._cache = _build_dithered_image(w, h, top, bottom, self._angle)
            self._cache_key = key

        painter = QPainter(self)
        painter.drawImage(0, 0, self._cache)
        painter.end()

    def changeEvent(self, event: object) -> None:
        self._cache = None
        super().changeEvent(event)  # type: ignore [arg-type]


def _build_dithered_image(
    w: int, h: int, top: QColor, bottom: QColor, angle: float
) -> QImage:
    """Build a dithered gradient image."""
    r0, g0, b0 = top.red(), top.green(), top.blue()
    r1, g1, b1 = bottom.red(), bottom.green(), bottom.blue()

    rad = math.radians(angle)
    dx, dy = math.sin(rad), math.cos(rad)

    y = np.arange(h, dtype=np.float64)
    x = np.arange(w, dtype=np.float64)
    proj = dy * y[:, None] + dx * x[None, :]
    pmin, pmax = proj.min(), proj.max()
    t = (proj - pmin) / (pmax - pmin) if pmax > pmin else np.zeros_like(proj)

    r = r0 + (r1 - r0) * t
    g = g0 + (g1 - g0) * t
    b = b0 + (b1 - b0) * t

    # 4x4 Bayer ordered dithering matrix
    bayer = (
        np.array(
            [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
            dtype=np.float64,
        )
        / 16.0
    )
    offsets = bayer[np.arange(h) % 4][:, np.arange(w) % 4]

    r_out = np.clip(np.floor(r + offsets).astype(np.uint8), 0, 255)
    g_out = np.clip(np.floor(g + offsets).astype(np.uint8), 0, 255)
    b_out = np.clip(np.floor(b + offsets).astype(np.uint8), 0, 255)

    argb = np.empty((h, w, 4), dtype=np.uint8)
    argb[:, :, 0] = b_out
    argb[:, :, 1] = g_out
    argb[:, :, 2] = r_out
    argb[:, :, 3] = 255

    img = QImage(argb.data, w, h, w * 4, QImage.Format.Format_ARGB32)
    return img.copy()
