# Developer Profiling & Debugging Scripts

Scripts for diagnosing performance issues and understanding runtime behavior in
pymmcore-gui. Each script can be run standalone or imported into the app's
IPython console for live use.

All scripts are run from the repo root via `uv run python -m scripts.<name>`.

## Quick Reference

| Scenario | Script | Extra deps |
|----------|--------|------------|
| "The UI feels sluggish" | `event_loop_monitor` | none |
| "Startup is slow" | `startup_timer` | none |
| "Which paints are slow?" | `paint_profiler` | none |
| "I need a flame graph" | `profile_app pyspy` | `py-spy` |
| "Python or C++?" | `profile_app scalene` | `scalene` |
| "Show me a timeline" | `profile_app viztracer` | `viztracer` |
| "How many widgets exist?" | `object_inspector` | none |
| "Which slots are slow?" | `slot_tracer` | none |

## Scripts

### `event_loop_monitor` — Detect blocked event loop iterations

Hooks into `QAbstractEventDispatcher` to measure each event loop cycle. Any
iteration exceeding the threshold (default 16ms = 60fps) is flagged with an
optional stack trace.

```bash
# Launch the app with the monitor attached
uv run python -m scripts.event_loop_monitor
```

From the IPython console inside a running app:

```python
from scripts.event_loop_monitor import EventLoopMonitor
monitor = EventLoopMonitor(threshold_ms=16, capture_stacks=True)
# ... interact with the app ...
monitor.report()
```

### `startup_timer` — Measure startup phases

Breaks down startup time by phase: imports, QApplication creation, window
construction, config loading, and first paint.

```bash
uv run python -m scripts.startup_timer
uv run python -m scripts.startup_timer --repeat 5
```

### `paint_profiler` — Profile widget paint performance

Monkey-patches `paintEvent` on all widgets to time each paint call and detect
expensive rendering.

```bash
uv run python -m scripts.paint_profiler
```

From the console:

```python
from scripts.paint_profiler import PaintProfiler
profiler = PaintProfiler(threshold_ms=2.0)
profiler.patch(some_widget)       # single widget
profiler.patch_all(main_window)   # all children
# ... interact ...
profiler.report()
```

### `profile_app` — Unified profiling entry point

Wraps several profiling backends into one CLI:

```bash
# cProfile (built-in, always available)
uv run python -m scripts.profile_app cprofile
uv run python -m scripts.profile_app cprofile --sort tottime --top 60

# py-spy sampling profiler (flame graphs)
uv run python -m scripts.profile_app pyspy

# VizTracer (Perfetto timeline)
uv run --with viztracer python -m scripts.profile_app viztracer

# Scalene (per-line Python vs C++ time)
uv run --with scalene python -m scripts.profile_app scalene
```

Outputs are written to `./profiling_output/`.

For **py-spy live monitoring** of a running app:

```bash
py-spy top --pid $(pgrep -f mmgui)
```

### `object_inspector` — Inspect the live Qt object tree

Shows widget counts, active timers, object class distribution, and the full
QObject tree hierarchy.

```bash
uv run python -m scripts.object_inspector
```

From the console:

```python
from scripts.object_inspector import inspect_app, find_timers, count_objects
inspect_app()
```

### `slot_tracer` — Trace signal/slot performance

Provides a `@timed_slot` decorator for measuring individual slot execution, and
a `RepaintTracer` that counts `update()`/`repaint()` calls per widget.

```bash
uv run python -m scripts.slot_tracer
```

Decorate individual slots in your code:

```python
from scripts.slot_tracer import timed_slot

@timed_slot(threshold_ms=5.0)
def on_slider_changed(self, value: int) -> None:
    ...
```

## Existing Environment Variables

These are built into the app itself (not part of these scripts):

| Variable | Effect |
|----------|--------|
| `MMGUI_DEBUG_EXCEPTIONS` | Drop into pdb on unhandled exception |
| `MMGUI_EXIT_ON_EXCEPTION` | Exit the app after handling an exception |
| `MM_TELEMETRY_DEBUG` | Debug output for Sentry telemetry |

## Tips

- **Combine tools**: Run `event_loop_monitor` + `paint_profiler` together from
  the console to correlate slow loop iterations with paint activity.
- **py-spy `--native`**: On Linux/Windows, adds C++ frames to flame graphs.
  On macOS, only Python frames are shown (still useful).
- **VizTracer + Perfetto**: Open the JSON output at https://ui.perfetto.dev for
  an interactive timeline with zoom, search, and flow arrows.
- **snakeviz**: Install `snakeviz` to interactively explore cProfile output:
  `snakeviz profiling_output/cprofile.prof`
