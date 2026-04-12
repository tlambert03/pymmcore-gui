# ruff: noqa: D101, D102, D103, D105
"""Monitor event loop iteration times to detect blocked/slow iterations.

Hooks into QAbstractEventDispatcher's awake/aboutToBlock signals to measure
how long each event loop cycle takes. Iterations exceeding the threshold are
logged with optional traceback capture.

Usage:
    # As a module — patches the app before exec():
    python -m scripts.event_loop_monitor

    # Programmatically from a console or test:
    from scripts.event_loop_monitor import EventLoopMonitor
    monitor = EventLoopMonitor(threshold_ms=16)
    # ... interact with the app, then:
    monitor.report()
"""

from __future__ import annotations

import sys
import time
import traceback
from dataclasses import dataclass, field

from pymmcore_gui._qt.QtCore import QAbstractEventDispatcher, QElapsedTimer


@dataclass
class SlowIteration:
    elapsed_ms: float
    timestamp: float
    stack: str | None = None


@dataclass
class EventLoopMonitor:
    """Track event loop iteration durations, flagging slow ones."""

    threshold_ms: float = 16.0
    capture_stacks: bool = False
    _timer: QElapsedTimer = field(default_factory=QElapsedTimer, repr=False)
    _slow: list[SlowIteration] = field(default_factory=list, repr=False)
    _total_iterations: int = field(default=0, repr=False)
    _max_ms: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        dispatcher = QAbstractEventDispatcher.instance()
        if dispatcher is None:
            raise RuntimeError("No QAbstractEventDispatcher — is QApplication running?")
        dispatcher.awake.connect(self._on_awake)
        dispatcher.aboutToBlock.connect(self._on_about_to_block)

    def _on_awake(self) -> None:
        self._timer.start()

    def _on_about_to_block(self) -> None:
        elapsed = self._timer.elapsed()
        self._total_iterations += 1
        if elapsed > self._max_ms:
            self._max_ms = elapsed
        if elapsed > self.threshold_ms:
            stack = None
            if self.capture_stacks:
                stack = "".join(traceback.format_stack()[:-1])
            entry = SlowIteration(
                elapsed_ms=elapsed, timestamp=time.time(), stack=stack
            )
            self._slow.append(entry)
            print(f"\033[33m[SLOW LOOP] {elapsed:.1f}ms\033[0m", file=sys.stderr)
            if stack:
                print(stack, file=sys.stderr)

    @property
    def slow_iterations(self) -> list[SlowIteration]:
        return list(self._slow)

    def report(self) -> None:
        """Print a summary of event loop performance."""
        print(f"\n{'=' * 60}")
        print("Event Loop Monitor Report")
        print(f"{'=' * 60}")
        print(f"  Total iterations:   {self._total_iterations}")
        print(f"  Slow iterations:    {len(self._slow)} (>{self.threshold_ms:.0f}ms)")
        print(f"  Max iteration time: {self._max_ms:.1f}ms")
        if self._slow:
            avg = sum(s.elapsed_ms for s in self._slow) / len(self._slow)
            print(f"  Avg slow time:      {avg:.1f}ms")
            print("\n  Top 10 slowest:")
            for s in sorted(self._slow, key=lambda x: x.elapsed_ms, reverse=True)[:10]:
                print(f"    {s.elapsed_ms:.1f}ms")
                if s.stack:
                    for line in s.stack.strip().splitlines()[-4:]:
                        print(f"      {line}")
        print(f"{'=' * 60}\n")

    def reset(self) -> None:
        self._slow.clear()
        self._total_iterations = 0
        self._max_ms = 0.0


def main() -> None:
    from pymmcore_gui import create_mmgui
    from pymmcore_gui._qt.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        from pymmcore_gui._app import MMQApplication

        app = MMQApplication(sys.argv)

    monitor = EventLoopMonitor(threshold_ms=16, capture_stacks=True)
    print("Event loop monitor active (threshold=16ms, stacks=on)")
    print("Interact with the GUI, then close to see the report.\n")

    create_mmgui(exec_app=False)
    app.exec()
    monitor.report()


if __name__ == "__main__":
    main()
