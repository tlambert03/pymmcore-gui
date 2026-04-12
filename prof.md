# Profiling and debugging PyQt6 apps like the pros do

**The hardest part of profiling a PyQt6 application is that execution constantly
crosses an invisible boundary between Python and Qt's C++ internals.** Most
Python profilers see only the Python side; most C++ profilers see only the
native side. The breakthrough insight is that a small set of modern tools—py-spy
with `--native` mode, Scalene's Python-vs-native split, and VizTracer's
Perfetto-based timeline—can bridge this gap when combined strategically.
Meanwhile, KDAB's GammaRay now supports Python-based Qt apps (PySide in v3.1+)
for deep Qt object introspection, and Qt 6.5+ ships built-in CTF tracing that
captures signal/slot dispatch, event handling, and library loading with
near-zero overhead.

The professional approach used by shops like KDAB follows a clear escalation
path: quick triage with a sampling profiler, timeline analysis of event flow,
line-level Python-vs-native breakdown, then deep C++ analysis only when needed.
For a slider-driven visualization app, this workflow pinpoints whether the
bottleneck is Python data processing, Qt rendering, or event loop
congestion—often within minutes.

---

## The Python/C++ boundary is your central profiling challenge

PyQt6 applications have a split personality. Your Python code calls into Qt's
massive C++ codebase via SIP bindings, and the event loop, signal dispatch, and
painting pipeline all execute in C++. A naive `cProfile` session shows most time
in `{built-in method exec_}`—one opaque blob representing the entire Qt event
loop. **cProfile cannot see into C++ code, only profiles the main thread, and
has known compatibility issues with PyQt's `sys.exit()` handling.**

The tools that actually bridge both worlds are limited but powerful:

| Tool | Python frames | C++ frames | Merged view | Overhead |
|------|:---:|:---:|:---:|:---:|
| **py-spy `--native`** | ✅ | ✅ (x86_64 Linux/Windows) | ✅ Merged stacks | Very low |
| **Linux `perf`** (Python 3.12+) | ✅ via perf trampolines | ✅ | ✅ Full stack | Very low |
| **Scalene** | ✅ | % time breakdown per line | Partial | Low (~10-20%) |
| **VizTracer** | ✅ | C boundary calls only | No deep C++ | Medium |
| **Intel VTune** | ✅ | ✅ | ✅ Source-level | Low |

**py-spy with `--native`** is the single most valuable tool for PyQt6
developers. It uses `libunwind-ptrace` on Linux and `StackWalk64` on Windows to
unwind native stacks, then merges them with Python frames by replacing
`_PyEval_EvalFrameDefault` entries with actual Python function names. The result
is a unified flame graph showing your Python `paintEvent` calling into
`QPainter::drawImage` calling into `QRasterPaintEngine::fill`—the complete
picture.

```bash
# The most useful single command for PyQt6 profiling
sudo py-spy record --native -o profile.svg -- python my_pyqt_app.py

# Or attach to a running app while dragging a slider
sudo py-spy record --native -o profile.svg --pid $(pgrep -f my_app) --duration 30
```

**Linux `perf` with Python 3.12+** provides even deeper visibility. Python 3.12
added perf trampoline support that lets `perf` resolve Python function names
alongside C++, kernel, and syscall frames:

```bash
PYTHONPERFSUPPORT=1 perf record -F 9999 -g --call-graph dwarf -o perf.data python my_app.py
```

This produces the ultimate full-stack view: Python code → SIP bindings → Qt C++
→ kernel syscalls. KDAB's **Hotspot** (v1.6.0, 2025) provides an excellent GUI
for analyzing these `perf.data` files with interactive flame graphs, off-CPU
analysis, and timeline views.

---

## Five profiling tools and when each one wins

**py-spy** is a Rust-based sampling profiler that attaches externally with zero
instrumentation. It naturally sees all Python threads including QThread workers
(as long as they execute Python code), generates SVG flame graphs or
Speedscope-compatible output, and with `--native` exposes Qt's C++ internals.
It's production-safe and adds virtually no overhead. Use it for quick triage:
`sudo py-spy top --pid <PID>` gives a live `top`-like view of your hottest
functions while you interact with the GUI.

