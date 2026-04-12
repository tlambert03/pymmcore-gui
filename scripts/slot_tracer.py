# ruff: noqa: D101, D102, D103
"""Trace signal/slot execution times across the application.

Provides a decorator and a monkey-patching approach to measure how long
slot callbacks take, identifying slow handlers that block the GUI thread.

Usage:
    # Decorate individual slots:
    from scripts.slot_tracer import timed_slot

    @timed_slot(threshold_ms=5.0)
    def on_value_changed(self, value: int) -> None:
        ...

    # Or run the app with automatic QMetaObject-level signal monitoring:
    python -m scripts.slot_tracer
"""

from __future__ import annotations

import functools
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pymmcore_gui._qt.QtCore import QMetaMethod, QObject

F = TypeVar("F", bound=Callable[..., Any])


def timed_slot(
    threshold_ms: float = 1.0,
    log: bool = True,
) -> Callable[[F], F]:
    """Decorator that times a slot and warns if it exceeds threshold_ms."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter_ns()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
                if elapsed_ms > threshold_ms and log:
                    print(
                        f"\033[33m[SLOW SLOT] {func.__qualname__}: "
                        f"{elapsed_ms:.2f}ms\033[0m",
                        file=sys.stderr,
                    )

        return wrapper  # type: ignore

    return decorator


@dataclass
class SignalEvent:
    signal_name: str
    sender_class: str
    timestamp: float
    elapsed_ms: float | None = None


@dataclass
class SignalTracer:
    """Traces signal emissions using connectNotify on watched objects."""

    _events: list[SignalEvent] = field(default_factory=list, repr=False)
    _counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int), repr=False
    )

    def watch(self, obj: QObject) -> None:
        """Install connect/disconnect tracing on a QObject."""
        cls = type(obj)
        original_connect_notify = cls.connectNotify

        def traced_connect_notify(
            self_: QObject, signal: QMetaMethod
        ) -> None:  # pragma: no cover
            sig_name = signal.methodSignature().data().decode()  # type: ignore
            sender_cls = type(self_).__name__
            print(f"\033[36m[CONNECT] {sender_cls}.{sig_name}\033[0m", file=sys.stderr)
            original_connect_notify(self_, signal)

        cls.connectNotify = traced_connect_notify  # type: ignore

    def log_emission(self, signal_name: str, sender: QObject) -> None:
        sender_cls = type(sender).__name__
        event = SignalEvent(
            signal_name=signal_name,
            sender_class=sender_cls,
            timestamp=time.time(),
        )
        self._events.append(event)
        self._counts[f"{sender_cls}.{signal_name}"] += 1

    def report(self) -> None:
        """Print signal emission statistics."""
        print(f"\n{'=' * 60}")
        print("Signal Tracer Report")
        print(f"{'=' * 60}")
        print(f"  Total events tracked: {len(self._events)}")
        if self._counts:
            print("\n  Signal emission counts (top 20):")
            for name, count in sorted(
                self._counts.items(), key=lambda x: x[1], reverse=True
            )[:20]:
                print(f"    {count:>6}x  {name}")
        print(f"{'=' * 60}\n")


@dataclass
class RepaintTracer:
    """Track widget update()/repaint() calls to find duplicate repaints."""

    _update_counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int), repr=False
    )
    _repaint_counts: dict[str, int] = field(
        default_factory=lambda: defaultdict(int), repr=False
    )

    def patch_widget(self, widget: Any) -> None:
        """Monkey-patch update() and repaint() on a widget to count calls."""
        cls_name = type(widget).__name__
        original_update = widget.update
        original_repaint = widget.repaint

        @functools.wraps(original_update)
        def traced_update(*args: Any, **kwargs: Any) -> Any:
            self._update_counts[cls_name] += 1
            return original_update(*args, **kwargs)

        @functools.wraps(original_repaint)
        def traced_repaint(*args: Any, **kwargs: Any) -> Any:
            self._repaint_counts[cls_name] += 1
            print(
                f"\033[31m[REPAINT] {cls_name}.repaint() called "
                f"(prefer update())\033[0m",
                file=sys.stderr,
            )
            return original_repaint(*args, **kwargs)

        widget.update = traced_update
        widget.repaint = traced_repaint

    def report(self) -> None:
        print(f"\n{'=' * 60}")
        print("Repaint Tracer Report")
        print(f"{'=' * 60}")
        if self._update_counts:
            print("  update() calls:")
            for name, count in sorted(
                self._update_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"    {count:>6}x  {name}")
        if self._repaint_counts:
            print("  repaint() calls (should be rare):")
            for name, count in sorted(
                self._repaint_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"    {count:>6}x  {name}")
        print(f"{'=' * 60}\n")


def main() -> None:
    from pymmcore_gui import create_mmgui
    from pymmcore_gui._qt.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        from pymmcore_gui._app import MMQApplication

        app = MMQApplication(sys.argv)

    print("Slot / signal tracer active.")
    print("Interact with the GUI, then close to see the report.\n")

    win = create_mmgui(exec_app=False)

    # Patch all child widgets for repaint tracking
    repaint_tracer = RepaintTracer()
    for child in win.findChildren(QObject):
        if hasattr(child, "update") and hasattr(child, "repaint"):
            repaint_tracer.patch_widget(child)

    app.exec()
    repaint_tracer.report()


if __name__ == "__main__":
    main()
