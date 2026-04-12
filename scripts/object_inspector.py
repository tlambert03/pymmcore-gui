# ruff: noqa: D103
"""Inspect the live Qt object tree, signal connections, and widget hierarchy.

Useful for understanding the runtime structure of the application — which
widgets exist, how many QObjects are alive, what timers are running, etc.

Usage:
    # Launch the app with the inspector attached:
    uv run python -m scripts.object_inspector

    # Or from the IPython console inside the running app:
    from scripts.object_inspector import inspect_app
    inspect_app()
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from pymmcore_gui._qt.QtCore import QObject, QTimer
from pymmcore_gui._qt.QtWidgets import QApplication, QWidget


def get_object_tree(root: QObject, depth: int = 0, max_depth: int = 6) -> list[str]:
    """Return indented lines describing the QObject tree."""
    lines: list[str] = []
    cls = type(root).__name__
    name = root.objectName() or "(unnamed)"
    extra = ""
    if isinstance(root, QWidget):
        size = root.size()
        vis = "visible" if root.isVisible() else "hidden"
        extra = f" [{vis}, {size.width()}x{size.height()}]"
    lines.append(f"{'  ' * depth}{cls} '{name}'{extra}")
    if depth < max_depth:
        for child in root.children():
            lines.extend(get_object_tree(child, depth + 1, max_depth))
    return lines


def count_objects(root: QObject) -> Counter[str]:
    """Count QObject subclass instances in the tree."""
    counter: Counter[str] = Counter()
    counter[type(root).__name__] += 1
    for child in root.findChildren(QObject):
        counter[type(child).__name__] += 1
    return counter


def find_timers(root: QObject) -> list[dict[str, Any]]:
    """Find all active QTimer instances."""
    timers = []
    for timer in root.findChildren(QTimer):
        timers.append(
            {
                "objectName": timer.objectName() or "(unnamed)",
                "interval_ms": timer.interval(),
                "singleShot": timer.isSingleShot(),
                "active": timer.isActive(),
                "parent": type(timer.parent()).__name__ if timer.parent() else None,
            }
        )
    return timers


def widget_summary(root: QWidget) -> dict[str, int]:
    """Count visible vs hidden widgets."""
    visible = 0
    hidden = 0
    for w in root.findChildren(QWidget):
        if w.isVisible():
            visible += 1
        else:
            hidden += 1
    return {"visible": visible, "hidden": hidden, "total": visible + hidden}


def inspect_app(max_tree_depth: int = 4) -> None:
    """Print a comprehensive inspection of the running application."""
    app = QApplication.instance()
    if app is None:
        print("No QApplication instance found.")
        return

    windows = app.topLevelWidgets()

    print(f"\n{'=' * 60}")
    print("Qt Application Inspector")
    print(f"{'=' * 60}")
    print(f"  Application: {app.applicationName()} v{app.applicationVersion()}")
    print(f"  Top-level windows: {len(windows)}")

    for win in windows:
        if not win.isVisible():
            continue
        cls = type(win).__name__
        print(f"\n--- {cls} '{win.objectName() or '(unnamed)'}' ---")

        # Widget counts
        summary = widget_summary(win)
        print(
            f"  Widgets: {summary['total']} total "
            f"({summary['visible']} visible, {summary['hidden']} hidden)"
        )

        # Object class distribution
        counts = count_objects(win)
        print("  QObject types (top 15):")
        for name, count in counts.most_common(15):
            print(f"    {count:>5}x  {name}")

        # Active timers
        timers = find_timers(win)
        active_timers = [t for t in timers if t["active"]]
        print(f"\n  Timers: {len(timers)} total, {len(active_timers)} active")
        for t in active_timers:
            shot = " (single-shot)" if t["singleShot"] else ""
            print(f"    {t['interval_ms']:>6}ms  parent={t['parent']}{shot}")

        # Object tree
        print(f"\n  Object tree (depth={max_tree_depth}):")
        for line in get_object_tree(win, max_depth=max_tree_depth):
            print(f"    {line}")

    print(f"\n{'=' * 60}\n")


def main() -> None:
    from pymmcore_gui import create_mmgui

    app = QApplication.instance()
    if app is None:
        from pymmcore_gui._app import MMQApplication

        app = MMQApplication(sys.argv)

    print("Launching app with object inspector...")
    print("The inspector will run after the window is shown.\n")

    create_mmgui(exec_app=False)

    # Run inspector after event loop has had a chance to settle
    QTimer.singleShot(2000, lambda: inspect_app(max_tree_depth=4))

    app.exec()


if __name__ == "__main__":
    main()