**VizTracer** is a deterministic tracer that records every function entry/exit
and outputs Chrome Trace Format / Perfetto protobuf. Its killer feature for Qt
apps is the **timeline view**—you can see the temporal sequence of
`slider.valueChanged` → `on_value_changed()` → `self.update()` → `paintEvent()`
and spot exactly where delay accumulates. One critical caveat: VizTracer does
not automatically detect QThread-based threads. You must manually call
`get_tracer().enable_thread_tracing()` at the start of each QThread's `run()`
method.

```python
from viztracer import VizTracer
tracer = VizTracer(max_stack_depth=10, include_files=["my_app/"])
tracer.start()
app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
tracer.stop()
tracer.save("slider_profile.json")  # View with: vizviewer slider_profile.json
```

**Scalene** provides a unique capability no other tool matches: **per-line
separation of Python time vs native (C/C++) time vs system time**. For a PyQt6
app, this immediately answers the critical question of whether a slow line is
due to your Python logic or Qt's C++ rendering. Run `scalene my_app.py` and look
at each line of your `paintEvent`—if it shows 95% native time, the bottleneck is
inside Qt's rendering pipeline and your Python code is not the problem.

**yappi** (Yet Another Python Profiler) is the only deterministic profiler with
proper wall-time vs CPU-time multithreading support. However, **it has known
issues with QThreads and may crash**, because QThreads are created at the C++
level and CPython's thread state management may not be properly notified. Prefer
Python's native `threading.Thread` for workers when using yappi, or use it only
on the main thread.

**Austin** is a pure-C frame stack sampler with extremely low overhead and a
rich ecosystem of visualization integrations (Speedscope, FlameGraph, VS Code
extension, web UI). Like py-spy, it reads Python frames from process memory
without pausing the target. It lacks native C++ frame support but is excellent
for production monitoring.

---

## Qt's built-in tracing captures signal dispatch and event handling

**Qt 6.5 introduced a cross-platform Common Trace Format (CTF) backend** that
instruments the Qt runtime itself. When Qt is built with `-trace ctf`, the
framework emits structured trace events for QCoreApplication initialization,
event dispatching, **signal/slot invocations**, QLibrary loading, QImageReader
operations, and QFontDatabase queries. This is the closest thing to "X-ray
vision" into the event loop.

The tracing backends available when building Qt from source are:

- **`-trace ctf`** — Cross-platform CTF (Qt 6.5+), works on Windows, Linux, and
  embedded
- **`-trace lttng`** — Linux-only, integrates with the LTTng ecosystem
- **`-trace etw`** — Windows-only Event Tracing for Windows

For PyQt6 users, the catch is that you'd need a custom Qt build with tracing
enabled—prebuilt PyPI wheels don't include it. But if you're doing serious
performance work, building Qt with `-trace ctf` and installing it into your
environment is worth the effort. View the resulting traces in **Eclipse Trace
Compass** (native CTF support), **Qt Creator's Chrome Trace Format Visualizer**,
or convert with `babeltrace` for other viewers.

**Qt's QLoggingCategory** system provides lighter-weight categorized logging
with zero overhead when disabled (the `qCDebug()` macro does not evaluate
arguments if the category is off). Enable Qt's internal categories to see
framework-level activity:

```bash
export QT_LOGGING_RULES="qt.core.*.debug=true;qt.gui.*.debug=true;qt.widgets.*.debug=true"
```

---

## GammaRay and the KDAB professional toolkit

**KDAB's GammaRay** (v3.3, October 2025) is the gold standard for Qt application
introspection. It attaches to a running Qt process and provides over 20
inspection tools including an object tree browser, **signal/slot connection
monitor**, event monitor, timer statistics, and a **Paint Analyzer** that shows
every QPainter operation used to draw a widget with timing data. GammaRay 3.1
(July 2024) officially added PySide introspection support, and PyQt6 apps should
work similarly since both use the same underlying Qt libraries—attach to the
running Python process rather than launching through GammaRay.

