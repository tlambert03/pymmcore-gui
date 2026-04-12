# ruff: noqa: D101, D102, D103
"""Profile widget paint performance.

Monkey-patches paintEvent on target widgets to measure rendering times,
detect excessive repaints, and identify the costliest paint operations.

Usage:
    uv run python -m scripts.paint_profiler

    # Or attach to specific widgets programmatically:
    from scripts.paint_profiler import PaintProfiler
    profiler = PaintProfiler()
    profiler.patch(my_widget)
    # ... interact ...
    profiler.report()
"""

from __future__ import annotations

import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from pymmcore_gui._qt.QtCore import QTimer
from pymmcore_gui._qt.QtWidgets import QApplication, QWidget


@dataclass
class PaintRecord:
    widget_class: str
    elapsed_ms: float
    region_rect: tuple[int, int, int, int]  # x, y, w, h
    timestamp: float
    stack: str | None = None


@dataclass
class PaintProfiler:
    """Track paintEvent timing across widgets."""

    threshold_ms: float = 2.0
    capture_slow_stacks: bool = True
    _records: list[PaintRecord] = field(default_factory=list, repr=False)
    _counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int), repr=False
    )
    _total_time: dict[str, float] = field(
        default_factory=lambda: defaultdict(float), repr=False
    )

    def patch(self, widget: QWidget) -> None:
        """Monkey-patch paintEvent on the given widget."""
        cls_name = type(widget).__name__
        original = widget.paintEvent

        def profiled_paint(event: Any) -> None:
            t0 = time.perf_counter_ns()
            original(event)
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6

            self._counts[cls_name] += 1
            self._total_time[cls_name] += elapsed_ms

            rect = event.rect()
            record = PaintRecord(
                widget_class=cls_name,
                elapsed_ms=elapsed_ms,
                region_rect=(rect.x(), rect.y(), rect.width(), rect.height()),
                timestamp=time.time(),
            )

            if elapsed_ms > self.threshold_ms:
                if self.capture_slow_stacks:
                    record.stack = "".join(traceback.format_stack()[:-1])
                print(
                    f"\033[33m[SLOW PAINT] {cls_name}: {elapsed_ms:.2f}ms "
                    f"region=({rect.x()},{rect.y()},{rect.width()},{rect.height()})"
                    f"\033[0m",
                    file=sys.stderr,
                )
            self._records.append(record)

        widget.paintEvent = profiled_paint  # type: ignore

    def patch_all(self, root: QWidget) -> int:
        """Patch all child widgets that have a paintEvent."""
        patched = 0
        for child in root.findChildren(QWidget):
            self.patch(child)
            patched += 1
        return patched

    def report(self) -> None:
        print(f"\n{'=' * 60}")
        print("Paint Profiler Report")
        print(f"{'=' * 60}")
        print(f"  Total paint events: {sum(self._counts.values())}")
        print(
            f"  Slow paints (>{self.threshold_ms}ms): "
            f"{sum(1 for r in self._records if r.elapsed_ms > self.threshold_ms)}"
        )

        if self._counts:
            print("\n  Paint counts and total time:")
            sorted_widgets = sorted(
                self._total_time.items(), key=lambda x: x[1], reverse=True
            )
            for cls_name, total_ms in sorted_widgets:
                count = self._counts[cls_name]
                avg = total_ms / count if count > 0 else 0
                print(
                    f"    {cls_name:<35} "
                    f"{count:>5}x  "
                    f"total={total_ms:>8.1f}ms  "
                    f"avg={avg:>6.2f}ms"
                )

        slow = [r for r in self._records if r.elapsed_ms > self.threshold_ms]
        if slow:
            print("\n  Top 10 slowest paint events:")
            for r in sorted(slow, key=lambda x: x.elapsed_ms, reverse=True)[:10]:
                print(
                    f"    {r.elapsed_ms:>8.2f}ms  {r.widget_class}  "
                    f"region={r.region_rect}"
                )
                if r.stack:
                    for line in r.stack.strip().splitlines()[-3:]:
                        print(f"      {line.strip()}")

        print(f"{'=' * 60}\n")

    def reset(self) -> None:
        self._records.clear()
        self._counts.clear()
        self._total_time.clear()


def main() -> None:
    from pymmcore_gui import create_mmgui

    app = QApplication.instance()
    if app is None:
        from pymmcore_gui._app import MMQApplication

        app = MMQApplication(sys.argv)

    win = create_mmgui(exec_app=False)

    profiler = PaintProfiler(threshold_ms=2.0, capture_slow_stacks=True)

    def attach_profiler() -> None:
        n = profiler.patch_all(win)
        print(f"Paint profiler attached to {n} widgets.")
        print("Interact with the GUI, then close to see the report.\n")

    QTimer.singleShot(1000, attach_profiler)

    app.exec()
    profiler.report()


if __name__ == "__main__":
    main()
