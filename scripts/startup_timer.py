# ruff: noqa: D103
"""Measure application startup time broken down by phase.

Instruments the import chain, QApplication creation, window construction,
config loading, and first paint to identify startup bottlenecks.

Usage:
    uv run python -m scripts.startup_timer
    uv run python -m scripts.startup_timer --repeat 3
"""

from __future__ import annotations

import argparse
import sys
import time


def measure_startup(repeat: int = 1) -> None:
    results: list[dict[str, float]] = []

    for i in range(repeat):
        if repeat > 1:
            print(f"\n--- Run {i + 1}/{repeat} ---")

        timings: dict[str, float] = {}

        # Phase 1: Import pymmcore_gui
        t0 = time.perf_counter()

        timings["import pymmcore_gui"] = time.perf_counter() - t0

        # Phase 2: Import Qt
        t0 = time.perf_counter()
        from pymmcore_gui._qt.QtWidgets import QApplication

        timings["import Qt"] = time.perf_counter() - t0

        # Phase 3: Create QApplication
        t0 = time.perf_counter()
        app = QApplication.instance()
        if app is None:
            from pymmcore_gui._app import MMQApplication

            app = MMQApplication(sys.argv)
        timings["QApplication"] = time.perf_counter() - t0

        # Phase 4: Import CMMCorePlus
        t0 = time.perf_counter()
        from pymmcore_plus import CMMCorePlus

        timings["import CMMCorePlus"] = time.perf_counter() - t0

        # Phase 5: Create core instance
        t0 = time.perf_counter()
        core = CMMCorePlus()
        timings["CMMCorePlus()"] = time.perf_counter() - t0

        # Phase 6: Create main window
        t0 = time.perf_counter()
        from pymmcore_gui._main_window import MicroManagerGUI

        win = MicroManagerGUI(mmcore=core)
        timings["MicroManagerGUI()"] = time.perf_counter() - t0

        # Phase 7: Load demo config
        t0 = time.perf_counter()
        try:
            core.loadSystemConfiguration("MMConfig_demo.cfg")
        except Exception as e:
            print(f"  (config load failed: {e})")
        timings["loadSystemConfiguration"] = time.perf_counter() - t0

        # Phase 8: Show + first paint
        t0 = time.perf_counter()
        win.show()
        app.processEvents()
        timings["show + processEvents"] = time.perf_counter() - t0

        total = sum(timings.values())
        timings["TOTAL"] = total
        results.append(timings)

        # Print this run
        print(f"\n{'Phase':<30} {'Time (ms)':>10} {'%':>6}")
        print(f"{'-' * 48}")
        for phase, t in timings.items():
            if phase == "TOTAL":
                print(f"{'-' * 48}")
            pct = (t / total * 100) if total > 0 else 0
            print(f"{phase:<30} {t * 1000:>10.1f} {pct:>5.1f}%")

        win.close()
        # Clean up for next iteration (imports are cached, which is fine —
        # that reflects real second-launch behavior)
        del win

    # Summary across runs
    if repeat > 1:
        print(f"\n{'=' * 60}")
        print(f"Summary across {repeat} runs")
        print(f"{'=' * 60}")
        all_phases = [k for k in results[0] if k != "TOTAL"]
        for phase in [*all_phases, "TOTAL"]:
            values = [r[phase] * 1000 for r in results]
            avg = sum(values) / len(values)
            mn = min(values)
            mx = max(values)
            print(
                f"  {phase:<30} avg={avg:>7.1f}ms  min={mn:>7.1f}ms  max={mx:>7.1f}ms"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure mmgui startup time.")
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of runs (default: 1)."
    )
    args = parser.parse_args()
    measure_startup(repeat=args.repeat)


if __name__ == "__main__":
    main()