GammaRay's signal monitoring capability is particularly valuable for
understanding cascading signal/slot chains. The `SignalSpyCallbackSet` API
monitors all QObject signal/slot communication, showing you exactly which
signals fire and which slots respond, with timing. The **QMetaObject
validation** feature identifies common problems with signal/slot declarations.

The complete KDAB open-source performance stack:

- **GammaRay** — Runtime Qt introspection (signals, events, painting, object
  tree)
- **Hotspot** — GUI for Linux `perf` data with flame graphs and off-CPU analysis
- **Heaptrack** — Heap memory allocation profiling with stack traces (much
  faster than Valgrind Massif)
- **Clazy** — Compile-time static analyzer for Qt-specific anti-patterns
- **ctf2ctf** — Converts LTTng CTF traces to Chrome Trace Format JSON

KDAB's recommended 5-step methodology is: **(1)** assess what to measure (CPU?
memory? frame rate? startup?), **(2)** choose tools appropriate to the metric,
**(3)** write automated benchmarks, **(4)** establish a baseline measurement,
**(5)** make changes, measure, and compare iteratively. Their 3-day training
course "Debugging and Profiling Qt applications on Linux" covers this entire
stack.

For **CI integration**, use `perf record` in CI pipelines, store `perf.data` as
artifacts (Hotspot v1.6.0 supports archived `.perf.data.zip` files), and track
regressions over time. Qt's own test framework includes a `QBENCHMARK` macro for
performance benchmarks that can be integrated into automated test suites.

---

## Practical PyQt6 instrumentation patterns

### Event loop monitoring catches blocked iterations

The `QAbstractEventDispatcher` exposes `awake` and `aboutToBlock` signals that
bracket each event processing cycle. The time between `awake` and `aboutToBlock`
represents how long the event loop spent processing pending events before going
idle—if this exceeds **16ms**, you're dropping frames at 60fps:

```python
from PyQt6.QtCore import QAbstractEventDispatcher, QElapsedTimer

class EventLoopMonitor:
    def __init__(self, threshold_ms=16):
        self.threshold_ms = threshold_ms
        self.timer = QElapsedTimer()
        dispatcher = QAbstractEventDispatcher.instance()
        dispatcher.awake.connect(self._on_awake)
        dispatcher.aboutToBlock.connect(self._on_about_to_block)

    def _on_awake(self):
        self.timer.start()

    def _on_about_to_block(self):
        elapsed = self.timer.elapsed()
        if elapsed > self.threshold_ms:
            print(f"[SLOW LOOP] Event processing took {elapsed}ms")
```

### Signal/slot tracing via connectNotify and decorators

PyQt6 exposes Qt's `connectNotify` and `disconnectNotify` virtual methods, which
fire whenever a signal is connected or disconnected. Override these in your
QObject subclasses for connection debugging:

```python
class TracedObject(QObject):
    def connectNotify(self, signal: QMetaMethod):
        print(f"Connected: {signal.methodSignature().data().decode()}")
        super().connectNotify(signal)
```

For measuring slot execution time, a decorator that wraps the `@pyqtSlot`
pattern is effective. **The critical design choice is making tracing zero-cost
when disabled**—check an environment variable at decoration time and return the
unwrapped function if tracing is off:

```python
TRACING = os.environ.get('PYQT_TRACE', '0') == '1'

def timed_slot(func):
    if not TRACING:
        return func  # Zero overhead when disabled
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter_ns()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
            if elapsed_ms > 1.0:
                print(f"[SLOW SLOT] {func.__qualname__}: {elapsed_ms:.2f}ms")
    return wrapper
```

### Paint profiling and detecting unnecessary repaints

Override `update()` and `repaint()` on your widgets to log callers via
`traceback.extract_stack()`. This reveals **duplicate repaint triggers**—a
common performance killer where multiple code paths call `update()` for the same
logical change. Remember that `update()` is asynchronous and Qt coalesces
multiple calls into one `paintEvent` with the union of dirty regions, while
`repaint()` is synchronous and should almost never be used.

For the slider-driven canvas specifically, **throttle updates with a single-shot
QTimer**:

```python
self.update_timer = QTimer()
self.update_timer.setSingleShot(True)
self.update_timer.setInterval(16)  # ~60fps cap
self.update_timer.timeout.connect(self.do_repaint)
slider.valueChanged.connect(lambda: self.update_timer.start())
```

---

## Visualization tools that tie everything together

**Perfetto UI** (`ui.perfetto.dev`) is the most capable trace viewer available
today. It handles Chrome Trace JSON, Perfetto protobuf, and can render traces
with hundreds of millions of events. VizTracer uses Perfetto as its frontend.
You can write custom trace events in Chrome JSON format from Python and view
them alongside system traces.

**Tracy Profiler** (v0.11+, 2024) added direct Python support and offers
real-time streaming visualization with ~2ns per instrumentation zone—roughly
300x less overhead than Perfetto's SDK. Tracy's native desktop GUI is extremely
fast for interactive exploration. It also includes an `import-chrome` utility
that converts Chrome Trace JSON to Tracy's format, enabling interoperability
with VizTracer output.

**Speedscope** (`speedscope.app`) runs entirely in the browser without uploading
data and provides three flame graph views (Time Order, Left Heavy, Sandwich).
py-spy outputs directly in Speedscope format with `--format speedscope`.

For **combining Python and C++ traces**, the most practical approaches are:
**(1)** py-spy `--native` for merged flame graphs, **(2)** VizTracer's
`--combine` flag to merge multiple JSON trace files with different
process/thread IDs, **(3)** emitting both Python and C++ events in Chrome Trace
JSON to the same file and viewing in Perfetto, or **(4)** using `per4m` to
overlay VizTracer's Python traces with Linux `perf` hardware counter and
scheduler data on a unified timeline.

---

## The recommended escalation workflow

For a PyQt6 visualization tool with slider-driven canvas updates, follow this
diagnostic sequence:

**Step 1 — Quick triage** (30 seconds): `sudo py-spy top --pid <PID>` while
dragging the slider. This shows which Python functions are hottest in real time.
If `paintEvent` dominates, the rendering path is the bottleneck. If a
data-processing function dominates, optimize your computation first.

**Step 2 — Python vs native split** (2 minutes): Run `scalene my_app.py` and
interact with the slider. Look at the per-line breakdown. If your `paintEvent`
shows **90%+ native time**, the bottleneck is inside Qt's C++ rendering and your
Python code isn't the problem—consider caching rendered images or reducing
QPainter operations. If it shows significant Python time, focus on your Python
logic.

**Step 3 — Timeline analysis** (5 minutes): Use VizTracer to record a trace
while dragging the slider. The Perfetto timeline reveals whether `paintEvent`
calls are bunching up, whether signal/slot dispatch introduces latency, and
whether your worker threads are producing data faster than the GUI thread
consumes it.

**Step 4 — Deep C++ analysis** (when needed): Use `py-spy record --native` or
`perf` with Python 3.12+ to see exactly which Qt C++ functions consume time. Use
KDAB's Hotspot to analyze the `perf.data` with flame graphs and off-CPU views.

**Step 5 — Qt introspection** (for signal/event issues): Attach GammaRay to
inspect the object tree, monitor signal connections, time event delivery, and
analyze QPainter operations in the Paint Analyzer.

## Conclusion

The PyQt6 profiling landscape in 2025–2026 is genuinely capable, but requires
knowing which tool to reach for. **py-spy `--native` and Scalene solve the
fundamental Python/C++ boundary problem** that makes naive profiling useless.
**VizTracer + Perfetto UI provides the timeline view** essential for
understanding event-driven architectures. **Qt's built-in CTF tracing** (6.5+)
gives framework-level visibility when you control the Qt build. And **GammaRay**
remains unmatched for Qt-specific introspection—its recent PySide support
extends this to the Python ecosystem.

The tools that don't exist yet are notable: there is no single tool that unifies
Python tracing, Qt C++ tracing, and GPU rendering profiling into one seamless
timeline. The closest approximation is combining VizTracer output with `perf`
data via `per4m`, or writing both Python and C++ events into a shared Perfetto
trace. Tracy's new Python support and its real-time streaming model may evolve
to fill this gap. For now, the multi-tool escalation workflow described
above—triage, split, timeline, deep dive, introspect—is how professional Qt
development shops operate, and it works.
